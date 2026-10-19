/* E19 fixture 1: -Wformat catches printf("%f", int). Undefined behaviour (C17 7.21.6.1p9). */
#include <stdio.h>

int main(void) {
    int a = 66;
    printf("%f\n", a);
    return 0;
}
