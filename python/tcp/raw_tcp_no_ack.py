#!/usr/bin/env python3
"""Send a SYN but no final ACK in the isolated QEMU TCP lab.

This is intentionally fixed to client veth 10.0.0.1 -> server 10.0.0.2:50000.
It crafts only the initial SYN and observes SYN-ACK retransmissions; it is not
a general TCP client. Run as root inside the lab's client network namespace.
"""

import fcntl
import secrets
import socket
import struct
import time

CLIENT_IFACE = "veth-client"
CLIENT_IP = "10.0.0.1"
SERVER_IP = "10.0.0.2"
CLIENT_PORT = 40000
SERVER_PORT = 50000
CAPTURE_SECONDS = 15
SIOCGIFADDR = 0x8915
ETH_P_IP = 0x0800
TCP_SYN = 0x02
TCP_ACK = 0x10
TCP_RST = 0x04
UINT32_MASK = 0xFFFFFFFF


def internet_checksum(data: bytes) -> int:
    if len(data) & 1:
        data += b"\x00"
    words = struct.unpack(f"!{len(data) // 2}H", data)
    total = sum(words)
    while total >> 16:
        total = (total & 0xFFFF) + (total >> 16)
    return ~total & 0xFFFF


def verify_lab_interface() -> None:
    try:
        socket.if_nametoindex(CLIENT_IFACE)
    except OSError as error:
        raise SystemExit(
            f"Required lab interface {CLIENT_IFACE!r} is missing"
        ) from error

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
        request = struct.pack("256s", CLIENT_IFACE.encode("ascii"))
        response = fcntl.ioctl(probe.fileno(), SIOCGIFADDR, request)
    actual_ip = socket.inet_ntoa(response[20:24])
    if actual_ip != CLIENT_IP:
        raise SystemExit(
            f"Refusing to run: {CLIENT_IFACE} has {actual_ip}, expected lab IP {CLIENT_IP}"
        )


def build_packet(seq: int, ack: int, flags: int, ip_id: int) -> bytes:
    source = socket.inet_aton(CLIENT_IP)
    destination = socket.inet_aton(SERVER_IP)

    tcp_header = struct.pack(
        "!HHIIHHHH",
        CLIENT_PORT,
        SERVER_PORT,
        seq & UINT32_MASK,
        ack & UINT32_MASK,
        (5 << 12) | flags,
        64240,
        0,
        0,
    )
    pseudo_header = (
        source
        + destination
        + struct.pack("!BBH", 0, socket.IPPROTO_TCP, len(tcp_header))
    )
    tcp_checksum = internet_checksum(pseudo_header + tcp_header)
    tcp_header = struct.pack(
        "!HHIIHHHH",
        CLIENT_PORT,
        SERVER_PORT,
        seq & UINT32_MASK,
        ack & UINT32_MASK,
        (5 << 12) | flags,
        64240,
        tcp_checksum,
        0,
    )

    ip_header = struct.pack(
        "!BBHHHBBH4s4s",
        0x45,
        0,
        20 + len(tcp_header),
        ip_id,
        0,
        64,
        socket.IPPROTO_TCP,
        0,
        source,
        destination,
    )
    ip_checksum = internet_checksum(ip_header)
    ip_header = struct.pack(
        "!BBHHHBBH4s4s",
        0x45,
        0,
        20 + len(tcp_header),
        ip_id,
        0,
        64,
        socket.IPPROTO_TCP,
        ip_checksum,
        source,
        destination,
    )
    return ip_header + tcp_header


def parse_tcp_frame(frame: bytes) -> tuple[str, str, int, int, int, int, int] | None:
    if len(frame) < 14 + 20 or struct.unpack_from("!H", frame, 12)[0] != ETH_P_IP:
        return None

    ip_start = 14
    version_ihl = frame[ip_start]
    ip_header_len = (version_ihl & 0x0F) * 4
    if version_ihl >> 4 != 4 or frame[ip_start + 9] != socket.IPPROTO_TCP:
        return None

    tcp_start = ip_start + ip_header_len
    if len(frame) < tcp_start + 20:
        return None

    source_ip = socket.inet_ntoa(frame[ip_start + 12 : ip_start + 16])
    destination_ip = socket.inet_ntoa(frame[ip_start + 16 : ip_start + 20])
    source_port, destination_port, seq, ack, offset_flags, window, _, _ = (
        struct.unpack_from("!HHIIHHHH", frame, tcp_start)
    )
    flags = offset_flags & 0x01FF
    return (
        source_ip,
        destination_ip,
        source_port,
        destination_port,
        seq,
        ack,
        (flags << 16) | window,
    )


def main() -> None:
    verify_lab_interface()
    client_isn = secrets.randbits(32)
    client_next = (client_isn + 1) & UINT32_MASK

    with (
        socket.socket(
            socket.AF_PACKET, socket.SOCK_RAW, socket.htons(ETH_P_IP)
        ) as capture,
        socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_RAW) as sender,
    ):
        capture.bind((CLIENT_IFACE, 0))
        sender.setsockopt(
            socket.SOL_SOCKET, socket.SO_BINDTODEVICE, CLIENT_IFACE.encode() + b"\x00"
        )
        sender.setsockopt(socket.IPPROTO_IP, socket.IP_HDRINCL, 1)

        syn = build_packet(client_isn, 0, TCP_SYN, secrets.randbits(16))
        sender.sendto(syn, (SERVER_IP, SERVER_PORT))
        print(
            f"Sent custom SYN: {CLIENT_IP}:{CLIENT_PORT} -> {SERVER_IP}:{SERVER_PORT}, "
            f"seq={client_isn}"
        )
        print("Waiting for the server's SYN-ACK...")

        deadline = time.monotonic() + CAPTURE_SECONDS
        synack_count = 0

        while time.monotonic() < deadline:
            capture.settimeout(min(1.0, deadline - time.monotonic()))
            try:
                frame, _ = capture.recvfrom(65535)
            except TimeoutError:
                continue

            packet = parse_tcp_frame(frame)
            if packet is None:
                continue
            (
                source_ip,
                destination_ip,
                source_port,
                destination_port,
                server_seq,
                server_ack,
                rest,
            ) = packet
            flags = rest >> 16
            if (
                source_ip != SERVER_IP
                or destination_ip != CLIENT_IP
                or source_port != SERVER_PORT
                or destination_port != CLIENT_PORT
                or (flags & (TCP_SYN | TCP_ACK | TCP_RST)) != (TCP_SYN | TCP_ACK)
                or server_ack != client_next
            ):
                continue

            synack_count += 1
            elapsed = CAPTURE_SECONDS - max(0, deadline - time.monotonic())
            label = "initial SYN-ACK" if synack_count == 1 else "SYN-ACK retransmission"
            print(
                f"Received {label} #{synack_count} at +{elapsed:.1f}s, seq={server_seq}"
            )

            if synack_count == 1:
                print("Not sending the final ACK; waiting for SYN-ACK retransmissions.")

    if synack_count == 0:
        raise SystemExit(
            "No matching SYN-ACK received; check the listener and veth setup"
        )
    if synack_count < 2:
        raise SystemExit("No SYN-ACK retransmission observed during the capture window")
    print(
        f"Observed {synack_count - 1} SYN-ACK retransmission(s) without sending an ACK."
    )


if __name__ == "__main__":
    main()
