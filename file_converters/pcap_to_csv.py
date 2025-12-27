import argparse
import csv
import os
import pyshark
import pandas as pd


def find_single_pcapng(directory: str) -> str:
    """
    Find exactly one .pcapng file in the given directory.
    """
    if not os.path.isdir(directory):
        raise NotADirectoryError(f"Not a directory: {directory}")

    pcapng_files = [
        f for f in os.listdir(directory)
        if f.lower().endswith(".pcapng")
    ]

    if not pcapng_files:
        raise FileNotFoundError("No .pcapng file found in directory")

    if len(pcapng_files) > 1:
        raise ValueError("More than one .pcapng file found in directory")

    return os.path.join(directory, pcapng_files[0])


def extract_packet_data(pcapng_path: str):
    """
    Extract timestamp, src_ip, dst_ip, protocol from pcapng - ALL PROTOCOLS
    """
    records = []

    with pyshark.FileCapture(pcapng_path, keep_packets=False) as capture:
        for pkt in capture:
            try:
                timestamp = pd.to_datetime(
                    float(pkt.frame_info.time_epoch),
                    unit="s",
                    utc=True
                ).strftime("%H:%M:%S.%f")[:-3]

                # Get source and destination IPs from various layers
                src_ip = ""
                dst_ip = ""
                
                # Check for IP layer (IPv4)
                if hasattr(pkt, 'ip'):
                    src_ip = pkt.ip.src
                    dst_ip = pkt.ip.dst
                # Check for IPv6 layer
                elif hasattr(pkt, 'ipv6'):
                    src_ip = pkt.ipv6.src
                    dst_ip = pkt.ipv6.dst
                # Check for other network layers that might have addresses
                elif hasattr(pkt, 'eth'):
                    src_ip = pkt.eth.src
                    dst_ip = pkt.eth.dst
                # Check for ARP
                elif hasattr(pkt, 'arp'):
                    src_ip = pkt.arp.src_proto_ipv4 if hasattr(pkt.arp, 'src_proto_ipv4') else pkt.arp.src_hw_mac
                    dst_ip = pkt.arp.dst_proto_ipv4 if hasattr(pkt.arp, 'dst_proto_ipv4') else pkt.arp.dst_hw_mac

                # Get the protocol - use highest_layer to capture ALL protocols
                protocol = pkt.highest_layer
                
                # Alternatively, you could get a list of all layers
                # all_layers = list(pkt.layers)
                # protocol = " > ".join([layer.layer_name.upper() for layer in all_layers])
                
                records.append([
                    timestamp,
                    src_ip,
                    dst_ip,
                    protocol
                ])

            except Exception as e:
                # Optional: Print error for debugging
                # print(f"Error processing packet {pkt.number}: {e}")
                continue

    return records


def write_csv(records, output_csv: str):
    """
    Write packet records to traffic.csv.
    """
    with open(output_csv, mode="w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp", "src_ip", "dst_ip", "protocol"])
        writer.writerows(records)


def main():
    parser = argparse.ArgumentParser(
        description="Read the only pcapng file in a directory and write traffic.csv"
    )
    parser.add_argument(
        "directory_path",
        type=str,
        help="Path to directory containing exactly one .pcapng file"
    )

    args = parser.parse_args()

    directory = os.path.abspath(args.directory_path)
    pcapng_path = find_single_pcapng(directory)

    output_csv = os.path.join(directory, "traffic.csv")

    records = extract_packet_data(pcapng_path)
    write_csv(records, output_csv)

    print(f"PCAPNG file read: {pcapng_path}")
    print(f"traffic.csv written to: {output_csv}")
    print(f"Total packets processed: {len(records)}")
    
    # Optional: Print unique protocols found
    if records:
        protocols = set([record[3] for record in records])
        print(f"Unique protocols found: {len(protocols)}")
        print("Protocols:", ", ".join(sorted(protocols)))


if __name__ == "__main__":
    main()




# #!/usr/bin/env python3
# import argparse
# import csv
# from dataclasses import dataclass
# from pathlib import Path
# from typing import List

# import pandas as pd
# import pyshark

# GREEN = "\033[92m"
# RESET = "\033[0m"


# @dataclass(frozen=True)
# class TrafficRow:
#     timestamp: str
#     src_ip: str
#     dst_ip: str
#     protocol: str


# def resolve_pcapng(pcap_path: Path) -> Path:
#     """
#     Accepts either:
#       - a .pcapng file path
#       - a directory containing at least one .pcapng file (first match is used)
#     Returns a Path to the chosen .pcapng file.
#     """
#     if not pcap_path.exists():
#         raise FileNotFoundError(f"pcap_path not found: {pcap_path}")

#     if pcap_path.is_file():
#         if pcap_path.suffix.lower() != ".pcapng":
#             raise ValueError("Input file must have a .pcapng extension")
#         return pcap_path

#     if pcap_path.is_dir():
#         for f in pcap_path.iterdir():
#             if f.is_file() and f.name.lower().endswith(".pcapng"):
#                 return f
#         raise FileNotFoundError(f"No .pcapng found in directory: {pcap_path}")

#     raise FileNotFoundError(f"pcap_path not found: {pcap_path}")


# class PcapToCSVConverter:
#     """Convert a .pcapng file into a CSV containing basic traffic metadata."""

#     def __init__(self, pcap_file: Path, timezone: str) -> None:
#         self.pcap_file = pcap_file
#         self.timezone = timezone

#     def extract_rows(self) -> List[TrafficRow]:
#         """
#         Uses the same logic you had working:
#           - convert pkt.frame_info.time_epoch to local timezone
#           - keep src/dst IP
#           - protocol uses pkt.transport_layer (TCP/UDP) or OTHER
#         """
#         rows: List[TrafficRow] = []

#         with pyshark.FileCapture(str(self.pcap_file), keep_packets=False) as capture:
#             for pkt in capture:
#                 try:
#                     utc_time = pd.to_datetime(float(pkt.frame_info.time_epoch), unit="s", utc=True)
#                     local_time = utc_time.tz_convert(self.timezone)
#                     time_str = local_time.strftime("%H:%M:%S.%f")[:-3]
#                     highest = getattr(pkt, "highest_layer", None)
#                     if highest:
#                         protocol = str(highest).lower()
#                     else:
#                         protocol = (str(pkt.transport_layer).lower() if hasattr(pkt, "transport_layer") else "other")

#                     rows.append(
#                         TrafficRow(
#                             timestamp=time_str,
#                             src_ip=pkt.ip.src,
#                             dst_ip=pkt.ip.dst,
#                             protocol=protocol,
#                         )
#                     )
#                 except AttributeError:
#                     # missing pkt.ip / pkt.frame_info etc.
#                     continue
#                 except (ValueError, TypeError):
#                     continue

#         return rows

#     @staticmethod
#     def write_csv(output_csv: Path, rows: List[TrafficRow]) -> None:
#         # If user passed a directory, default to <dir>/traffic.csv
#         if output_csv.exists() and output_csv.is_dir():
#             output_csv = output_csv / "traffic.csv"
#         elif str(output_csv).endswith("/") or str(output_csv).endswith("\\"):
#             # Path(".../") might not exist yet; treat as directory intent
#             output_csv = output_csv / "traffic.csv"

#         if output_csv.suffix.lower() != ".csv":
#             raise ValueError(f"Output must be a .csv file path (got: {output_csv})")

#         output_csv.parent.mkdir(parents=True, exist_ok=True)

#         with output_csv.open(mode="w", newline="", encoding="utf-8") as f:
#             writer = csv.writer(f)
#             writer.writerow(["timestamp", "src_ip", "dst_ip", "protocol"])
#             writer.writerows([[r.timestamp, r.src_ip, r.dst_ip, r.protocol] for r in rows])


# def parse_args() -> argparse.Namespace:
#     parser = argparse.ArgumentParser(
#         description=(
#             "Convert a .pcapng file to CSV.\n\n"
#             "You can pass either a .pcapng file or a directory containing a .pcapng.\n\n"
#             "Timezone conversion uses IANA timezone names.\n\n"
#             "Accepted U.S. timezones:\n"
#             "  America/New_York  (Eastern)\n"
#             "  America/Chicago   (Central - default)\n"
#             "  America/Denver    (Mountain)\n"
#             "  America/Phoenix   (Arizona, no DST)\n"
#             "  America/Los_Angeles (Pacific)\n"
#             "  America/Anchorage (Alaska)\n"
#             "  America/Adak      (Aleutian Islands)\n"
#         ),
#         formatter_class=argparse.RawTextHelpFormatter,
#     )

#     parser.add_argument(
#         "pcap_path",
#         type=Path,
#         help="Path to input .pcapng file OR a directory containing a .pcapng file",
#     )
#     parser.add_argument(
#         "--pcap_to_csv",
#         type=Path,
#         required=True,
#         help="Path to output CSV file (e.g., /path/to/traffic.csv). If a directory is provided, traffic.csv will be created inside it.",
#     )
#     parser.add_argument(
#         "--timezone",
#         type=str,
#         default="America/Chicago",
#         help=(
#             "IANA timezone name used for timestamp conversion.\n"
#             "Default: America/Chicago"
#         ),
#     )

#     return parser.parse_args()


# if __name__ == "__main__":
#     args = parse_args()

#     # Print green message if default timezone is used
#     if args.timezone == "America/Chicago":
#         print(f"{GREEN}No timezone provided. Using default timezone: America/Chicago{RESET}")

#     pcap_file = resolve_pcapng(args.pcap_path)

#     converter = PcapToCSVConverter(pcap_file=pcap_file, timezone=args.timezone)

#     rows = converter.extract_rows()
#     converter.write_csv(args.pcap_to_csv, rows)

#     # Determine final output path for display (in case user passed a directory)
#     out_path = args.pcap_to_csv
#     if out_path.exists() and out_path.is_dir():
#         out_path = out_path / "traffic.csv"

#     print(f"Converted {pcap_file.name} → {out_path} (timezone={args.timezone})")
