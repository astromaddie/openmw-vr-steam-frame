#!/usr/bin/env python3
"""Copy non-driver shared dependencies into a Linux package and retain distro licenses."""
import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess

# These belong to SteamOS/the active graphics stack. Never ship a driver or glibc.
SYSTEM = re.compile(r'^(?:ld-linux|lib(?:c|m|pthread|dl|rt|resolv|util|anl|gcc_s|stdc\+\+)\.so|lib(?:GLX|GLdispatch|GL|EGL|OpenGL|GLESv2|GLESv1_CM|vulkan|drm|gbm|nvidia|mesa|LLVM|X11|X11-xcb|Xext|Xrandr|Xcursor|Xinerama|Xi|Xrender|Xfixes|Xxf86vm|xcb|wayland|xkbcommon)(?:[_.-]|\.so))')


def dependencies(binary):
    result = subprocess.run(['ldd', str(binary)], capture_output=True, text=True, check=True)
    if 'not found' in result.stdout:
        raise RuntimeError(result.stdout)
    for line in result.stdout.splitlines():
        match = re.match(r'\s*(\S+) => (/.*?) \(', line)
        if match:
            yield match.group(1), Path(match.group(2))


def bundle(package):
    lib = package / 'lib'
    lib.mkdir(exist_ok=True)
    licenses = package / 'licenses/system-libraries'
    licenses.mkdir(parents=True, exist_ok=True)
    entries = {}
    queue = [package / name for name in ('openmw_vr', 'openmw', 'openmw-iniimporter')]
    while queue:
        for name, source in dependencies(queue.pop()):
            if name in entries or SYSTEM.match(name):
                continue
            target = lib / name
            shutil.copy2(source.resolve(), target)
            entries[name] = {'source': str(source.resolve())}
            # Debian/Ubuntu copyright files contain license notices for packaged libraries.
            owner = subprocess.run(['dpkg-query', '-S', str(source)], text=True, capture_output=True)
            if owner.returncode:
                owner = subprocess.run(['dpkg-query', '-S', str(source.resolve())], text=True, capture_output=True)
            if owner.returncode and str(source).startswith('/lib/'):
                owner = subprocess.run(['dpkg-query', '-S', '/usr' + str(source)], text=True, capture_output=True)
            if owner.returncode == 0:
                distro_package = owner.stdout.split(': ')[0].split(':')[0]
                notice = Path('/usr/share/doc') / distro_package / 'copyright'
                if notice.is_file():
                    shutil.copy2(notice, licenses / (distro_package + '.txt'))
                    entries[name]['package'] = distro_package
                    entries[name]['version'] = subprocess.check_output(
                        ['dpkg-query', '-W', '-f=${Version}', distro_package], text=True)
                else:
                    raise RuntimeError('Missing library license: ' + name)
            else:
                raise RuntimeError('Cannot identify license owner for ' + str(source))
            queue.append(target)
    (package / 'LIBRARIES.json').write_text(json.dumps(entries, indent=2) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('package', type=Path)
    bundle(parser.parse_args().package.resolve())
