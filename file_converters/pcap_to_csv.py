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
