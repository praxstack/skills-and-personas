#include <stdio.h>

int main(void) {
    int n = 2;
    switch (n) {
    case 1:
        puts("one");
        break;
    case 2:
        puts("two");
        break;
    case 3:
        puts("three");
        break;
    case 4:
        puts("four");
    }
    puts("done");
    return 0;
}
