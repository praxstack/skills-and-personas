/* AC-2.4: prints its process id, which differs between the two runs. */
#include <stdio.h>
#include <unistd.h>

int main(void) {
    printf("pid %d\n", (int)getpid());
    return 0;
}
