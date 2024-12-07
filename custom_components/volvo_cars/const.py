"""Constants for the Volvo Cars integration."""

from homeassistant.const import Platform

DOMAIN = "volvo_cars"
PLATFORMS: list = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.DEVICE_TRACKER,
    Platform.IMAGE,
    Platform.LOCK,
    Platform.SENSOR,
]

ATTR_API_TIMESTAMP = "api_timestamp"
ATTR_DIRECTION = "direction"
ATTR_LAST_RESULT = "last_result"

CONF_OTP = "otp"
CONF_REFRESH_TOKEN = "refresh_token"
CONF_VCC_API_KEY = "vcc_api_key"
CONF_VIN = "vin"

MANUFACTURER = "Volvo"
