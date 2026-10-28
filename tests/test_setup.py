import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('frame_setup', Path(__file__).parents[1] / 'scripts/frame_setup.py')
setup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(setup)


class SetupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        environment = patch.dict(os.environ, {'XDG_CONFIG_HOME': str(self.home / 'config'), 'XDG_DATA_HOME': str(self.home / 'data')})
        environment.start()
        self.addCleanup(environment.stop)
        self.build = self.home / 'build with spaces'
        self.build.mkdir()
        self.data = self.home / 'Morrowind/Data Files'
        self.data.mkdir(parents=True)
        (self.data / 'Morrowind.esm').touch()

    def test_removable_library_and_manifest_install_name(self):
        library = self.home / 'removable/Steam Library'
        steamapps = self.home / '.local/share/Steam/steamapps'
        steamapps.mkdir(parents=True)
        (steamapps / 'libraryfolders.vdf').write_text('"path" "' + str(library) + '"')
        (library / 'steamapps').mkdir(parents=True)
        (library / 'steamapps/appmanifest_22320.acf').write_text('"installdir" "TES3"')
        data = library / 'steamapps/common/TES3/Data Files'
        data.mkdir(parents=True)
        (data / 'Morrowind.esm').touch()
        self.assertEqual(setup.find_data(self.home), data.resolve())

    def test_optional_expansions_and_preserved_config(self):
        (self.data / 'Bloodmoon.esm').touch()
        setup.install(self.build, self.data, self.home, False)
        cfg = self.home / 'config/openmw-frame/openmw.cfg'
        self.assertIn('content=Bloodmoon.esm', cfg.read_text())
        self.assertNotIn('content=Tribunal.esm', cfg.read_text())
        cfg.write_text('custom content\n')
        settings = cfg.parent / 'settings.cfg'
        settings.write_text('custom settings\n')
        setup.install(self.build, self.data, self.home, False)
        self.assertEqual(cfg.read_text(), 'custom content\n')
        self.assertEqual(settings.read_text(), 'custom settings\n')
        self.assertFalse((self.home / '.config/openmw').exists())

    def test_launcher_exact_arguments_with_spaces(self):
        binary = self.build / 'openmw_vr'
        binary.write_text('#!/usr/bin/env python3\nimport json,sys,os\nprint(json.dumps(dict(argv=sys.argv[1:], crash_catcher=os.getenv("OPENMW_DISABLE_CRASH_CATCHER"))))\n')
        binary.chmod(0o755)
        launcher = setup.install(self.build, self.data, self.home, False)
        result = json.loads(subprocess.check_output([str(launcher), '--start', 'Balmora, Guild of Mages'], text=True))
        self.assertEqual(result['crash_catcher'], '1')
        args = result['argv']
        self.assertEqual(args[-2:], ['--start', 'Balmora, Guild of Mages'])
        self.assertEqual(args[:3], ['--replace', 'config', '--config'])
        self.assertIn(str(self.home / 'data/openmw-frame'), args)

    def test_save_import_copies_without_overwrite(self):
        source = self.home / 'old/saves/player'
        source.mkdir(parents=True)
        (source / 'a.omwsave').write_text('old')
        (source / 'b.omwsave').write_text('other')
        dest = self.home / 'data/openmw-frame/saves'
        (dest / 'player').mkdir(parents=True)
        (dest / 'player/a.omwsave').write_text('new')
        setup.import_saves(source.parent, dest)
        self.assertEqual((dest / 'player/a.omwsave').read_text(), 'new')
        self.assertEqual((dest / 'player/b.omwsave').read_text(), 'other')
        self.assertEqual((source / 'a.omwsave').read_text(), 'old')

    def test_bad_package_fails(self):
        (self.build / 'SHA256SUMS').write_text('0' * 64 + '  openmw_vr\n')
        with self.assertRaisesRegex(ValueError, 'checksum failed'):
            setup.verify_package(self.build)

    def test_nested_save_destination_is_rejected(self):
        source = self.home / 'source'
        source.mkdir()
        with self.assertRaisesRegex(ValueError, 'inside the import source'):
            setup.import_saves(source, source / 'saves')

    def test_wrong_architecture_rejected(self):
        binary = self.build / 'openmw_vr'
        binary.write_bytes(b'\x7fELF\x02\x01' + b'\0' * 12 + b'\x3e\x00')
        binary.chmod(0o755)
        with self.assertRaisesRegex(ValueError, 'ARM64'):
            setup.check_binary(self.build)

    def test_missing_library_version_on_stderr_is_rejected(self):
        binary = self.build / 'openmw_vr'
        binary.write_bytes(b'\x7fELF\x02\x01' + b'\0' * 12 + bytes([183, 0]))
        binary.chmod(0o755)
        result = subprocess.CompletedProcess([], 0, 'libc.so => /lib/libc.so', 'GLIBC_9.0 not found')
        with patch.object(setup.subprocess, 'run', return_value=result):
            with self.assertRaisesRegex(ValueError, 'Runtime library check failed'):
                setup.check_binary(self.build)

    def test_failed_importer_does_not_publish_config(self):
        (self.data.parent / 'Morrowind.ini').touch()
        with patch.object(setup.subprocess, 'run', side_effect=subprocess.CalledProcessError(1, 'importer')):
            with self.assertRaises(subprocess.CalledProcessError):
                setup.install(self.build, self.data, self.home, False)
        self.assertFalse((self.home / 'config/openmw-frame/openmw.cfg').exists())


if __name__ == '__main__':
    unittest.main()
