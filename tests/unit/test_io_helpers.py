from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from rsrf.io import (
    artifact_file_count,
    artifact_sha256,
    artifact_size_bytes,
    ensure_directory,
    file_sha256,
    read_json,
    write_json,
)


class EnsureDirectoryTests(unittest.TestCase):
    def test_creates_nested_directories(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "a" / "b" / "c"
            result = ensure_directory(path)
            self.assertTrue(path.is_dir())
            self.assertEqual(result, path)

    def test_existing_directory_is_no_op(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir)
            result = ensure_directory(path)
            self.assertEqual(result, path)


class JsonRoundtripTests(unittest.TestCase):
    def test_write_and_read(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test.json"
            payload = {"key": "value", "num": 42}
            write_json(path, payload)
            loaded = read_json(path)
            self.assertEqual(loaded, payload)

    def test_read_missing_file_raises(self) -> None:
        with self.assertRaises(FileNotFoundError):
            read_json(Path("/nonexistent/path.json"))

    def test_write_creates_parent_directories(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "nested" / "dir" / "test.json"
            write_json(path, {"x": 1})
            self.assertTrue(path.exists())


class FileSha256Tests(unittest.TestCase):
    def test_deterministic_hash(self) -> None:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("hello")
            f.flush()
            path = Path(f.name)
        try:
            h1 = file_sha256(path)
            h2 = file_sha256(path)
            self.assertEqual(h1, h2)
            self.assertEqual(len(h1), 64)
        finally:
            path.unlink()


class ArtifactHelpersTests(unittest.TestCase):
    def test_artifact_sha256_for_file(self) -> None:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("content")
            path = Path(f.name)
        try:
            h = artifact_sha256(path)
            self.assertEqual(h, file_sha256(path))
        finally:
            path.unlink()

    def test_artifact_sha256_for_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "a.txt").write_text("hello")
            (Path(tmpdir) / "b.txt").write_text("world")
            h = artifact_sha256(Path(tmpdir))
            self.assertEqual(len(h), 64)

    def test_artifact_sha256_missing_raises(self) -> None:
        with self.assertRaises(FileNotFoundError):
            artifact_sha256(Path("/does/not/exist"))

    def test_artifact_size_bytes_file(self) -> None:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("12345")
            path = Path(f.name)
        try:
            size = artifact_size_bytes(path)
            self.assertEqual(size, 5)
        finally:
            path.unlink()

    def test_artifact_size_bytes_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "a.txt").write_text("abc")
            (Path(tmpdir) / "b.txt").write_text("de")
            size = artifact_size_bytes(Path(tmpdir))
            self.assertEqual(size, 5)

    def test_artifact_size_bytes_missing_raises(self) -> None:
        with self.assertRaises(FileNotFoundError):
            artifact_size_bytes(Path("/does/not/exist"))

    def test_artifact_file_count_file(self) -> None:
        with tempfile.NamedTemporaryFile(delete=False) as f:
            path = Path(f.name)
        try:
            self.assertEqual(artifact_file_count(path), 1)
        finally:
            path.unlink()

    def test_artifact_file_count_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "a.txt").write_text("a")
            (Path(tmpdir) / "b.txt").write_text("b")
            self.assertEqual(artifact_file_count(Path(tmpdir)), 2)

    def test_artifact_file_count_missing_raises(self) -> None:
        with self.assertRaises(FileNotFoundError):
            artifact_file_count(Path("/does/not/exist"))


if __name__ == "__main__":
    unittest.main()
