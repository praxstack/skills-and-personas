#include <stdio.h>
#include <string.h>

int main(void) {
    int a = 66;
    double d = (double)a;
    unsigned char ab[sizeof a];
    unsigned char db[sizeof d];
    memcpy(ab, &a, sizeof a);
    memcpy(db, &d, sizeof d);
    for (size_t i = 0; i < sizeof a; i++)
        printf("a[%zu] %02x\n", i, ab[i]);
    for (size_t i = 0; i < sizeof d; i++)
        printf("d[%zu] %02x\n", i, db[i]);
    return 0;
}
