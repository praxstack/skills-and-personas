#include <stdio.h>

int main(void) {
    int n = 2;
    switch (n) {
    case 1:
        puts("one");
    case 2:
        puts("two");
    case 3:
        break;
    case 4:
        puts("four");
    }
    puts("done");
    return 0;
}
