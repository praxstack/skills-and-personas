#include <stdio.h>
#include <string.h>

int main(void) {
    char a = 'B';
    double d = (double)a;
    unsigned long long bits;
    memcpy(&bits, &d, sizeof bits);
    printf("%d\n", a);
    printf("%f\n", (double)a);
    printf("%02x\n", (unsigned char)a);
    printf("%016llx\n", bits);
    return 0;
}
