#!/usr/bin/env python3
"""A one-connection TCP echo-style server."""

import argparse
import socket

HOST = "127.0.0.1"
DEFAULT_PORT = 50000


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Listen for one TCP client on the selected address."
    )
    parser.add_argument("--host", default=HOST, help="address to listen on")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    args = parser.parse_args()

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((args.host, args.port))
        server.listen(1)
        address, port = server.getsockname()
        print(f"Listening on {address}:{port}; waiting for one connection...")

        connection, peer = server.accept()
        with connection:
            print(f"Accepted connection from {peer[0]}:{peer[1]}")
            data = connection.recv(4096)
            if data:
                print(f"Received: {data.decode('utf-8', errors='replace').rstrip()}")
                connection.sendall(b"Received: " + data)
            else:
                print("Client closed the connection without sending data.")


if __name__ == "__main__":
    main()
