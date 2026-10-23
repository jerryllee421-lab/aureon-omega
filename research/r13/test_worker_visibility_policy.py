"""Pure policy-model tests; these do not execute PowerShell or MetaTrader 5."""
import unittest


def worker_guard_state(elapsed_seconds, verified_workers, unverified_workers):
    if verified_workers > 1:
        return "EXCESS_AGENTS"
    if verified_workers == 0 and unverified_workers > 0 and elapsed_seconds >= 90:
        return "UNVERIFIED_STOP_QUEUE"
    if verified_workers == 0 and elapsed_seconds >= 90:
        return "NO_VISIBLE_STOP_QUEUE"
    return "WARMUP_OR_OK"


class WorkerVisibilityPolicyTests(unittest.TestCase):
    def test_startup_visibility_gap_is_not_immediately_fatal(self):
        for elapsed in (0, 3, 40, 89):
            with self.subTest(elapsed=elapsed):
                self.assertEqual(worker_guard_state(elapsed, 0, 0), "WARMUP_OR_OK")

    def test_no_visible_worker_after_warmup_blocks_queue(self):
        self.assertEqual(worker_guard_state(90, 0, 0), "NO_VISIBLE_STOP_QUEUE")
        self.assertEqual(worker_guard_state(120, 0, 0), "NO_VISIBLE_STOP_QUEUE")

    def test_unverified_worker_is_not_owned_worker(self):
        self.assertEqual(worker_guard_state(89, 0, 1), "WARMUP_OR_OK")
        self.assertEqual(worker_guard_state(90, 0, 1), "UNVERIFIED_STOP_QUEUE")

    def test_one_verified_worker_remains_accepted(self):
        self.assertEqual(worker_guard_state(5, 1, 0), "WARMUP_OR_OK")
        self.assertEqual(worker_guard_state(100, 1, 0), "WARMUP_OR_OK")

    def test_multiple_verified_workers_fail_closed(self):
        self.assertEqual(worker_guard_state(1, 2, 0), "EXCESS_AGENTS")
        self.assertEqual(worker_guard_state(100, 2, 0), "EXCESS_AGENTS")


if __name__ == "__main__":
    unittest.main()
