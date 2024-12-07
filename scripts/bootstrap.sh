#!/usr/bin/env bash

set -e

cd "$(dirname "$0")/.."

# Set the path to custom_components
## This let's us have the structure we want <root>/custom_components/volvo_cars
## while at the same time have Home Assistant configuration inside <root>/config
## without resulting to symlinks.
export PYTHONPATH="${PYTHONPATH}:${PWD}/custom_components"
