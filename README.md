> ⚠️ **Personal project — not a professional developer.** These integrations were built for personal use via AI-assisted "vibe coding" (Claude). They work for my setup but may have rough edges. Use at your own risk, PRs welcome, and please be kind in issues.

# Spire Energy — Home Assistant Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)

A [HACS](https://hacs.xyz/) custom integration for [Spire Energy](https://www.spireenergy.com/) that pulls natural gas usage, meter readings, and billing information into Home Assistant.

---

## Features

- **Cumulative meter read** — use `Gas Meter Reading` in the HA Energy Dashboard for long-term tracking
- **Daily granularity** — if you have a smart meter (AMI), today's CCF usage is available
- **Billing sensors** — current balance, next bill date, last bill amount and date
- Automatically re-authenticates when sessions expire
- **No extra dependencies** — uses only `aiohttp` (already bundled with Home Assistant)

---

## Sensors

| Sensor | Entity ID | Unit | Device Class | State Class | Description |
|--------|-----------|------|--------------|-------------|-------------|
| Spire Gas Meter Reading | `sensor.spire_gas_meter_reading` | CCF | `gas` | `total_increasing` | Cumulative meter read. Primary sensor for HA Energy dashboard. |
| Spire Gas Usage Today | `sensor.spire_gas_usage_today` | CCF | `gas` | `measurement` | Today's consumption (AMI smart meters only — may show `unknown` on standard meters) |
| Spire Current Balance | `sensor.spire_current_balance` | USD | `monetary` | `total` | Current amount due on your account |
| Spire Next Bill Date | `sensor.spire_next_bill_date` | — | — | — | Date your next bill is due |
| Spire Last Bill Amount | `sensor.spire_last_bill_amount` | USD | `monetary` | `measurement` | Amount of your most recent bill |
| Spire Last Bill Date | `sensor.spire_last_bill_date` | — | — | — | Date your most recent bill was issued |

> **Note:** Entity IDs may vary if you have renamed entities. The names above are the defaults.

---

## Installation

### Via HACS (Recommended)

1. Open HACS → Integrations → ⋮ → Custom repositories
2. Add `https://github.com/Space-C0wboy/ha-spire-energy` as type **Integration**
3. Click **Download**
4. Restart Home Assistant

### Manual

1. Copy `custom_components/spire_energy/` to your HA `custom_components/` directory
2. Restart Home Assistant

---

## Configuration

1. Go to **Settings → Devices & Services → Add Integration**
2. Search for **Spire Energy**
3. Enter your [myaccount.spireenergy.com](https://myaccount.spireenergy.com) email and password

---

## Energy Dashboard Setup

1. Go to **Settings → Dashboards → Energy**
2. Under **Gas consumption**, click **Add gas source**
3. Select **Spire Gas Meter Reading**
4. HA will track cumulative CCF and calculate cost if you enter your rate

> **Note:** 1 CCF = 100 cubic feet of natural gas ≈ 1.02 therms

---

## Data Granularity

- **Daily reads**: Available if your account has an AMI smart meter (`is_daily_read_customer: true`)
- **Update frequency**: Every 6 hours (data typically updates once daily)
- **Billing data**: Updates every 6 hours alongside meter data

---

## Supported Regions

Alabama, Missouri, Mississippi (all Spire service territories)

---

## Troubleshooting

**`invalid_auth` on setup**
- Verify your credentials work at [myaccount.spireenergy.com](https://myaccount.spireenergy.com)
- Use your email address (not a username)

**`sensor.spire_gas_usage_today` stays unknown**
- This sensor only populates if your meter is an AMI smart meter. Standard meters don't report daily consumption.

**Billing sensors show `unknown`**
- Billing data is fetched from the same session as meter data. If billing sensors are unavailable, check the HA logs for errors under `spire_energy`. A re-authentication may be needed.

**Check logs**
- Settings → System → Logs, filter by `spire_energy`

---

## License

MIT
