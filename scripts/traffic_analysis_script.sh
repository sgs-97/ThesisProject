#!/usr/bin/env bash

set -e

# -----------------------------
# Usage
# -----------------------------
if [ "$#" -ne 1 ]; then
    echo "Usage: $0 <path/to/ip.json>"
    exit 1
fi

OUTPUT_FILE="$1"
# If user gives a directory, write ip.json inside it
if [[ "$OUTPUT_FILE" == */ ]]; then
    OUTPUT_FILE="${OUTPUT_FILE}ip.json"
elif [[ -d "$OUTPUT_FILE" ]]; then
    OUTPUT_FILE="${OUTPUT_FILE%/}/ip.json"
fi

OUTPUT_DIR=$(dirname "$OUTPUT_FILE")
mkdir -p "$OUTPUT_DIR"

echo "======================================"
echo " Traffic Analysis IP Config Generator"
echo "======================================"
echo "Output file: $OUTPUT_FILE"
echo

# -----------------------------
# Default values
# -----------------------------
DEFAULT_ROUTER="192.168.2.1"
DEFAULT_DEVICE="192.168.2.2"
DEFAULT_UPLINK=1
DEFAULT_DOWNLINK=0

DEFAULT_PROTOCOLS=(
    "quic"
    "tls"
    "https"
    "http"
    "http2"
    "dns"
)

echo " Default values will be used if you press ENTER"
echo

# -----------------------------
# Inputs (with defaults)
# -----------------------------

read -p "Enter Router IP [$DEFAULT_ROUTER]: " ROUTER_IP
ROUTER_IP=${ROUTER_IP:-$DEFAULT_ROUTER}

read -p "Enter Device IP [$DEFAULT_DEVICE]: " DEVICE_IP
DEVICE_IP=${DEVICE_IP:-$DEFAULT_DEVICE}

read -p "Enable uplink? (1/0) [$DEFAULT_UPLINK]: " UPLINK
UPLINK=${UPLINK:-$DEFAULT_UPLINK}

read -p "Enable downlink? (1/0) [$DEFAULT_DOWNLINK]: " DOWNLINK
DOWNLINK=${DOWNLINK:-$DEFAULT_DOWNLINK}

echo " Time Zone Configuration"
echo "--------------------------------------------------"
echo "Network traffic timestamps (pcap) are typically in UTC."
echo "ADB logs usually use the DEVICE'S LOCAL TIME ZONE."
echo
echo "To correctly align network traffic with adb logs,"
echo "please choose the IANA time zone you want to convert"
echo "network traffic into."
echo
echo "Examples:"
echo "  UTC"
echo "  America/Chicago (Default)"
echo "  America/New_York"
echo "  Europe/London"
echo
echo " Press ENTER to keep traffic timestamps in UTC."
echo

DEFAULT_TIMEZONE="America/Chicago"

read -p "Enter IANA Time Zone for traffic localization [$DEFAULT_TIMEZONE]: " TRAFFIC_TIMEZONE
TRAFFIC_TIMEZONE=${TRAFFIC_TIMEZONE:-$DEFAULT_TIMEZONE}


echo
echo "✅ Using configuration:"
echo "   Router IP  : $ROUTER_IP"
echo "   Device IP  : $DEVICE_IP"
echo "   Uplink     : $UPLINK"
echo "   Downlink   : $DOWNLINK"
echo "   Traffic Timezone: $TRAFFIC_TIMEZONE"
echo

# -----------------------------
# Protocols
# -----------------------------

# echo "Default PAYLOAD_PROTOCOLS:"
# for p in "${DEFAULT_PROTOCOLS[@]}"; do
#     echo "  - $p"
# done

# echo
# read -p "Add more payload protocols? (yes/no) [no]: " ADD_MORE
# ADD_MORE=${ADD_MORE:-no}

# EXTRA_PROTOCOLS=()

# if [[ "$ADD_MORE" =~ ^(yes|YES|y|Y)$ ]]; then
#     read -p "Enter extra protocols (comma-separated): " EXTRA_INPUT
#     IFS=',' read -ra EXTRA_PROTOCOLS <<< "$EXTRA_INPUT"
# fi

# # Merge + deduplicate
# ALL_PROTOCOLS=("${DEFAULT_PROTOCOLS[@]}" "${EXTRA_PROTOCOLS[@]}")
# UNIQUE_PROTOCOLS=()

# for proto in "${ALL_PROTOCOLS[@]}"; do
#     proto=$(echo "$proto" | xargs | tr '[:upper:]' '[:lower:]')
#     [[ -z "$proto" ]] && continue
#     [[ " ${UNIQUE_PROTOCOLS[*]} " =~ " $proto " ]] || UNIQUE_PROTOCOLS+=("$proto")
# done

# echo
# echo "Final PAYLOAD_PROTOCOLS:"
# for p in "${UNIQUE_PROTOCOLS[@]}"; do
#     echo "  - $p"
# done

# -----------------------------
# Write JSON
# -----------------------------

{
echo "{"
echo "  \"router\": \"${ROUTER_IP}\","
echo "  \"device\": \"${DEVICE_IP}\","
echo "  \"uplink\": ${UPLINK},"
echo "  \"downlink\": ${DOWNLINK},"
echo "  \"traffic_timezone\": \"${TRAFFIC_TIMEZONE}\","
echo "  \"PAYLOAD_PROTOCOLS\": ["
for ((i=0; i<${#UNIQUE_PROTOCOLS[@]}; i++)); do
    if [[ $i -lt $((${#UNIQUE_PROTOCOLS[@]} - 1)) ]]; then
        echo "    \"${UNIQUE_PROTOCOLS[$i]}\","
    else
        echo "    \"${UNIQUE_PROTOCOLS[$i]}\""
    fi
done
echo "  ]"
echo "}"
} > "$OUTPUT_FILE"

if [[ -f "$OUTPUT_FILE" ]]; then
    echo
    echo " ip.json written successfully!"
    echo " Location: $OUTPUT_FILE"
else
    echo
    echo " Failed to write ip.json. Check path/permissions:"
    echo "   $OUTPUT_FILE"
    exit 1
fi
