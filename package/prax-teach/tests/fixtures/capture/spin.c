/* AC-2.5 cleanup after a timeout: never terminates. */
int main(void) {
    volatile int spin = 1;
    while (spin) {
    }
    return 0;
}
