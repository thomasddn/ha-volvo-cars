"""Constants for the Volvo Cars integration."""

from homeassistant.const import Platform

DOMAIN = "volvo_cars"
PLATFORMS: list = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.DEVICE_TRACKER,
    Platform.IMAGE,
    Platform.LOCK,
    Platform.NUMBER,
    Platform.SENSOR,
]

ATTR_API_TIMESTAMP = "api_timestamp"
ATTR_DIRECTION = "direction"
ATTR_LAST_RESULT = "last_result"

CONF_OTP = "otp"
CONF_VCC_API_KEY = "vcc_api_key"
CONF_VIN = "vin"

DATA_BATTERY_CAPACITY = "battery_capacity_kwh"
DATA_REQUEST_COUNT = "api_request_count"

MANUFACTURER = "Volvo"

OPT_DEVICE_TRACKER_PICTURE = "device_tracker_picture"
OPT_ENERGY_CONSUMPTION_UNIT = "energy_consumption_unit"
OPT_FUEL_CONSUMPTION_UNIT = "fuel_consumption_unit"
OPT_IMG_BG_COLOR = "image_bg_color"
OPT_IMG_TRANSPARENT = "image_transparent"

OPT_UNIT_ENERGY_KWH_PER_100KM = "kwh_100km"
OPT_UNIT_ENERGY_MILES_PER_KWH = "miles_kwh"

OPT_UNIT_LITER_PER_100KM = "l_100km"
OPT_UNIT_MPG_UK = "mpg_uk"
OPT_UNIT_MPG_US = "mpg_us"


SERVICE_REFRESH_DATA = "refresh_data"
SERVICE_PARAM_DATA = "data"
SERVICE_PARAM_ENTRY = "entry"
