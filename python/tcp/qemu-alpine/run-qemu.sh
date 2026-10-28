#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
WORK_DIR="$SCRIPT_DIR/.build"
KERNEL="$WORK_DIR/vmlinuz-virt"
INITRAMFS="$WORK_DIR/initramfs.cpio.gz"
QEMU=${QEMU:-qemu-system-x86_64}

if ! command -v "$QEMU" >/dev/null 2>&1; then
    echo "Cannot find $QEMU. Install qemu-system-x86 or set QEMU to its path." >&2
    exit 1
fi
if [ ! -f "$KERNEL" ] || [ ! -f "$INITRAMFS" ]; then
    echo "Build artifacts are missing. Run ./build.sh first." >&2
    exit 1
fi

exec "$QEMU" \
    -machine accel=tcg \
    -cpu max \
    -m 512M \
    -kernel "$KERNEL" \
    -initrd "$INITRAMFS" \
    -append "console=ttyS0 rdinit=/init tsc=unstable" \
    -nographic \
    -no-reboot \
    -serial mon:stdio \
    -netdev user,id=mgmt,restrict=on,hostfwd=tcp:127.0.0.1:2222-:22 \
    -device virtio-net-pci,netdev=mgmt
