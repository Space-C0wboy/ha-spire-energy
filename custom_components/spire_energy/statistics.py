"""External statistics for the Energy dashboard: daily gas use from meter reads, cost from bills."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, tzinfo
import re
from typing import Any

from homeassistant.components.recorder.models import (
    StatisticData,
    StatisticMeanType,
    StatisticMetaData,
)
from homeassistant.components.recorder.statistics import async_add_external_statistics
from homeassistant.const import UnitOfVolume
from homeassistant.core import HomeAssistant, callback
from homeassistant.util import dt as dt_util
from homeassistant.util.unit_conversion import VolumeConverter

from .const import DOMAIN


@dataclass(frozen=True)
class DailyRead:
    day: date
    read: float  # cumulative meter read, CCF
    units: float  # Spire's own usage figure for the day, CCF


@dataclass(frozen=True)
class Bill:
    start: date  # exclusive: the previous bill's read date
    end: date  # inclusive: this bill's read date
    dollars: float


def _details(data: dict[str, Any]) -> list[dict[str, Any]]:
    try:
        return [d for y in data["premises"][0]["yearlyUsages"] for d in y["usageDetails"]]
    except (KeyError, IndexError, TypeError):
        return []


def parse_daily_reads(data: dict[str, Any]) -> list[DailyRead]:
    """Daily meter reads from the daily-usage-history endpoint, oldest first."""
    reads: dict[date, DailyRead] = {}
    for d in _details(data):
        try:
            day = date.fromisoformat(d["measuredOn"])
            reads[day] = DailyRead(day, float(d["meterRead"]), float(d["units"]))
        except (KeyError, TypeError, ValueError):
            continue
    return [reads[day] for day in sorted(reads)]


def parse_bills(data: dict[str, Any]) -> list[Bill]:
    """Billing periods from the usage-history endpoint, oldest first; a re-bill replaces the original."""
    bills: dict[tuple[date, date], Bill] = {}
    for d in _details(data):
        try:
            start, end = date.fromisoformat(d["startDate"]), date.fromisoformat(d["endDate"])
            bills[(start, end)] = Bill(start, end, float(d["dollars"]))
        except (KeyError, TypeError, ValueError):
            continue
    return [bills[key] for key in sorted(bills, key=lambda k: k[1])]


def _daily_usage(reads: list[DailyRead]) -> dict[date, float]:
    # Read differences, not `units`: the day after a gap in the data then carries the gap's usage.
    usage = {reads[0].day: reads[0].units}
    for prev, cur in zip(reads, reads[1:]):
        diff = cur.read - prev.read
        usage[cur.day] = diff if diff >= 0 else cur.units  # meter swap
    return usage


def _daily_cost(usage: dict[date, float], bills: list[Bill]) -> dict[date, float]:
    """Spread each bill over its days by usage (evenly if none); remainder on the last day keeps totals exact."""
    cost: dict[date, float] = {}
    for bill in bills:
        days = [day for day in sorted(usage) if bill.start < day <= bill.end] or [bill.end]
        period_use = sum(usage.get(day, 0.0) for day in days)
        allocated = 0.0
        for day in days[:-1]:
            share = usage[day] / period_use if period_use else 1 / len(days)
            amount = round(bill.dollars * share, 2)
            cost[day] = cost.get(day, 0.0) + amount
            allocated += amount
        cost[days[-1]] = round(cost.get(days[-1], 0.0) + bill.dollars - allocated, 2)
    return cost


def build_statistics(
    reads: list[DailyRead], bills: list[Bill], tz: tzinfo
) -> tuple[list[StatisticData], list[StatisticData]]:
    """Rebuild both series from scratch. Same start times every run, so re-imports overwrite."""
    if not reads:
        return [], []
    usage = _daily_usage(reads)
    cost = _daily_cost(usage, bills)
    read_on = {r.day: r.read for r in reads}

    def start(day: date) -> datetime:
        return datetime.combine(day, time.min, tzinfo=tz)

    baseline = reads[0].day - timedelta(days=1)
    consumption = [StatisticData(start=start(baseline), state=reads[0].read - reads[0].units, sum=0.0)]
    money = [StatisticData(start=start(baseline), state=0.0, sum=0.0)]
    volume_total = 0.0
    for day in sorted(usage):
        volume_total = round(volume_total + usage[day], 3)
        consumption.append(StatisticData(start=start(day), state=read_on[day], sum=volume_total))
    money_total = 0.0
    for day in sorted(usage.keys() | cost.keys()):
        day_cost = round(cost.get(day, 0.0), 2)
        money_total = round(money_total + day_cost, 2)
        money.append(StatisticData(start=start(day), state=day_cost, sum=money_total))
    return consumption, money


def statistic_ids(account_id: str) -> tuple[str, str]:
    suffix = re.sub(r"[^a-z0-9_]", "_", str(account_id).lower())
    return f"{DOMAIN}:gas_consumption_{suffix}", f"{DOMAIN}:gas_cost_{suffix}"


@callback
def async_import_statistics(
    hass: HomeAssistant, account_id: str, reads: list[DailyRead], bills: list[Bill]
) -> None:
    if not reads:
        return
    consumption_id, cost_id = statistic_ids(account_id)
    consumption, cost = build_statistics(reads, bills, dt_util.get_default_time_zone())
    async_add_external_statistics(
        hass,
        StatisticMetaData(
            mean_type=StatisticMeanType.NONE,
            has_sum=True,
            name="Spire gas consumption",
            source=DOMAIN,
            statistic_id=consumption_id,
            unit_class=VolumeConverter.UNIT_CLASS,
            unit_of_measurement=UnitOfVolume.CENTUM_CUBIC_FEET,
        ),
        consumption,
    )
    async_add_external_statistics(
        hass,
        StatisticMetaData(
            mean_type=StatisticMeanType.NONE,
            has_sum=True,
            name="Spire gas cost",
            source=DOMAIN,
            statistic_id=cost_id,
            unit_class=None,
            unit_of_measurement=None,
        ),
        cost,
    )
