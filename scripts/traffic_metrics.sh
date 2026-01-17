#!/usr/bin/env bash
#
# Usage:
#   ./run_traffic_analysis.sh <path_to_traffic_csv> <device_ip> [uplink|downlink|both]
#
# Examples:
#   ./run_traffic_analysis.sh ./traffic.csv 192.168.2.2 both
#   ./run_traffic_analysis.sh /data/traffic.csv 192.168.2.2 uplink
#   ./run_traffic_analysis.sh /data/traffic.csv 192.168.2.2 downlink
#

set -euo pipefail

# ----------- ARGUMENTS -----------
if [ "$#" -lt 2 ]; then
    echo "Usage: $0 <path_to_traffic_csv> <device_ip> [uplink|downlink|both]"
    exit 1
fi

TRAFFIC_PATH="$1"
DEVICE_IP="$2"
MODE="${3:-both}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PY_SCRIPT="$(dirname "$SCRIPT_DIR")/analyze/network_traffic/traffic_analysis.py"

# ----------- VALIDATIONS -----------
if [ ! -f "$PY_SCRIPT" ]; then
    echo "ERROR: traffic_analyze.py not found in $SCRIPT_DIR"
    exit 1
fi

if [ ! -f "$TRAFFIC_PATH" ]; then
    echo "ERROR: traffic.csv not found at $TRAFFIC_PATH"
    exit 1
fi

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
echo "Device IP  : $DEVICE_IP"
echo "Mode       : $MODE"
echo "----------------------------------------"

python3 "$PY_SCRIPT" \
    --csv "$TRAFFIC_PATH" \
    --device-ip "$DEVICE_IP" \
    --top 5 \
    $UPLINK_FLAG \
    $DOWNLINK_FLAG

echo "----------------------------------------"
echo "Traffic analysis completed."
