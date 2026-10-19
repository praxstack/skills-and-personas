#include <math.h>
#include <stdio.h>

int main(void) {
    double x1 = 0.8, w1 = 1.5;
    double x2 = 0.4, w2 = -1.0;
    double b = -0.2;
    double t1 = x1 * w1;
    printf("%g * %g = %+g\n", x1, w1, t1);
    double t2 = x2 * w2;
    printf("%g * %g = %+g\n", x2, w2, t2);
    double z = t1 + t2 + b;
    printf("b = %+g  z = %g\n", b, z);
    double a = fmax(0.0, z);
    printf("a = %g\n", a);
    return 0;
}
