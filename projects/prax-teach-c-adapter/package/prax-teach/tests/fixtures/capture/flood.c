/* AC-2.5 output cap: writes 2 MB to stdout ("out") or stderr ("err"). */
#include <stdio.h>
#include <string.h>

int main(int argc, char **argv) {
    FILE *f = (argc > 1 && strcmp(argv[1], "err") == 0) ? stderr : stdout;
    char line[1024];
    memset(line, 'x', sizeof line - 1);
    line[sizeof line - 1] = '\n';
    for (int i = 0; i < 2048; i++) fwrite(line, 1, sizeof line, f);
    return 0;
}
