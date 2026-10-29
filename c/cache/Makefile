CC = gcc
CFLAGS ?= -O2 -g
WARNINGS = -std=c11 -Wall -Wextra -Wpedantic

.PHONY: all clean

all: cache-demo

cache-demo: main.c
	$(CC) $(CPPFLAGS) $(CFLAGS) $(WARNINGS) -o $@ $<

clean:
	rm -f cache-demo cachegrind.out.row cachegrind.out.column
