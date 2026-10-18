/* AC-2.5 cleanup after a watchdog kill: keeps touching new memory, then sleeps. */
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

int main(void) {
    for (int i = 0; i < 64; i++) {
        char *p = malloc(16 << 20);
        if (!p) break;
        memset(p, i + 1, 16 << 20);
    }
    sleep(30);
    return 0;
}
