#!/usr/bin/env python3
"""Copy a release directory to a Steam Frame and run its verified installer."""
import argparse
from pathlib import Path
import shlex
import subprocess
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('release_dir', type=Path)
    parser.add_argument('--host', default='frame')
    args = parser.parse_args()
    release = args.release_dir.resolve()
    if not (release / 'SHA256SUMS').is_file():
        parser.error('Use an unpacked release containing SHA256SUMS')
    if args.host.startswith('-'):
        parser.error('Invalid SSH host')
    with tempfile.TemporaryDirectory(prefix='omwf-') as temp:
        socket = str(Path(temp) / 'ssh')
        options = ['-o', 'ControlMaster=auto', '-o', 'ControlPersist=60', '-o', 'ControlPath=' + socket]
        try:
            subprocess.run(['ssh', *options, args.host, 'mkdir -p "$HOME/openmw-frame/releases"'], check=True)
            subprocess.run(['rsync', '-a', '-e', shlex.join(['ssh', *options]), str(release),
                            args.host + ':openmw-frame/releases/'], check=True)
            command = '"$HOME"/' + shlex.quote('openmw-frame/releases/' + release.name + '/setup.sh')
            subprocess.run(['ssh', *options, args.host, command], check=True)
        finally:
            subprocess.run(['ssh', *options, '-O', 'exit', args.host], capture_output=True)


if __name__ == '__main__':
    main()
