/* E19 fixture 2: runtime ASan, a heap buffer overflow one past the end. No compile warning. */
#include <stdio.h>
#include <stdlib.h>

int main(int argc, char **argv) {
    (void)argv;
    volatile char *buf = malloc(4);
    buf[argc + 3] = 1; /* argc is 1: writes buf[4] */
    printf("%d\n", buf[0]);
    free((void *)buf);
    return 0;
}
