#include <stdio.h>

int factorial(int n) {
    printf("enter factorial(%d)\n", n);
    int r = 1;
    if (n > 1)
        r = n * factorial(n - 1);
    printf("factorial(%d) = %d\n", n, r);
    return r;
}

int main(void) {
    int r = factorial(2);
    printf("main got %d\n", r);
    return 0;
}
