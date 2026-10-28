"""Run the production VR player startup against delayed and persisted storage."""
import os
from pathlib import Path
import shutil
import subprocess
import unittest


SOURCE = Path(os.environ["OPENMW_SOURCE"])
LUA = shutil.which("lua") or shutil.which("lua5.4") or shutil.which("lua5.3") or shutil.which("luajit")
HARNESS = Path(__file__).with_suffix(".lua")


@unittest.skipUnless(LUA, "install Lua to run production player startup settings tests")
class PlayerSettingsStartupTests(unittest.TestCase):
    def test_vr_lua_modules_are_builtin_resources(self):
        data = SOURCE / "files/data"
        cmake = (data / "CMakeLists.txt").read_text()
        listed = {
            line.strip()
            for line in cmake.splitlines()
            if line.strip().startswith("scripts/")
        }
        modules = {
            path.relative_to(data).as_posix()
            for path in (data / "scripts/omw/vr").rglob("*.lua")
        }
        self.assertEqual(modules - listed, set(), "unshipped VR Lua resources")

    def test_empty_and_saved_storage(self):
        result = subprocess.run(
            [LUA, str(HARNESS)],
            env={**os.environ, "OPENMW_SOURCE": str(SOURCE)},
            check=False,
            text=True,
            capture_output=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
