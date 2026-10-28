# QEMU 上の最小 Alpine TCP 実験 Linux

Alpine Linux 3.24.3 の x86_64 minirootfsにPython 3、`iproute2`、`iptables`、`tcpdump`、`openssh-server`などを入れたinitramfsを作り、QEMUで起動します。

管理用NICはQEMU user-mode networkingの `restrict=on` で制限し、SSHポートだけをホストのloopbackへ転送します。実験用veth namespaceは管理NICから分離されています。

## 1. ホストの準備

Debian / Ubuntuで実行します。

```sh
sudo apt update
sudo apt install ca-certificates cpio coreutils curl gzip grep openssh-client qemu-system-x86 sudo tar util-linux
```

SSH接続用の鍵を作成します。既にこの鍵があれば作成をスキップしてください。

```sh
ssh-keygen -t ed25519 -f ~/.ssh/tcp-lab -C qemu-tcp-lab
```

## 2. Alpineイメージをビルドして起動

```sh
cd python/tcp/qemu-alpine
```

```sh
SSH_PUBKEY_FILE="$HOME/.ssh/tcp-lab.pub" ./build.sh
```

```sh
./run-qemu.sh
```

ビルドにはネットワーク接続とroot権限が必要です。QEMUは512 MiBで起動します。

## 3. SSHシェルを開く

ホスト側のターミナルで実行します。server、capture、client用に3つのSSHターミナルを開いてください。

```sh
ssh -i ~/.ssh/tcp-lab -p 2222 root@127.0.0.1
```

認証は公開鍵のみです。ポート転送は `127.0.0.1:2222` に限定され、ゲストから外部ネットワークへ接続できません。

## 4. namespaceを確認

SSHターミナル1で実行します。namespaceはVM起動時に自動作成されています。

```sh
ip netns list
```

`client` と `server` が表示されることを確認します。clientのアドレスは `10.0.0.1`、serverは `10.0.0.2` です。

## 5. serverを起動

SSHターミナル1で、再送回数を減らしてからserverをバックグラウンド起動します。

```sh
ip netns exec server sh -c 'echo 3 > /proc/sys/net/ipv4/tcp_synack_retries'
```

```sh
ip netns exec server python3 /root/tcp-lab/tcp_server.py --host 10.0.0.2 >/tmp/tcp-server.log 2>&1 &
```

```sh
SERVER_PID=$!
```

## 6. pcapの取得を開始

SSHターミナル2で実行し、キャプチャを開始したままにします。

```sh
ip netns exec server tcpdump -n -i veth-server -s 0 -U -w /tmp/raw_tcp_no_ack.pcap 'tcp port 50000'
```

## 7. 独自TCPハンドシェイクを実行

SSHターミナル3で、まずclientカーネルが自動送信するRSTだけを抑制します。このルールはスクリプトが送るSYNは破棄せず、カーネルが自動送信するRSTだけを抑制します。

```sh
ip netns exec client iptables -I OUTPUT 1 -o veth-client -p tcp -s 10.0.0.1 --sport 40000 -d 10.0.0.2 --dport 50000 --tcp-flags RST RST -j DROP
```

独自にSYNを送信し、SYN-ACKを受信しても最終ACKは送らず、サーバーからの再送を待ちます。

```sh
ip netns exec client python3 /root/tcp-lab/raw_tcp_no_ack.py
```

`SYN-ACK retransmission` と表示されれば再送を確認できています。終了後、RST抑制ルールを削除します。

```sh
ip netns exec client iptables -D OUTPUT -o veth-client -p tcp -s 10.0.0.1 --sport 40000 -d 10.0.0.2 --dport 50000 --tcp-flags RST RST -j DROP
```

## 8. pcapを止めて確認

SSHターミナル2で `Ctrl-C` を押してキャプチャを終了します。続けてVM内でパケットを確認します。

```sh
tcpdump -n -r /tmp/raw_tcp_no_ack.pcap
```

## 9. pcapをホストへコピー

ホスト側のターミナルで実行します。

```sh
ssh -i ~/.ssh/tcp-lab -p 2222 root@127.0.0.1 'cat /tmp/raw_tcp_no_ack.pcap' > ./raw_tcp_no_ack.pcap
```

## SSHホスト鍵が変わった場合

ビルドごとにQEMUゲストのSSHホスト鍵を生成し直します。`REMOTE HOST IDENTIFICATION HAS CHANGED` が出たら、まずVMのシリアルコンソールで新しい指紋を確認します。

```sh
ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub
```

指紋がSSH警告に表示された値と一致し、自分が起動したQEMUであることを確認した場合に限り、ホスト側で古い登録を削除します。

```sh
ssh-keygen -f ~/.ssh/known_hosts -R '[127.0.0.1]:2222'
```

その後SSHで再接続し、新しい指紋を確認して受け入れます。

## 10. serverとQEMUを終了

SSHターミナル1でserverを止めます。

```sh
kill "$SERVER_PID"
```

QEMUを終了するにはシリアルコンソールで `Ctrl-a` の後に `x` を押します。
