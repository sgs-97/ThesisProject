#!/usr/bin/env bash
#
# Usage:
#   ./run_traffic_analysis.sh <path_to_traffic_csv> [device_ip] [uplink|downlink|both]
#

set -euo pipefail

# ----------- ARGUMENTS -----------
if [ "$#" -lt 1 ]; then
    echo "Usage: $0 <path_to_traffic_csv> [device_ip] [uplink|downlink|both]"
    exit 1
fi

TRAFFIC_PATH="$1"

# Decide whether $2 is device_ip or mode
if [[ "${2:-}" =~ ^(uplink|downlink|both)$ ]]; then
    DEVICE_IP=""
    MODE="${2:-both}"
else
    DEVICE_IP="${2:-}"
    MODE="${3:-both}"
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PY_SCRIPT="$(dirname "$SCRIPT_DIR")/analyze/metrics/traffic_analysis.py"

# ----------- VALIDATIONS -----------
if [ ! -f "$PY_SCRIPT" ]; then
    echo "ERROR: traffic_analysis.py not found at $PY_SCRIPT"
    exit 1
fi

# Allow passing either a file or a directory
if [ -d "$TRAFFIC_PATH" ]; then
    TRAFFIC_PATH="$TRAFFIC_PATH/traffic.csv"
fi

# if [ ! -f "$TRAFFIC_PATH" ]; then
#     echo "ERROR: traffic.csv not found at $TRAFFIC_PATH"
#     exit 1
# fi

# ----------- RUN CDF FIRST -----------
echo "----------------------------------------"
echo "Running CDF analysis..."

CDF_SCRIPT="$SCRIPT_DIR/traffic_cdf_by_hostname.sh"

if [ ! -f "$CDF_SCRIPT" ]; then
    echo "ERROR: traffic_cdf_by_hostname.sh not found at $CDF_SCRIPT"
    exit 1
fi

# Pass experiment directory (folder containing traffic.csv)
EXP_DIR="$(dirname "$TRAFFIC_PATH")"

"$CDF_SCRIPT" "$EXP_DIR"

echo "CDF analysis completed."
echo "----------------------------------------"

# ----------- MODE HANDLING -----------
UPLINK_FLAG=""
DOWNLINK_FLAG=""

case "$MODE" in
    uplink)
        UPLINK_FLAG="--uplink"
        ;;
    downlink)
        DOWNLINK_FLAG="--downlink"
        ;;
    both)
        UPLINK_FLAG="--uplink"
        DOWNLINK_FLAG="--downlink"
        ;;
    *)
        echo "ERROR: Invalid mode '$MODE'. Use uplink | downlink | both"
        exit 1
        ;;
esac

# ----------- EXECUTION -----------
echo "Running traffic analysis..."
echo "CSV        : $TRAFFIC_PATH"
if [ -n "$DEVICE_IP" ]; then
  echo "Device IP  : $DEVICE_IP"
else
  echo "Device IP  : (from ip.json)"
fi

echo "Mode       : $MODE"
echo "----------------------------------------"

CMD=(
  python3 "$PY_SCRIPT"
  --csv "$TRAFFIC_PATH"
)

# Only pass device-ip if provided
if [ -n "$DEVICE_IP" ]; then
    CMD+=(--device-ip "$DEVICE_IP")
fi

"${CMD[@]}"
EXIT_CODE=$?
echo "Python exit code: $EXIT_CODE"


echo "----------------------------------------"
echo "Traffic analysis completed."
