#define _POSIX_C_SOURCE 200809L

#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <valgrind/cachegrind.h>

#define MATRIX_SIDE 1024U
#define MATRIX_ELEMENTS ((size_t)MATRIX_SIDE * MATRIX_SIDE)
#define BENCH_REPETITIONS 8U
#define NANOSECONDS_PER_MILLISECOND 1000000.0

static void initialize_matrix(uint32_t *matrix)
{
    for (size_t i = 0; i < MATRIX_ELEMENTS; ++i) {
        matrix[i] = (uint32_t)i * UINT32_C(2654435761) + UINT32_C(17);
    }
}

static uint64_t sum_row_major(const volatile uint32_t *matrix)
{
    uint64_t sum = 0;

    for (size_t row = 0; row < MATRIX_SIDE; ++row) {
        for (size_t column = 0; column < MATRIX_SIDE; ++column) {
            sum += matrix[row * MATRIX_SIDE + column];
        }
    }
    return sum;
}

static uint64_t sum_column_major(const volatile uint32_t *matrix)
{
    uint64_t sum = 0;

    for (size_t column = 0; column < MATRIX_SIDE; ++column) {
        for (size_t row = 0; row < MATRIX_SIDE; ++row) {
            sum += matrix[row * MATRIX_SIDE + column];
        }
    }
    return sum;
}

static uint64_t scan(const volatile uint32_t *matrix, int column_major)
{
    return column_major ? sum_column_major(matrix) : sum_row_major(matrix);
}

static uint64_t monotonic_time_ns(void)
{
    struct timespec now;
    if (clock_gettime(CLOCK_MONOTONIC, &now) != 0) {
        perror("clock_gettime");
        exit(EXIT_FAILURE);
    }

    return (uint64_t)now.tv_sec * UINT64_C(1000000000) + (uint64_t)now.tv_nsec;
}

static void run_native_benchmark(const volatile uint32_t *matrix)
{
    uint64_t elapsed_ns[2] = {0, 0};
    uint64_t checksum[2] = {0, 0};

    for (unsigned int repetition = 0; repetition < BENCH_REPETITIONS; ++repetition) {
        int first_mode = (int)(repetition % 2);
        for (int offset = 0; offset < 2; ++offset) {
            int mode = (first_mode + offset) % 2;
            uint64_t start = monotonic_time_ns();
            checksum[mode] += scan(matrix, mode);
            elapsed_ns[mode] += monotonic_time_ns() - start;
        }
    }

    if (checksum[0] != checksum[1]) {
        fprintf(stderr, "Row and column scans produced different sums.\n");
        exit(EXIT_FAILURE);
    }

    double row_ms = (double)elapsed_ns[0] / BENCH_REPETITIONS
        / NANOSECONDS_PER_MILLISECOND;
    double column_ms = (double)elapsed_ns[1] / BENCH_REPETITIONS
        / NANOSECONDS_PER_MILLISECOND;
    double difference_ms = column_ms - row_ms;

    printf("Native processing time (average over %u alternating row/column rounds):\n",
           BENCH_REPETITIONS);
    printf("  row-major:    %.3f ms\n", row_ms);
    printf("  column-major: %.3f ms\n", column_ms);
    printf("  difference (column - row): %+.3f ms", difference_ms);
    if (row_ms > 0.0) {
        printf(" (column/row: %.2fx)\n", column_ms / row_ms);
    } else {
        putchar('\n');
    }
    printf("  checksum per scan: %" PRIu64 "\n", checksum[0] / BENCH_REPETITIONS);
}

int main(int argc, char **argv)
{
    if (argc != 2 || (strcmp(argv[1], "row") != 0
                      && strcmp(argv[1], "column") != 0
                      && strcmp(argv[1], "benchmark") != 0)) {
        fprintf(stderr, "Usage: %s row|column|benchmark\n", argv[0]);
        return EXIT_FAILURE;
    }

    uint32_t *matrix = malloc(MATRIX_ELEMENTS * sizeof(*matrix));
    if (matrix == NULL) {
        perror("malloc");
        return EXIT_FAILURE;
    }
    initialize_matrix(matrix);

    volatile uint32_t *measured_matrix = matrix;
    if (strcmp(argv[1], "benchmark") == 0) {
        run_native_benchmark(measured_matrix);
    } else {
        int column_major = strcmp(argv[1], "column") == 0;
        CACHEGRIND_START_INSTRUMENTATION;
        uint64_t sum = scan(measured_matrix, column_major);
        CACHEGRIND_STOP_INSTRUMENTATION;
        printf("mode=%s elements=%zu sum=%" PRIu64 "\n",
               argv[1], MATRIX_ELEMENTS, sum);
    }

    free(matrix);
    return EXIT_SUCCESS;
}
