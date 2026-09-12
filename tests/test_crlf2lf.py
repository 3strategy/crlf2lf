from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).parents[1] / "scripts" / "crlf2lf.py"


class GitFilesTests(unittest.TestCase):
    def test_default_converts_untracked_nonignored_git_files(self) -> None:
        with tempfile.TemporaryDirectory(prefix="crlf2lf-test-") as directory:
            root = Path(directory)
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            (root / ".gitignore").write_text("ignored.txt\n", encoding="utf-8")
            candidate = root / "new-untracked.txt"
            ignored = root / "ignored.txt"
            candidate.write_bytes(b"alpha\r\nbeta\r\n")
            ignored.write_bytes(b"leave\r\nignored\r\n")

            previewed = subprocess.run(
                [sys.executable, str(SCRIPT), str(root), "--preview"],
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(previewed.returncode, 0)
            self.assertIn("new-untracked.txt", previewed.stdout)
            self.assertNotIn("ignored.txt", previewed.stdout)
            self.assertIn(b"\r", candidate.read_bytes())

            written = subprocess.run(
                [sys.executable, str(SCRIPT), str(root)],
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(written.returncode, 0)
            self.assertNotIn(b"\r", candidate.read_bytes())
            self.assertIn(b"\r", ignored.read_bytes())

    def test_default_converts_files_outside_git(self) -> None:
        with tempfile.TemporaryDirectory(prefix="crlf2lf-test-") as directory:
            candidate = Path(directory) / "plain.txt"
            candidate.write_bytes(b"alpha\r\nbeta\r\n")

            written = subprocess.run(
                [sys.executable, str(SCRIPT), directory],
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(written.returncode, 0)
            self.assertNotIn(b"\r", candidate.read_bytes())

    def test_legacy_git_flag_still_checks_without_writing(self) -> None:
        with tempfile.TemporaryDirectory(prefix="crlf2lf-test-") as directory:
            root = Path(directory)
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            candidate = root / "new-untracked.txt"
            candidate.write_bytes(b"alpha\r\nbeta\r\n")

            checked = subprocess.run(
                [sys.executable, str(SCRIPT), str(root), "--git-tracked", "--check"],
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(checked.returncode, 1)
            self.assertIn("new-untracked.txt", checked.stdout)
            self.assertIn(b"\r", candidate.read_bytes())


if __name__ == "__main__":
    unittest.main()
