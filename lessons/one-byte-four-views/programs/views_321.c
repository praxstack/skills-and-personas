#include <stdio.h>

int main(void) {
    int a = 321;
    char b[9] = {0};
    for (int i = 0; i < 8; i++)
        b[i] = '0' + (((unsigned)a >> (7 - i)) & 1u);
    printf("%s\n", b);
    printf("0x%02X\n", (unsigned)a & 0xFFu);
    printf("%d\n", a);
    printf("%u\n", (unsigned)a);
    printf("%f\n", (double)a);
    char c[2];
    snprintf(c, sizeof c, "%c", a);
    printf("%d\n", (unsigned char)c[0]);
    return 0;
}
