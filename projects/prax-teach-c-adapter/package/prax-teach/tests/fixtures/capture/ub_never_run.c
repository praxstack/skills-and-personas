/* A program marked ub:true. It has a -Wformat warning (undefined behaviour) and it never
 * terminates, so if capture ever ran it, capture would fail with RunTimeout. */
#include <stdio.h>

int main(void) {
    int a = 66;
    printf("%f\n", a);
    volatile int spin = 1;
    while (spin) {
    }
    return 0;
}
