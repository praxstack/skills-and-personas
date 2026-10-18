/* Sandbox probe for tests/test_security.py. One action per run, picked by argv[1].
 * Prints "ALLOWED <action>" when the action worked and "DENIED <action> <reason>" when it did not.
 * Mach probes only look a service up; they never send it a message, so no app is launched. */
#include <arpa/inet.h>
#include <errno.h>
#include <fcntl.h>
#include <mach/mach.h>
#include <netinet/in.h>
#include <servers/bootstrap.h>
#include <spawn.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/wait.h>
#include <unistd.h>

extern char **environ;

static int report(const char *action, int ok, const char *why) {
    if (ok) printf("ALLOWED %s\n", action);
    else printf("DENIED %s %s\n", action, why);
    return 0;
}

static int lookup(const char *action, const char *service) {
    mach_port_t port = MACH_PORT_NULL;
    kern_return_t kr = bootstrap_look_up(bootstrap_port, service, &port);
    return report(action, kr == KERN_SUCCESS && port != MACH_PORT_NULL, bootstrap_strerror(kr));
}

int main(int argc, char **argv) {
    if (argc < 2) return 2;
    const char *a = argv[1];
    if (!strcmp(a, "read-home")) {
        const char *home = getenv("PROBE_HOME_FILE");
        int fd = home ? open(home, O_RDONLY) : -1;
        return report(a, fd >= 0, strerror(errno));
    }
    if (!strcmp(a, "write-outside")) {
        int fd = open(argv[2], O_WRONLY | O_CREAT | O_TRUNC, 0600);
        return report(a, fd >= 0, strerror(errno));
    }
    if (!strcmp(a, "write-tmp")) {
        int fd = open(argv[2], O_WRONLY | O_CREAT | O_TRUNC, 0600);
        return report(a, fd >= 0 && write(fd, "x", 1) == 1, strerror(errno));
    }
    if (!strcmp(a, "connect")) {
        int s = socket(AF_INET, SOCK_STREAM, 0);
        struct sockaddr_in sa = {0};
        sa.sin_family = AF_INET;
        sa.sin_port = htons(443);
        inet_pton(AF_INET, "1.1.1.1", &sa.sin_addr);
        int ok = s >= 0 && connect(s, (struct sockaddr *)&sa, sizeof sa) == 0;
        return report(a, ok, strerror(errno));
    }
    if (!strcmp(a, "fork")) {
        pid_t p = fork();
        if (p == 0) _exit(0);
        if (p > 0) waitpid(p, NULL, 0);
        return report(a, p > 0, strerror(errno));
    }
    if (!strcmp(a, "posix-spawn")) {
        pid_t p;
        char *args[] = {"/usr/bin/true", NULL};
        int rc = posix_spawn(&p, "/usr/bin/true", NULL, NULL, args, environ);
        if (rc == 0) waitpid(p, NULL, 0);
        return report(a, rc == 0, strerror(rc));
    }
    if (!strcmp(a, "mach-nsurlsessiond")) return lookup(a, "com.apple.nsurlsessiond");
    if (!strcmp(a, "mach-lsd-open")) return lookup(a, "com.apple.lsd.open");
    if (!strcmp(a, "mach-launchservicesd")) return lookup(a, "com.apple.coreservices.launchservicesd");
    if (!strcmp(a, "mach-appleevents")) return lookup(a, "com.apple.coreservices.appleevents");
    if (!strcmp(a, "mach-pasteboard")) return lookup(a, "com.apple.pasteboard.1");
    if (!strcmp(a, "hello")) return report(a, 1, "");
    if (!strcmp(a, "heap-overflow")) {
        volatile char *buf = malloc(4);
        buf[argc + 2] = 1; /* argc is 2: writes buf[4], one past the end */
        free((void *)buf);
        return report(a, 1, "");
    }
    if (!strcmp(a, "ub-shift")) {
        volatile int n = 31 + argc; /* 33: shift past the width of int */
        return report(a, (1 << n) != 0, "");
    }
    return 2;
}
