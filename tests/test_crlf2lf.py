from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).parents[1] / "scripts" / "crlf2lf.py"


class BinarySafetyTests(unittest.TestCase):
    def run_helper(self, path: Path, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), str(path), *args],
            capture_output=True, text=True, check=False,
        )

    def test_binary_files_are_unchanged_in_every_mode_and_scope(self) -> None:
        fixtures = {
            # These printable formats defeated the old null/control heuristic.
            "exam.PDF": b"%PDF-1.4\r\n1 0 obj\r\n<< /Type /Catalog >>\r\nendobj\r\n%%EOF\r\n",
            "GB-H.bcmap": b"printable compressed mapping\r\n",
            "asset.bin": b"printable bytes\r\n",
            # Renamed files still need protection based on content.
            "download": b"%PDF-1.4\r\nprintable objects\r\n%%EOF\r\n",
            "image.txt": b"GIF89a" + b"printable bytes\r\n",
            "archive.txt": b"PK\x03\x04" + b"printable bytes\r\n",
            "late-control.txt": b"header\r\n" + b"a" * 9000 + b"\x01\r\n",
            "late-payload.txt": b"header\r\n" + b"a" * 9000 + b"\xff\r\n",
            "utf16.txt": "hello\r\n".encode("utf-16"),
        }
        for scope in ("--all-files", "--git-files"):
            with self.subTest(scope=scope), tempfile.TemporaryDirectory(prefix="crlf2lf-test-") as directory:
                root = Path(directory)
                if scope == "--git-files":
                    subprocess.run(["git", "init", "-q", str(root)], check=True)
                for name, contents in fixtures.items():
                    (root / name).write_bytes(contents)
                for mode in ("--preview", "--check", "--write"):
                    with self.subTest(mode=mode):
                        result = self.run_helper(root, scope, mode)
                        self.assertEqual(result.returncode, 0, result.stderr)
                        self.assertIn(f"skipped {len(fixtures)} ", result.stdout)
                        for name, contents in fixtures.items():
                            self.assertEqual((root / name).read_bytes(), contents, name)

    def test_single_binary_file_is_skipped(self) -> None:
        with tempfile.TemporaryDirectory(prefix="crlf2lf-test-") as directory:
            candidate = Path(directory) / "map.bcmap"
            contents = b"ASCII-looking bytes\r\n"
            candidate.write_bytes(contents)
            result = self.run_helper(candidate)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Converted 0 file(s)", result.stdout)
            self.assertEqual(candidate.read_bytes(), contents)

    def test_utf8_text_preserves_bom_and_nonascii_bytes(self) -> None:
        with tempfile.TemporaryDirectory(prefix="crlf2lf-test-") as directory:
            root = Path(directory)
            fixtures = {
                "captions.sbv": "שלום\r\nעולם\rסוף\n".encode("utf-8"),
                "source.cs": b"\xef\xbb\xbfclass Point {}\r\n",
                "settings.yaml": b"key:\r\n\tvalue\r",
                "README": b"one\r\ntwo\rthree\n",
                "empty.txt": b"",
            }
            for name, contents in fixtures.items():
                (root / name).write_bytes(contents)
            checked = self.run_helper(root, "--all-files", "--check")
            self.assertEqual(checked.returncode, 1, checked.stderr)
            for name, contents in fixtures.items():
                self.assertEqual((root / name).read_bytes(), contents)
            result = self.run_helper(root, "--all-files")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Converted 4 file(s)", result.stdout)
            for name, contents in fixtures.items():
                self.assertEqual(
                    (root / name).read_bytes(),
                    contents.replace(b"\r\n", b"\n").replace(b"\r", b"\n"),
                    name,
                )


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
