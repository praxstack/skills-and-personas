/* E19 fixture 3: runtime UBSan, signed integer overflow. No compile warning. */
#include <limits.h>
#include <stdio.h>

int main(int argc, char **argv) {
    (void)argv;
    volatile int x = INT_MAX;
    int y = x + argc; /* INT_MAX + 1 */
    printf("%d\n", y);
    return 0;
}
