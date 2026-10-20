"""Owned return status and nonblocking orphan-drain regression controls."""
import os
import signal
from types import SimpleNamespace
import unittest
from unittest.mock import call, patch

from supervisor_reaping import wait_reaping


class SupervisorReapingTests(unittest.TestCase):
    def test_adopted_exits_do_not_replace_owned_failure(self):
        child=SimpleNamespace(pid=42,returncode=None)
        with patch('supervisor_reaping.os.waitpid',side_effect=[(17,0),(42,7<<8),(18,9<<8),(0,0)]) as wait:
            self.assertEqual(wait_reaping(child),7)
        self.assertEqual(child.returncode,7)
        self.assertEqual(wait.call_args_list,[call(-1,0),call(-1,0),call(-1,os.WNOHANG),call(-1,os.WNOHANG)])

    def test_owned_signal_status_survives_reaping(self):
        child=SimpleNamespace(pid=42,returncode=None)
        with patch('supervisor_reaping.os.waitpid',side_effect=[(17,0),(42,signal.SIGTERM),ChildProcessError()]):
            self.assertEqual(wait_reaping(child),-signal.SIGTERM)

    def test_drain_does_not_wait_for_live_descendants(self):
        child=SimpleNamespace(pid=42,returncode=None)
        with patch('supervisor_reaping.os.waitpid',side_effect=[(42,0),(0,0)]) as wait:
            self.assertEqual(wait_reaping(child),0)
        self.assertEqual(wait.call_args_list,[call(-1,0),call(-1,os.WNOHANG)])

    def test_lost_owned_status_is_not_assumed_success(self):
        child=SimpleNamespace(pid=42,returncode=None)
        with patch('supervisor_reaping.os.waitpid',side_effect=ChildProcessError()),self.assertRaises(ChildProcessError):
            wait_reaping(child)
        self.assertIsNone(child.returncode)

if __name__=='__main__':unittest.main()
