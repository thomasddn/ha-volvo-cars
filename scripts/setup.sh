#!/usr/bin/env bash
# Setups the repository.

set -e

# Stop on errors
cd "$(dirname "$0")/.."

# Add default vscode settings if not existing
SETTINGS_FILE=./.vscode/settings.json
SETTINGS_TEMPLATE_FILE=./.vscode/settings.default.json
if [ ! -f "$SETTINGS_FILE" ]; then
    echo "Copy $SETTINGS_TEMPLATE_FILE to $SETTINGS_FILE."
    cp "$SETTINGS_TEMPLATE_FILE" "$SETTINGS_FILE"
fi

mkdir -p config

if [ ! -n "$VIRTUAL_ENV" ]; then
  if [ -x "$(command -v uv)" ]; then
    uv venv venv
  else
    python3 -m venv venv
  fi
  source /home/vscode/.local/ha-venv/bin/activate
fi

if ! [ -x "$(command -v uv)" ]; then
  python3 -m pip install uv
fi

scripts/bootstrap.sh

hass --script ensure_config -c config

if ! grep -R "logger" config/configuration.yaml >> /dev/null;then
echo "
logger:
  default: info
  logs:
    homeassistant.components.cloud: debug
" >> config/configuration.yaml
fi
