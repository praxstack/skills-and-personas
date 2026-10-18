/* Review WP2 P2-1 fixture: ~32 MB of string literal from macro repetition; clang needs gigabytes. */
#define R1(x) x x x x x x x x x x
#define R2(x) R1(R1(x))
#define R3(x) R1(R2(x))
#define R6(x) R3(R3(x))
static const char s[] = R6("0123456789abcdef0123456789abcdef");
int main(void) { return s[1] - '1'; }
