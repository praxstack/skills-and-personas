"""PID 1 wait policy: reap adopted exits while retaining the owned child's status.

Only the supervisor owns waitpid for these Popen objects. Do not combine this
function with a SIGCHLD handler, Popen.wait(), or a competing waiter.
"""
import os


def wait_reaping(child):
    """Wait for child; consume orphan zombies without waiting for live orphans."""
    while child.returncode is None:
        pid, status = os.waitpid(-1, 0)
        if pid == child.pid:
            child.returncode = os.waitstatus_to_exitcode(status)
    # The owned child can exit alongside adopted descendants. Drain exited ones
    # only; live descendants remain subject to PID 1's existing kill/deadline.
    while True:
        try:
            pid, _ = os.waitpid(-1, os.WNOHANG)
        except ChildProcessError:
            break
        if pid == 0:
            break
    return child.returncode
