#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 1 ]; then
  echo "Usage: $0 <experiment_directory>"
  exit 1
fi

EXP_DIR="$(realpath "$1")"

TRAFFIC_CSV="$EXP_DIR/traffic.csv"
IP_JSON="$EXP_DIR/ip.json"
OUT_HTML="$EXP_DIR/cdf_bytes_per_hostname.html"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(realpath "$SCRIPT_DIR/../..")"

# -------------------------------
# Validation
# -------------------------------
[ -d "$EXP_DIR" ] || { echo "[ERROR] Not a directory: $EXP_DIR"; exit 1; }
[ -f "$TRAFFIC_CSV" ] || { echo "[ERROR] Missing traffic.csv"; exit 1; }
[ -f "$IP_JSON" ] || { echo "[ERROR] Missing ip.json"; exit 1; }

# -------------------------------
# Run CDF plot
# -------------------------------
echo "[INFO] Running CDF plot for directory: $EXP_DIR"

cd "$PROJECT_ROOT"

python3 -m ThesisProject.analyze.cdfs.traffic_cdf \
  --traffic-csv "$TRAFFIC_CSV" \
  --ip-json "$IP_JSON" \
  --out "$OUT_HTML"

echo "[✓] CDF HTML written to:"
echo "    $OUT_HTML"
