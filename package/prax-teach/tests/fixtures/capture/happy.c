/* Happy-path capture fixture (AC-2.2). One byte, printed four ways, plus a sum.
 * The switch falls through on purpose: gcc-16 -Wextra warns about it (-Wimplicit-fallthrough),
 * clang -Wextra does not, so the gcc diagnostic must be recorded and must not block. */
#include <stdio.h>

int main(void) {
    unsigned char b = 66;
    printf("%d\n", b);
    printf("%c\n", b);
    printf("%u\n", (unsigned)b);
    printf("%f\n", (double)b);
    int a[] = {1, 2, 3, 4};
    int s = 0;
    for (int i = 0; i < 4; i++) s += a[i];
    printf("%d\n", s);
    int n = 1;
    switch (n) {
    case 1:
        s++;
    case 2:
        s++;
        break;
    }
    return s == 12 ? 0 : 1;
}
