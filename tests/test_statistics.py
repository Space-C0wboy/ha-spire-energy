"""Tests for parsing Spire history and building external statistics."""
from datetime import date, datetime
from unittest.mock import patch
from zoneinfo import ZoneInfo

from custom_components.spire_energy.statistics import (
    Bill,
    DailyRead,
    async_import_statistics,
    build_statistics,
    parse_bills,
    parse_daily_reads,
    statistic_ids,
)

from .common import DAILY, MONTHLY, bill, daily

TZ = ZoneInfo("America/Chicago")


def midnight(d: date) -> datetime:
    return datetime(d.year, d.month, d.day, tzinfo=TZ)


def rows(series, *keys):
    return [tuple(r[k] for k in keys) for r in series]


def test_parse_daily_reads_oldest_first():
    assert parse_daily_reads(DAILY) == [
        DailyRead(date(2026, 1, 1), 97.0, 1.5),
        DailyRead(date(2026, 1, 2), 100.0, 3.0),
        DailyRead(date(2026, 1, 5), 108.0, 1.0),
        DailyRead(date(2026, 1, 6), 110.0, 2.0),
    ]


def test_parse_bills_oldest_first():
    assert parse_bills(MONTHLY) == [
        Bill(date(2026, 1, 1), date(2026, 1, 2), 6.0),
        Bill(date(2026, 1, 2), date(2026, 1, 6), 33.0),
    ]


def test_parse_skips_incomplete_and_odd_payloads():
    for parse in (parse_daily_reads, parse_bills):
        assert parse({}) == []
        assert parse({"premises": []}) == []
        assert parse({"premises": [{"yearlyUsages": None}]}) == []
    broken = {"premises": [{"yearlyUsages": [{"usageDetails": [
        daily("2026-01-01", None, "1"), daily("bad", "1", "1"), {"measuredOn": "2026-01-03"},
    ]}]}]}
    assert parse_daily_reads(broken) == []
    assert parse_bills(DAILY) == []  # daily rows carry no dollars/period


def test_consumption_uses_read_differences_so_gaps_keep_their_usage():
    consumption, _ = build_statistics(parse_daily_reads(DAILY), [], TZ)
    assert rows(consumption, "start", "state", "sum") == [
        (midnight(date(2025, 12, 31)), 95.5, 0.0),  # baseline: first read minus its own usage
        (midnight(date(2026, 1, 1)), 97.0, 1.5),
        (midnight(date(2026, 1, 2)), 100.0, 4.5),
        (midnight(date(2026, 1, 5)), 108.0, 12.5),  # 8 CCF: covers the Jan 3-4 gap, not just units=1
        (midnight(date(2026, 1, 6)), 110.0, 14.5),
    ]


def test_meter_going_backwards_falls_back_to_units():
    reads = [DailyRead(date(2026, 1, 1), 500.0, 1.0), DailyRead(date(2026, 1, 2), 2.0, 2.0)]
    consumption, _ = build_statistics(reads, [], TZ)
    assert [r["sum"] for r in consumption] == [0.0, 1.0, 3.0]


def test_cost_spreads_each_bill_by_daily_usage():
    _, cost = build_statistics(parse_daily_reads(DAILY), parse_bills(MONTHLY), TZ)
    assert rows(cost, "start", "state", "sum") == [
        (midnight(date(2025, 12, 31)), 0.0, 0.0),
        (midnight(date(2026, 1, 1)), 0.0, 0.0),  # before the first bill period
        (midnight(date(2026, 1, 2)), 6.0, 6.0),  # only usage day in bill 1
        (midnight(date(2026, 1, 5)), 26.4, 32.4),  # 8 of 10 CCF in bill 2
        (midnight(date(2026, 1, 6)), 6.6, 39.0),  # remainder lands here; bill totals exact
    ]


def test_cost_split_evenly_when_period_used_nothing():
    reads = [DailyRead(date(2026, 1, d), 10.0, 0.0) for d in (1, 2, 3, 4)]
    _, cost = build_statistics(reads, [Bill(date(2026, 1, 1), date(2026, 1, 4), 10.0)], TZ)
    assert [r["state"] for r in cost] == [0.0, 0.0, 3.33, 3.33, 3.34]


def test_bill_with_no_daily_reads_lands_on_its_end_date():
    reads = [DailyRead(date(2026, 1, 1), 10.0, 1.0), DailyRead(date(2026, 1, 9), 12.0, 1.0)]
    _, cost = build_statistics(reads, [Bill(date(2026, 1, 3), date(2026, 1, 5), 20.0)], TZ)
    assert rows(cost, "start", "sum")[-2:] == [(midnight(date(2026, 1, 5)), 20.0), (midnight(date(2026, 1, 9)), 20.0)]


def test_rebilled_period_keeps_the_last_bill():
    rebilled = {"premises": [{"yearlyUsages": [{"usageDetails": [
        bill("2026-01-02", "2026-01-06", "33.00", "10"), bill("2026-01-02", "2026-01-06", "40.00", "10"),
    ]}]}]}
    assert parse_bills(rebilled) == [Bill(date(2026, 1, 2), date(2026, 1, 6), 40.0)]


def test_build_empty():
    assert build_statistics([], [], TZ) == ([], [])


def test_statistic_ids_are_per_account_and_valid():
    assert statistic_ids("1234-567 89") == (
        "spire_energy:gas_consumption_1234_567_89",
        "spire_energy:gas_cost_1234_567_89",
    )


async def test_import_calls_recorder(hass):
    with patch("custom_components.spire_energy.statistics.async_add_external_statistics") as add:
        async_import_statistics(hass, "123", parse_daily_reads(DAILY), parse_bills(MONTHLY))
    meta = [c.args[1] for c in add.call_args_list]
    assert [m["statistic_id"] for m in meta] == ["spire_energy:gas_consumption_123", "spire_energy:gas_cost_123"]
    assert meta[0]["unit_of_measurement"] == "CCF"
    assert len(add.call_args_list[0].args[2]) == 5


async def test_import_without_reads_does_nothing(hass):
    with patch("custom_components.spire_energy.statistics.async_add_external_statistics") as add:
        async_import_statistics(hass, "123", [], parse_bills(MONTHLY))
    assert add.call_count == 0
