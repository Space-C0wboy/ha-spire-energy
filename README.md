> ⚠️ **Personal project — not a professional developer.** These integrations were built for personal use via AI-assisted "vibe coding" (Claude). They work for my setup but may have rough edges. Use at your own risk, PRs welcome, and please be kind in issues.

# Spire Energy — Home Assistant Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)

A [HACS](https://hacs.xyz/) custom integration for [Spire Energy](https://www.spireenergy.com/) that pulls daily natural gas usage and meter readings into Home Assistant's Energy Dashboard.

---

## Features

- **Cumulative meter read** — use `Gas Meter Reading` in the HA Energy Dashboard for long-term tracking
- **Daily granularity** — if you have a smart meter (AMI), today's CCF usage is available
- Automatically re-authenticates when sessions expire
- **No extra dependencies** — uses only `aiohttp` (already bundled with Home Assistant)

---

## Sensors

| Sensor | Entity ID | Unit | Device Class | State Class | Description |
|--------|-----------|------|--------------|-------------|-------------|
| Spire Gas Meter Reading | `sensor.spire_gas_meter_reading` | CCF | `gas` | `total_increasing` | Cumulative meter read. Primary sensor for HA Energy dashboard. |
| Spire Gas Usage Today | `sensor.spire_gas_usage_today` | CCF | `gas` | `measurement` | Today's consumption (AMI smart meters only — may show `unknown` on standard meters) |

> **Note:** Entity IDs may vary if you have renamed entities. The names above are the defaults.

### Not Included: Billing Sensors

Balance due, payment due date, and bill history were explored but the Spire billing API lives on a separate subdomain (`www.myaccount.spire.com`) with unreliable DNS resolution. Those sensors were omitted to avoid flapping states. If that endpoint stabilizes in a future Spire update, billing sensors would be straightforward to add.

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

**Check logs**
- Settings → System → Logs, filter by `spire_energy`

---

## License

MIT
