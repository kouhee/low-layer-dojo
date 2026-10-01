#include <stdio.h>

int main(void)
{
    volatile double x = 53.0;

    volatile int a = x / 100.0 * 100.0;

    volatile double y = x / 100.0 * 100.0;
    volatile int b = y;

    printf("a = %d\n", a);
    printf("b = %d\n", b);

    return 0;
}
