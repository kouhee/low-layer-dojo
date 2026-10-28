#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
WORK_DIR="$SCRIPT_DIR/.build"
ROOTFS="$WORK_DIR/rootfs"
APK_CACHE="$WORK_DIR/apk-cache"
ALPINE_VERSION="3.24.3"
ARCH="x86_64"
MINIROOTFS="alpine-minirootfs-$ALPINE_VERSION-$ARCH.tar.gz"
MINIROOTFS_URL="https://dl-cdn.alpinelinux.org/alpine/v3.24/releases/$ARCH/$MINIROOTFS"
MINIROOTFS_SHA256="f8e1cafba9b1b283b5d30d06f9885c8d2bc161ffe9083ade8e2e157813a53407"
SSH_PUBKEY_FILE=${SSH_PUBKEY_FILE:-"$HOME/.ssh/tcp-lab.pub"}

if [ "$(id -u)" -ne 0 ]; then
    if ! command -v sudo >/dev/null 2>&1; then
        echo "Run this script as root or install sudo." >&2
        exit 1
    fi
    exec sudo env "SSH_PUBKEY_FILE=$SSH_PUBKEY_FILE" "$0" "$@"
fi

if [ ! -s "$SSH_PUBKEY_FILE" ]; then
    echo "SSH public key not found: $SSH_PUBKEY_FILE" >&2
    echo "Generate one with: ssh-keygen -t ed25519 -f ~/.ssh/tcp-lab" >&2
    echo "Then run: SSH_PUBKEY_FILE=~/.ssh/tcp-lab.pub ./build.sh" >&2
    exit 1
fi

for tool in curl tar cpio gzip find grep chroot mount umount sha256sum sort cp mkdir rm chmod chown od tr; do
    if ! command -v "$tool" >/dev/null 2>&1; then
        echo "Missing host tool: $tool. See README.md for the apt install command." >&2
        exit 1
    fi
done

if [ "$(uname -m)" != "$ARCH" ]; then
    echo "This build script requires an $ARCH Linux host." >&2
    exit 1
fi

mkdir -p "$WORK_DIR" "$APK_CACHE"
ARCHIVE="$WORK_DIR/$MINIROOTFS"
if [ ! -f "$ARCHIVE" ]; then
    curl -fL --retry 3 "$MINIROOTFS_URL" -o "$ARCHIVE"
fi
printf '%s  %s\n' "$MINIROOTFS_SHA256" "$ARCHIVE" | sha256sum -c -

rm -rf "$ROOTFS"
mkdir -p "$ROOTFS"
tar -xzf "$ARCHIVE" -C "$ROOTFS"
mkdir -p "$ROOTFS/var/cache/apk" "$ROOTFS/root/tcp-lab"
rm -f "$ROOTFS/etc/resolv.conf"
cp -L /etc/resolv.conf "$ROOTFS/etc/resolv.conf"
printf '%s\n' \
    'https://dl-cdn.alpinelinux.org/alpine/v3.24/main' \
    'https://dl-cdn.alpinelinux.org/alpine/v3.24/community' \
    > "$ROOTFS/etc/apk/repositories"

cp "$SCRIPT_DIR/../raw_tcp_no_ack.py" \
    "$SCRIPT_DIR/../tcp_server.py" \
    "$ROOTFS/root/tcp-lab/"

mount --bind /dev "$ROOTFS/dev"
mount --bind /proc "$ROOTFS/proc"
mount --bind /sys "$ROOTFS/sys"
cleanup_mounts() {
    umount "$ROOTFS/sys" 2>/dev/null || true
    umount "$ROOTFS/proc" 2>/dev/null || true
    umount "$ROOTFS/dev" 2>/dev/null || true
}
trap cleanup_mounts EXIT HUP INT TERM

if find "$APK_CACHE" -type f -name 'APKINDEX*.tar.gz' -print -quit | grep -q .; then
    cp -a "$APK_CACHE/." "$ROOTFS/var/cache/apk/"
    if ! chroot "$ROOTFS" /sbin/apk --no-progress --no-network \
        --cache-dir /var/cache/apk add python3 iproute2 iptables kmod linux-virt tcpdump openssh-server shadow; then
        echo "Some APKs are not cached; retrying with network access."
        chroot "$ROOTFS" /sbin/apk --no-progress --cache-dir /var/cache/apk \
            add python3 iproute2 iptables kmod linux-virt tcpdump openssh-server shadow
    fi
else
    chroot "$ROOTFS" /sbin/apk --no-progress --cache-dir /var/cache/apk update
    chroot "$ROOTFS" /sbin/apk --no-progress --cache-dir /var/cache/apk \
        add python3 iproute2 iptables kmod linux-virt tcpdump openssh-server shadow
fi

mkdir -p "$ROOTFS/root/.ssh"
cp "$SSH_PUBKEY_FILE" "$ROOTFS/root/.ssh/authorized_keys"
chmod 0700 "$ROOTFS/root/.ssh"
chmod 0600 "$ROOTFS/root/.ssh/authorized_keys"
chroot "$ROOTFS" /usr/bin/ssh-keygen -l -f /root/.ssh/authorized_keys >/dev/null

# Unlock root for public-key authentication without retaining a usable password.
ROOT_PASSWORD=$(od -An -N32 -tx1 /dev/urandom | tr -d ' \n')
printf 'root:%s\n' "$ROOT_PASSWORD" | chroot "$ROOTFS" /usr/sbin/chpasswd
unset ROOT_PASSWORD

chroot "$ROOTFS" /usr/bin/python3 --version
chroot "$ROOTFS" /usr/bin/ssh-keygen -A
chroot "$ROOTFS" /usr/sbin/sshd -t

chroot "$ROOTFS" /sbin/apk info -v | LC_ALL=C sort \
    > "$WORK_DIR/alpine-packages.lock"
cp -a "$ROOTFS/var/cache/apk/." "$APK_CACHE/"
rm -rf "$ROOTFS/var/cache/apk"
mkdir -p "$ROOTFS/var/cache/apk"

cat > "$ROOTFS/init" <<'INIT'
#!/bin/busybox sh

export PATH=/usr/sbin:/usr/bin:/sbin:/bin
mkdir -p /proc /sys /dev /run /tmp
mount -t proc proc /proc
mount -t sysfs sysfs /sys
mount -t devtmpfs devtmpfs /dev
mkdir -p /dev/pts
mount -t devpts devpts /dev/pts
mount -t tmpfs -o mode=0755,nosuid,nodev tmpfs /run
hostname tcp-lab

for module in virtio_pci virtio_net veth af_packet xt_tcpudp ip_tables iptable_filter; do
    /sbin/modprobe "$module" 2>/dev/null || true
done

ip link set lo up 2>/dev/null || true

setup_lab_network() {
    mkdir -p /run/netns
    ip netns add client || return 1
    ip netns add server || return 1
    ip link add veth-client type veth peer name veth-server || return 1
    ip link set veth-client netns client || return 1
    ip link set veth-server netns server || return 1
    ip -n client addr add 10.0.0.1/24 dev veth-client || return 1
    ip -n server addr add 10.0.0.2/24 dev veth-server || return 1
    ip -n client link set lo up || return 1
    ip -n server link set lo up || return 1
    ip -n client link set veth-client up || return 1
    ip -n server link set veth-server up || return 1
}

printf '\nAlpine TCP lab (restricted SSH management NIC)\n'
if ip link set eth0 up && ip addr add 10.0.2.15/24 dev eth0; then
    mkdir -p /run/sshd
    if /usr/sbin/sshd -E /tmp/sshd.log \
        -o ListenAddress=10.0.2.15 \
        -o PermitRootLogin=prohibit-password \
        -o PubkeyAuthentication=yes \
        -o PasswordAuthentication=no \
        -o KbdInteractiveAuthentication=no \
        -o AuthorizedKeysFile=/root/.ssh/authorized_keys; then
        printf 'SSH available via host-forwarded port 127.0.0.1:2222\n'
    else
        printf 'WARNING: sshd failed to start:\n' >&2
        cat /tmp/sshd.log >&2 2>/dev/null || true
    fi
else
    printf 'WARNING: SSH management interface setup failed.\n' >&2
fi
if setup_lab_network; then
    printf 'Network namespaces ready: client (10.0.0.1) <-> server (10.0.0.2)\n'
else
    ip netns del client 2>/dev/null || true
    ip netns del server 2>/dev/null || true
    ip link del veth-client 2>/dev/null || true
    printf 'WARNING: automatic namespace setup failed; see kernel/module support.\n' >&2
fi
printf 'Scripts: /root/tcp-lab/\n\n'
exec /bin/busybox setsid /bin/sh -c \
    'exec /bin/sh -l </dev/ttyS0 >/dev/ttyS0 2>&1'
INIT
chmod 0755 "$ROOTFS/init"

KERNEL="$ROOTFS/boot/vmlinuz-virt"
if [ ! -f "$KERNEL" ]; then
    echo "Alpine linux-virt did not install $KERNEL" >&2
    exit 1
fi
cp "$KERNEL" "$WORK_DIR/vmlinuz-virt"

cleanup_mounts
trap - EXIT HUP INT TERM
(
    cd "$ROOTFS"
    find . -print0 | cpio --null --create --format=newc | gzip -9 \
        > "$WORK_DIR/initramfs.cpio.gz"
)
gzip -t "$WORK_DIR/initramfs.cpio.gz"
if ! gzip -dc "$WORK_DIR/initramfs.cpio.gz" | cpio -it | grep -Eq '^(.*/)?init$'; then
    echo "The initramfs archive does not contain /init." >&2
    exit 1
fi

if [ -n "${SUDO_UID:-}" ] && [ -n "${SUDO_GID:-}" ]; then
    chown -R "$SUDO_UID:$SUDO_GID" "$WORK_DIR"
fi

echo "Build complete:"
echo "  Kernel:    $WORK_DIR/vmlinuz-virt"
echo "  Initramfs: $WORK_DIR/initramfs.cpio.gz"
echo "  APK cache: $APK_CACHE"
echo "Run ./run-qemu.sh to boot the VM."
