"""Shared test data, shaped like real Spire API responses."""


def daily(measured_on: str, read: str, units: str) -> dict:
    return {
        "measuredOn": measured_on, "month": measured_on[5:7], "dollars": None, "units": units,
        "unitType": "CCF", "daysInPeriod": None, "meterNumber": None, "meterRead": read,
        "startDate": None, "endDate": None,
    }


def bill(start: str, end: str, dollars: str, units: str) -> dict:
    return {
        "measuredOn": end, "month": end[5:7], "dollars": dollars, "units": units, "unitType": "CCFC",
        "daysInPeriod": "3", "meterNumber": None, "meterRead": None, "startDate": start, "endDate": end,
    }


# Newest first within each year, like the API. Gap between Jan 2 and Jan 5.
DAILY = {
    "isDailyReadCustomer": True,
    "premises": [{"yearlyUsages": [
        {"year": "2026", "usageDetails": [
            daily("2026-01-06", "110.00", "2.00"),
            daily("2026-01-05", "108.00", "1.00"),
            daily("2026-01-02", "100.00", "3.00"),
            daily("2026-01-01", "97.00", "1.50"),
        ]},
    ]}],
}

# Two bills: Jan 1 (exclusive) -> Jan 2, and Jan 2 (exclusive) -> Jan 6.
MONTHLY = {
    "premises": [{"yearlyUsages": [
        {"year": "2026", "usageDetails": [
            bill("2026-01-02", "2026-01-06", "33.00", "11.000000"),
            bill("2026-01-01", "2026-01-02", "6.00", "3.000000"),
        ]},
    ]}],
}
