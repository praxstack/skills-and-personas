#include <stdio.h>
#include <string.h>

int main(void) {
    int a = 66;
    char b[9] = {0};
    for (int i = 0; i < 8; i++)
        b[i] = '0' + ((a >> (7 - i)) & 1);
    printf("%s\n", b);
    printf("%#x\n", (unsigned)a);
    printf("%d\n", a);
    printf("%u\n", (unsigned)a);
    printf("%f\n", (double)a);
    printf("%c\n", a);
    double d = (double)a;
    unsigned long long u;
    memcpy(&u, &d, sizeof u);
    printf("%#llx\n", u);
    return 0;
}
