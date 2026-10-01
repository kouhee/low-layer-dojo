CC_X86  := gcc
CC_ARM  := aarch64-linux-gnu-gcc
QEMU    := qemu-aarch64

SRC := percent.c

CFLAGS := -Wall -Wextra -g
FPMATH_387 := -mfpmath=387

.PHONY: all clean test \
        x86_64-O0 x86_64-O2 x86_64-O3 \
        x86-O0 x86-O2 x86-O3 \
        x87-O0 x87-O2 x87-O3 \
        arm-O0 arm-O2 arm-O3

all: test

# ============================================================
# x86_64 (64-bit)
# ============================================================

x86_64-O0:
	$(CC_X86) -m64 -O0 $(CFLAGS) $(SRC) -o percent_x86_64_O0
	./percent_x86_64_O0

x86_64-O2:
	$(CC_X86) -m64 -O2 $(CFLAGS) $(SRC) -o percent_x86_64_O2
	./percent_x86_64_O2

x86_64-O3:
	$(CC_X86) -m64 -O3 $(CFLAGS) $(SRC) -o percent_x86_64_O3
	./percent_x86_64_O3

# ============================================================
# x86 32bit (no explicit mfpmath)
# ============================================================

x86-O0:
	$(CC_X86) -m32 -O0 $(CFLAGS) $(SRC) -o percent_x86_O0
	./percent_x86_O0

x86-O2:
	$(CC_X86) -m32 -O2 $(CFLAGS) $(SRC) -o percent_x86_O2
	./percent_x86_O2

x86-O3:
	$(CC_X86) -m32 -O3 $(CFLAGS) $(SRC) -o percent_x86_O3
	./percent_x86_O3

# ============================================================
# x86 32bit + x87 (explicit -mfpmath=387)
# ============================================================

x87-O0:
	$(CC_X86) -m32 $(FPMATH_387) -O0 $(CFLAGS) $(SRC) -o percent_x87_O0
	./percent_x87_O0

x87-O2:
	$(CC_X86) -m32 $(FPMATH_387) -O2 $(CFLAGS) $(SRC) -o percent_x87_O2
	./percent_x87_O2

x87-O3:
	$(CC_X86) -m32 $(FPMATH_387) -O3 $(CFLAGS) $(SRC) -o percent_x87_O3
	./percent_x87_O3


# ============================================================
# ARM64
# ============================================================

arm-O0:
	$(CC_ARM) -static -O0 $(CFLAGS) $(SRC) -o percent_arm_O0
	$(QEMU) ./percent_arm_O0

arm-O2:
	$(CC_ARM) -static -O2 $(CFLAGS) $(SRC) -o percent_arm_O2
	$(QEMU) ./percent_arm_O2

arm-O3:
	$(CC_ARM) -static -O3 $(CFLAGS) $(SRC) -o percent_arm_O3
	$(QEMU) ./percent_arm_O3


# ============================================================
# 全部実行
# ============================================================

test:
	@echo
	@echo "========================================"
	@echo " x86_64 (64-bit)"
	@echo "========================================"

	@echo
	@echo "--- -O0 ---"
	$(CC_X86) -m64 -O0 $(CFLAGS) $(SRC) -o percent_x86_64_O0
	./percent_x86_64_O0

	@echo
	@echo "--- -O2 ---"
	$(CC_X86) -m64 -O2 $(CFLAGS) $(SRC) -o percent_x86_64_O2
	./percent_x86_64_O2

	@echo
	@echo "--- -O3 ---"
	$(CC_X86) -m64 -O3 $(CFLAGS) $(SRC) -o percent_x86_64_O3
	./percent_x86_64_O3

	@echo
	@echo "========================================"
	@echo " x86 32bit (no explicit mfpmath)"
	@echo "========================================"

	@echo
	@echo "--- -O0 ---"
	$(CC_X86) -m32 -O0 $(CFLAGS) $(SRC) -o percent_x86_O0
	./percent_x86_O0

	@echo
	@echo "--- -O2 ---"
	$(CC_X86) -m32 -O2 $(CFLAGS) $(SRC) -o percent_x86_O2
	./percent_x86_O2

	@echo
	@echo "--- -O3 ---"
	$(CC_X86) -m32 -O3 $(CFLAGS) $(SRC) -o percent_x86_O3
	./percent_x86_O3

	@echo
	@echo "========================================"
	@echo " x86 32bit + x87 (-mfpmath=387)"
	@echo "========================================"

	@echo
	@echo "--- -O0 ---"
	$(CC_X86) -m32 $(FPMATH_387) -O0 $(CFLAGS) $(SRC) -o percent_x87_O0
	./percent_x87_O0

	@echo
	@echo "--- -O2 ---"
	$(CC_X86) -m32 $(FPMATH_387) -O2 $(CFLAGS) $(SRC) -o percent_x87_O2
	./percent_x87_O2

	@echo
	@echo "--- -O3 ---"
	$(CC_X86) -m32 $(FPMATH_387) -O3 $(CFLAGS) $(SRC) -o percent_x87_O3
	./percent_x87_O3

	@echo
	@echo "========================================"
	@echo " ARM64"
	@echo "========================================"

	@echo
	@echo "--- -O0 ---"
	$(CC_ARM) -static -O0 $(CFLAGS) $(SRC) -o percent_arm_O0
	$(QEMU) ./percent_arm_O0

	@echo
	@echo "--- -O2 ---"
	$(CC_ARM) -static -O2 $(CFLAGS) $(SRC) -o percent_arm_O2
	$(QEMU) ./percent_arm_O2

	@echo
	@echo "--- -O3 ---"
	$(CC_ARM) -static -O3 $(CFLAGS) $(SRC) -o percent_arm_O3
	$(QEMU) ./percent_arm_O3

	@echo
	@echo "Done."
	@echo


clean:
	rm -f percent_x86_64_O0 percent_x86_64_O2 percent_x86_64_O3
	rm -f percent_x86_O0 percent_x86_O2 percent_x86_O3
	rm -f percent_x87_O0 percent_x87_O2 percent_x87_O3
	rm -f percent_arm_O0 percent_arm_O2 percent_arm_O3
	rm -f percent_x87_O*.s percent_arm_O*.s
