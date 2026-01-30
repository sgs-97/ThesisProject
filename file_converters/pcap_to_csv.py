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
    protocol_trees = set()

    false_protocols = set()

    with pyshark.FileCapture(pcapng_path, 
                            keep_packets=False) as capture:
        for i, pkt in enumerate(capture):
            if i % 5000 == 0:
                print(f"[pcap_to_csv] processed {i} packets")

            try:
                timestamp = pd.to_datetime(
                    float(pkt.sniff_timestamp),  # Pyshark version of pkt.frame_info.time_epoch
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
                # CSV protocol remains unchanged
                protocol = pkt.highest_layer

                # Build protocol tree separately (full layer stack)
                try:
                    layers = []
                    for layer in pkt.layers:
                        name = getattr(layer, "layer_name", "")
                        if name:
                            layers.append(name.lower())
                    protocol_tree = ":".join(layers)
                except Exception:
                    protocol_tree = str(pkt.highest_layer).lower()

                if protocol_tree:
                    protocol_trees.add(protocol_tree)
                
                # Alternatively, you could get a list of all layers
                # all_layers = list(pkt.layers)
                # protocol = " > ".join([layer.layer_name.upper() for layer in all_layers])

                # --- packet size in bytes ---
                bytes_len = None
                # frame_info.len = actual on-the-wire packet size (best for throughput)

                if hasattr(pkt, "frame_info") and hasattr(pkt.frame_info, "len"):
                    bytes_len = int(pkt.frame_info.len)
                elif hasattr(pkt, "length"):
                    bytes_len = int(pkt.length)
                elif hasattr(pkt, "frame_info") and hasattr(pkt.frame_info, "cap_len"):
                    bytes_len = int(pkt.frame_info.cap_len)
                else:
                    bytes_len = 0

                                # ---------------- mark important vs non-important (no filtering) ----------------
                important = True
                reason = ""

                # Normalize protocol name for consistent checks
                proto_u = str(protocol).upper()

                # Always non-data/control protocols
                if proto_u in {"ICMP", "ICMPV6", "DNS", "MDNS", "ARP"}:
                    important = False
                    reason = f"{proto_u.lower()}_control"

                # TCP overhead classification (ACK-only / handshake / teardown)
                elif hasattr(pkt, "tcp"):
                    tcp_len = 0
                    try:
                        if hasattr(pkt.tcp, "len"):
                            tcp_len = int(pkt.tcp.len)
                    except Exception:
                        tcp_len = 0

                    syn = getattr(pkt.tcp, "flags_syn", "0")
                    fin = getattr(pkt.tcp, "flags_fin", "0")
                    rst = getattr(pkt.tcp, "flags_reset", "0")
                    ack = getattr(pkt.tcp, "flags_ack", "0")

                    # SYN/FIN/RST are control (setup/teardown)
                    if syn == "1":
                        important = False
                        reason = "tcp_handshake_syn"
                    elif fin == "1" or rst == "1":
                        important = False
                        reason = "tcp_teardown_fin_rst"
                    # ACK-only: ack flag set but no TCP payload
                    elif ack == "1" and tcp_len == 0:
                        important = False
                        reason = "tcp_ack_only"

                    # Retransmission flags (if tshark exposes them via pyshark)
                    if important:
                        for attr, label in [
                            ("analysis_retransmission", "tcp_retransmission"),
                            ("analysis_fast_retransmission", "tcp_fast_retransmission"),
                            ("analysis_spurious_retransmission", "tcp_spurious_retransmission"),
                        ]:
                            if hasattr(pkt.tcp, attr):
                                important = False
                                reason = label
                                break

                # TLS handshake classification (keep TLS application data as important)
                if important and hasattr(pkt, "tls"):
                    # record_content_type: 22=handshake, 23=application_data (if available)
                    ctype = getattr(pkt.tls, "record_content_type", None)
                    if ctype is not None and str(ctype) == "22":
                        important = False
                        reason = "tls_handshake"

                # QUIC handshake classification (best-effort): long header usually = Initial/Handshake/0-RTT
                if important and hasattr(pkt, "quic"):
                    header_form = getattr(pkt.quic, "header_form", None)  # often 1=long, 0=short
                    if header_form is not None and str(header_form) == "1":
                        important = False
                        reason = "quic_long_header_handshake"

                if not important:
                    false_protocols.add(str(protocol))
                
                records.append([
                    timestamp,
                    src_ip,
                    dst_ip,
                    protocol,
                    bytes_len,
                    important,
                    reason
                ])

            except Exception as e:
                # Optional: Print error for debugging
                # print(f"Error processing packet {pkt.number}: {e}")
                continue

    return records, protocol_trees, false_protocols


def write_csv(records, output_csv: str):
    """
    Write packet records to traffic.csv.
    """
    with open(output_csv, mode="w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp", "src_ip", "dst_ip", "protocol","bytes","important", "non_important_reason"])
        writer.writerows(records)

def write_unique_protocol_trees(protocol_trees, output_txt: str):
    """
    Write unique protocol trees to a text file.
    """
    with open(output_txt, "w", encoding="utf-8") as f:
        for tree in sorted(protocol_trees):
            f.write(tree + "\n")

    print(f"protocol_trees.txt written to: {output_txt}")
    print(f"Unique protocol trees: {len(protocol_trees)}")

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

    records, protocol_trees,false_protocols = extract_packet_data(pcapng_path)
    write_csv(records, output_csv)

    protocol_tree_txt = os.path.join(directory, "traffic_protocol_trees.txt")
    write_unique_protocol_trees(protocol_trees, protocol_tree_txt)

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
