import argparse
import csv
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

import pandas as pd
import pyshark


GREEN = "\033[92m"
RESET = "\033[0m"


@dataclass(frozen=True)
class TrafficRow:
    timestamp: str
    src_ip: str
    dst_ip: str
    protocol: str


class PcapToCSVConverter:
    """Convert a .pcapng file into a CSV containing basic traffic metadata."""

    def __init__(self, pcap_file: Path, timezone: str) -> None:
        self.pcap_file = pcap_file
        self.timezone = timezone

    def _format_timestamp(self, epoch_seconds: float) -> str:
        utc_time = pd.to_datetime(epoch_seconds, unit="s", utc=True)
        local_time = utc_time.tz_convert(self.timezone)
        return local_time.strftime("%H:%M:%S.%f")[:-3]

    def _extract_row(self, pkt) -> Optional[TrafficRow]:
        if not hasattr(pkt, "ip"):
            return None

        try:
            timestamp = self._format_timestamp(float(pkt.frame_info.time_epoch))
            protocol = getattr(pkt, "transport_layer", None) or "OTHER"

            return TrafficRow(
                timestamp=timestamp,
                src_ip=pkt.ip.src,
                dst_ip=pkt.ip.dst,
                protocol=protocol,
            )
        except (AttributeError, ValueError, TypeError):
            return None

    def extract_rows(self) -> List[TrafficRow]:
        rows: List[TrafficRow] = []

        with pyshark.FileCapture(str(self.pcap_file), keep_packets=False) as capture:
            for pkt in capture:
                row = self._extract_row(pkt)
                if row:
                    rows.append(row)

        return rows

    @staticmethod
    def write_csv(output_csv: Path, rows: List[TrafficRow]) -> None:
        output_csv.parent.mkdir(parents=True, exist_ok=True)

        with output_csv.open(mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["timestamp", "src_ip", "dst_ip", "protocol"])
            writer.writerows([[r.timestamp, r.src_ip, r.dst_ip, r.protocol] for r in rows])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Convert a .pcapng file to CSV.\n\n"
            "Timezone conversion uses IANA timezone names.\n\n"
            "Accepted U.S. timezones:\n"
            "  America/New_York  (Eastern)\n"
            "  America/Chicago   (Central - default)\n"
            "  America/Denver    (Mountain)\n"
            "  America/Phoenix   (Arizona, no DST)\n"
            "  America/Los_Angeles (Pacific)\n"
            "  America/Anchorage (Alaska)\n"
            "  America/Adak      (Aleutian Islands)\n"
        ),
        formatter_class=argparse.RawTextHelpFormatter
    )

    parser.add_argument("pcap_file", type=Path, help="Path to input .pcapng file")
    parser.add_argument(
        "--pcap_to_csv",
        type=Path,
        required=True,
        help="Path to output CSV file"
    )
    parser.add_argument(
        "--timezone",
        type=str,
        default="America/Chicago",
        help=(
            "IANA timezone name used for timestamp conversion.\n"
            "Default: America/Chicago"
        ),
    )

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    if not args.pcap_file.exists():
        raise FileNotFoundError(f"PCAPNG file not found: {args.pcap_file}")
    if args.pcap_file.suffix.lower() != ".pcapng":
        raise ValueError("Input file must have a .pcapng extension")
    if args.pcap_to_csv.suffix.lower() != ".csv":
        raise ValueError("Output file must have a .csv extension")

    # Print green message if default timezone is used
    if args.timezone == "America/Chicago":
        print(
            f"{GREEN}No timezone provided. "
            f"Using default timezone: America/Chicago{RESET}"
        )

    converter = PcapToCSVConverter(
        pcap_file=args.pcap_file,
        timezone=args.timezone
    )

    rows = converter.extract_rows()
    converter.write_csv(args.pcap_to_csv, rows)

    print(f"Converted {args.pcap_file.name} → {args.pcap_to_csv} (timezone={args.timezone})")
