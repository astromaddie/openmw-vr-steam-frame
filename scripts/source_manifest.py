#!/usr/bin/env python3
"""Record or verify the exact source files used by a successful engine build."""
import argparse
import hashlib
import json
from pathlib import Path


def hashes(root):
    return {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(root.rglob('*'))
            if '.git' not in path.relative_to(root).parts and path.is_file()}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('manifest', type=Path)
    parser.add_argument('--verify', action='store_true')
    args = parser.parse_args()
    actual = hashes(args.source)
    if not actual:
        parser.error('Source tree is empty')
    if args.verify:
        if not args.manifest.is_file() or json.loads(args.manifest.read_text()) != actual:
            parser.error('Source differs from the successful build; rebuild before packaging')
    else:
        args.manifest.write_text(json.dumps(actual, indent=2) + '\n')
