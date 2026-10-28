#!/usr/bin/env python3
"""Install an existing OpenMW Frame build without altering another OpenMW profile."""
import argparse
import hashlib
import json
import os
import platform
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import tempfile


def atomic_write(path, text, mode=0o644):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=path.name + '.', dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as out:
            out.write(text)
        os.chmod(name, mode)
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def verify_package(build):
    manifest = build / 'SHA256SUMS'
    if not manifest.exists():
        return
    for line in manifest.read_text().splitlines():
        digest, name = line.split(maxsplit=1)
        name = name.lstrip('*')
        relative = Path(name)
        if relative.is_absolute() or '..' in relative.parts:
            raise ValueError('Invalid checksum path: ' + name)
        target = build / relative
        if not target.is_file() or hashlib.sha256(target.read_bytes()).hexdigest() != digest:
            raise ValueError('Package checksum failed: ' + name)


def steam_libraries(home):
    roots = [home / '.local/share/Steam', home / '.steam/steam']
    seen = set()
    for root in list(roots):
        vdf = root / 'steamapps/libraryfolders.vdf'
        if vdf.exists():
            for value in re.findall(r'"path"\s+"((?:\\.|[^"\\])*)"', vdf.read_text()):
                roots.append(Path(value.replace('\\\\', '\\').replace('\\"', '"')))
    for root in roots:
        root = root.resolve()
        if root not in seen:
            seen.add(root)
            yield root


def find_data(home, explicit=None):
    if explicit:
        candidates = [Path(explicit).expanduser()]
    else:
        candidates = []
        for library in steam_libraries(home):
            manifest = library / 'steamapps/appmanifest_22320.acf'
            install = 'Morrowind'
            if manifest.exists():
                match = re.search(r'"installdir"\s+"([^"\n]+)"', manifest.read_text())
                if match:
                    install = match.group(1)
            candidates.append(library / 'steamapps/common' / install)
    for candidate in candidates:
        data = candidate if (candidate / 'Morrowind.esm').is_file() else candidate / 'Data Files'
        if (data / 'Morrowind.esm').is_file():
            return data.resolve()
    raise ValueError('Morrowind data was not found. Install Steam app 22320 or use --morrowind-dir PATH.')


def quote_config(path):
    value = str(path)
    if any(c in value for c in '\n\r\0'):
        raise ValueError('A data path contains an unsupported control character')
    return '"' + value.replace('\\', '\\\\').replace('"', '\\"') + '"'


def check_binary(build):
    binary = build / 'openmw_vr'
    if not binary.is_file() or not os.access(binary, os.X_OK):
        raise ValueError('No executable openmw_vr in ' + str(build))
    with binary.open('rb') as src:
        header = src.read(20)
    if len(header) < 20 or header[:4] != b'\x7fELF' or header[4:6] != b'\x02\x01' or int.from_bytes(header[18:20], 'little') != 183:
        raise ValueError('Expected an ARM64 Linux ELF executable')
    env = os.environ.copy()
    env['LD_LIBRARY_PATH'] = str(build / 'lib') + ':' + env.get('LD_LIBRARY_PATH', '')
    result = subprocess.run(['ldd', str(binary)], env=env, text=True, capture_output=True)
    if result.returncode or 'not found' in result.stdout + result.stderr:
        raise ValueError('Runtime library check failed:\n' + result.stdout + result.stderr)


def check_host():
    if platform.machine().lower() not in ('aarch64', 'arm64'):
        raise ValueError('Run setup on the ARM64 Steam Frame; use install_remote.py from another computer')
    release = platform.freedesktop_os_release()
    if release.get('ID') != 'steamos' or release.get('VARIANT_ID') != 'vr':
        raise ValueError('Expected the SteamOS VR variant on the Steam Frame')
    print('Verified target: ARM64 SteamOS VR', release.get('VERSION_ID', ''))


def import_saves(source, destination):
    source = Path(source).expanduser().resolve()
    if not source.is_dir():
        raise ValueError('Save source is not a directory: ' + str(source))
    if source == destination.resolve():
        return
    if destination.resolve().is_relative_to(source):
        raise ValueError('Save destination must not be inside the import source')
    for item in source.rglob('*'):
        if item.is_symlink():
            continue
        target = destination / item.relative_to(source)
        if item.is_file() and not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, target)


def install(build, data, home, add_to_steam=True, saves=None):
    config_base = Path(os.environ.get('XDG_CONFIG_HOME', home / '.config'))
    data_base = Path(os.environ.get('XDG_DATA_HOME', home / '.local/share'))
    config = config_base / 'openmw-frame'
    userdata = data_base / 'openmw-frame'
    config.mkdir(parents=True, exist_ok=True)
    userdata.mkdir(parents=True, exist_ok=True)
    cfg = config / 'openmw.cfg'
    if not cfg.exists():
        lines = ['data=' + quote_config(data)]
        for name in ('Morrowind.esm', 'Tribunal.esm', 'Bloodmoon.esm'):
            if (data / name).is_file():
                lines.append('content=' + name)
        for name in ('Morrowind.bsa', 'Tribunal.bsa', 'Bloodmoon.bsa'):
            if (data / name).is_file():
                lines.append('fallback-archive=' + name)
        with tempfile.TemporaryDirectory(dir=config) as scratch:
            temporary = Path(scratch) / 'openmw.cfg'
            temporary.write_text('\n'.join(lines) + '\n')
            ini = data.parent / 'Morrowind.ini'
            if not ini.exists():
                ini = data.parent / 'morrowind.ini'
            if ini.exists():
                env = os.environ.copy()
                env['LD_LIBRARY_PATH'] = str(build / 'lib') + ':' + env.get('LD_LIBRARY_PATH', '')
                subprocess.run([str(build / 'openmw-iniimporter'), '-i', str(ini), '-c', str(temporary)], check=True, env=env)
            atomic_write(cfg, temporary.read_text())
    settings = config / 'settings.cfg'
    if not settings.exists():
        atomic_write(settings, '[GUI]\nfont size = 18\n\n[VR]\nmirror texture = false\n')
    if saves:
        import_saves(saves, userdata / 'saves')
    launcher = userdata / 'OpenMW Frame'
    command = [str(build / 'openmw_vr'), '--replace', 'config', '--config', str(config),
               '--user-data', str(userdata), '--resources', str(build / 'resources')]
    atomic_write(launcher, '#!/bin/sh\nset -eu\ncd ' + shlex.quote(str(build)) + '\n'
                 + 'export LD_LIBRARY_PATH=' + shlex.quote(str(build / 'lib')) + ':"${LD_LIBRARY_PATH:-}"\n'
                 + 'exec ' + shlex.join(command) + ' "$@"\n', 0o755)
    atomic_write(config / 'frame-install.json', json.dumps({'version': 1, 'build': str(build),
                 'data': str(data), 'launcher': str(launcher)}, indent=2) + '\n')
    if add_to_steam:
        quoted = ('"' + str(launcher) + '"').encode()
        shortcuts = list((home / '.local/share/Steam/userdata').glob('*/config/shortcuts.vdf'))
        if not any(quoted in path.read_bytes() for path in shortcuts):
            subprocess.run(['steamos-add-to-steam', str(launcher)], check=True)
    print('Launcher:', launcher)
    print('Settings:', config)
    print('Saves:', userdata / 'saves')
    return launcher


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('build_dir', nargs='?', type=Path)
    parser.add_argument('--morrowind-dir', default=os.environ.get('MORROWIND_DIR'))
    parser.add_argument('--no-steam', action='store_true', default=os.environ.get('ADD_TO_STEAM') == '0')
    parser.add_argument('--import-saves', type=Path)
    args = parser.parse_args()
    here = Path(__file__).resolve().parent
    build = (args.build_dir or (here if (here / 'openmw_vr').exists() else Path.home() / 'openmw-vr/build')).resolve()
    try:
        check_host()
        verify_package(build)
        check_binary(build)
        data = find_data(Path.home(), args.morrowind_dir)
        install(build, data, Path.home(), not args.no_steam, args.import_saves)
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        print('OpenMW Frame setup:', error, file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
