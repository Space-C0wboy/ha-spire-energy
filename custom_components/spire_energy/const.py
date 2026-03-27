"""Constants for Spire Energy integration."""

DOMAIN = "spire_energy"
CONF_EMAIL = "email"
CONF_PASSWORD = "password"
CONF_UTILITY_ACCOUNT_ID = "utility_account_id"
CONF_SA_ID = "sa_id"

BASE_URL = "https://myaccount.spireenergy.com"
API_BASE = f"{BASE_URL}/o/rest"

# Endpoints
EP_ACCOUNTS = f"{API_BASE}/accounts/api/v1/accounts"
EP_ACCOUNT = f"{API_BASE}/accounts/api/v1/account/{{account_id}}"
EP_DAILY_USAGE = f"{API_BASE}/accounts/api/v1/usage-graphical-history/{{account_id}}/daily-usage-history"
EP_MONTHLY_USAGE = f"{API_BASE}/accounts/api/v1/usage-graphical-history/{{account_id}}/usage-history"
EP_BALANCE = f"{API_BASE}/accounts/api/v1/account/{{account_id}}/due-balance-alert"
EP_MFA_VALIDATE = f"{API_BASE}/mfa/v1.0/validate"

# Sensor names
SENSOR_GAS_METER = "gas_meter_reading"
SENSOR_GAS_TODAY = "gas_usage_today"
SENSOR_GAS_BALANCE = "gas_balance"
SENSOR_CURRENT_BALANCE = "current_balance"
SENSOR_NEXT_BILL_DATE = "next_bill_date"
SENSOR_LAST_BILL_AMOUNT = "last_bill_amount"
SENSOR_LAST_BILL_DATE = "last_bill_date"

# Update interval
UPDATE_INTERVAL_HOURS = 6

# Login
LOGIN_URL = BASE_URL
LOGIN_TIMEOUT = 30_000  # ms for Playwright
