# TCP 3-way handshake raw-packet lab

このディレクトリに置くPythonプログラムは、次の2つです。

- `raw_tcp_no_ack.py`: 隔離ラボ内でSYNを作成して送り、最終ACKを返さずにserver側のSYN-ACK再送を確認します。
- `tcp_server.py`: 1つのTCP接続を受け付けるサーバーです。

`raw_tcp_no_ack.py` は `veth-client` と `10.0.0.1 -> 10.0.0.2:50000` に固定されており、隔離されたQEMU環境の `client` namespace内でrootとして実行します。

## QEMU環境

Alpine Linuxの固定リリースを使う手順は[`qemu-alpine/README.md`](qemu-alpine/README.md)を参照してください。起動時に `client` / `server` namespaceとvethを自動作成します。SSH管理NICはQEMU user-mode networkingで外部接続を制限し、実験用vethネットワークとは分離しています。
