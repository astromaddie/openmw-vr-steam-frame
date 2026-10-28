import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts/prepare_source.py"


def git(directory, *args):
    return subprocess.run(
        ["git", *args], cwd=directory, check=True, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    ).stdout.strip()


class PrepareSourceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "source"
        self.source.mkdir()
        git(self.source, "init", "-q")
        git(self.source, "config", "user.name", "Test")
        git(self.source, "config", "user.email", "test@example.invalid")
        (self.source / "render.cpp").write_text("pixelsPerMeter = 1;\n")
        git(self.source, "add", "render.cpp")
        git(self.source, "commit", "-qm", "pinned pristine source")
        self.commit = git(self.source, "rev-parse", "HEAD")
        self.patches = self.root / "patches"
        self.patches.mkdir()
        self.make_patch("03-larger-ui.patch", "pixelsPerMeter = 2;\n")
        git(self.source, "add", "render.cpp")
        git(self.source, "commit", "-qm", "intermediate patch state")
        self.make_patch("10-frame-settings.patch", "pixelsPerMeter = 3;\n")
        git(self.source, "add", "render.cpp")
        git(self.source, "commit", "-qm", "later patch state")
        self.make_patch("12-reference-init.patch", None, new_file="reference.cpp", new_content="int reference = 1;\n")
        git(self.source, "reset", "--hard", self.commit)
        (self.source / "reference.cpp").unlink(missing_ok=True)
        self.pending_patch = self.root / "12-reference-init.patch"
        (self.patches / "12-reference-init.patch").rename(self.pending_patch)

    def make_patch(self, name, render_content, new_file=None, new_content=None):
        if render_content is not None:
            (self.source / "render.cpp").write_text(render_content)
        if new_file:
            (self.source / new_file).write_text(new_content)
            git(self.source, "add", "-N", new_file)
        patch = subprocess.run(
            ["git", "diff", "--binary"], cwd=self.source, check=True,
            stdout=subprocess.PIPE,
        ).stdout
        (self.patches / name).write_bytes(patch)
        if render_content is not None:
            (self.source / "render.cpp").write_text("pixelsPerMeter = " + ("2" if name.startswith("03") else "3") + ";\n")
        if new_file:
            (self.source / new_file).unlink()

    def apply_to_source(self, patch_name):
        subprocess.run(
            ["git", "apply", str(self.patches / patch_name)], cwd=self.source,
            check=True,
        )

    def run_prepare(self, *args):
        return subprocess.run(
            [sys.executable, str(SCRIPT), str(self.source), str(self.patches), self.commit, *args],
            text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )

    def test_overlapping_prefix_reruns_without_rewriting_and_appends_new_patch(self):
        self.apply_to_source("03-larger-ui.patch")
        self.apply_to_source("10-frame-settings.patch")
        render = self.source / "render.cpp"
        original_content = render.read_bytes()
        original_mtime = render.stat().st_mtime_ns

        result = self.run_prepare()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Recognized canonical patch prefix: 2/2", result.stdout)
        self.assertEqual(render.read_bytes(), original_content)
        self.assertEqual(render.stat().st_mtime_ns, original_mtime)

        result = self.run_prepare("--check-only")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Recognized canonical patch prefix: 2/2", result.stdout)
        self.assertFalse((self.source / "reference.cpp").exists())

        self.pending_patch.rename(self.patches / "12-reference-init.patch")
        result = self.run_prepare()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Applying 12-reference-init.patch", result.stdout)
        self.assertEqual(render.read_bytes(), original_content)
        self.assertEqual((self.source / "reference.cpp").read_text(), "int reference = 1;\n")

    def test_unrelated_source_change_is_refused_and_preserved(self):
        self.apply_to_source("03-larger-ui.patch")
        self.apply_to_source("10-frame-settings.patch")
        custom = self.source / "local-customization.txt"
        custom.write_text("keep this edit\n")
        before = {path.name: path.read_bytes() for path in (self.source / "render.cpp", custom)}

        result = self.run_prepare()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("refusing to modify it", result.stderr)
        self.assertEqual((self.source / "render.cpp").read_bytes(), before["render.cpp"])
        self.assertEqual(custom.read_bytes(), before["local-customization.txt"])
        self.assertFalse((self.source / "reference.cpp").exists())


if __name__ == "__main__":
    unittest.main()
