#!/usr/bin/env python3
"""Recognize and resume the canonical OpenMW Frame patch series safely."""

import argparse
import hashlib
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile


def run(command, *, cwd=None, stdout=None):
    return subprocess.run(
        command,
        cwd=cwd,
        check=True,
        stdout=stdout,
        stderr=subprocess.PIPE if stdout is not None else None,
    )


def source_hashes(root):
    """Return the content hash for every source file and symlink below root."""
    root = Path(root)
    result = {}
    for current, directories, files in os.walk(root, followlinks=False):
        current_path = Path(current)
        directories[:] = [name for name in directories if name != ".git"]
        for name in directories + files:
            if name == ".git":
                continue
            path = current_path / name
            if path.is_symlink():
                value = b"symlink\0" + os.readlink(path).encode("utf-8", "surrogateescape")
            elif path.is_file():
                value = b"file\0" + path.read_bytes()
            else:
                continue
            result[path.relative_to(root).as_posix()] = hashlib.sha256(value).hexdigest()
    return result


def canonical_patches(patches_dir):
    patches = sorted(Path(patches_dir).resolve().glob("*.patch"))
    if not patches:
        raise ValueError(f"No canonical patches found in {patches_dir}")
    return patches


def extract_pinned_source(source, commit, destination):
    archive = subprocess.Popen(
        ["git", "-C", str(source), "archive", commit], stdout=subprocess.PIPE
    )
    try:
        with tarfile.open(fileobj=archive.stdout, mode="r|") as tar:
            tar.extractall(destination, filter="data")
        if archive.wait() != 0:
            raise ValueError(f"Could not archive pinned source commit {commit}")
    finally:
        if archive.poll() is None:
            archive.kill()
            archive.wait()
        if archive.stdout:
            archive.stdout.close()
    run(["git", "init", "-q", str(destination)])


def identify_prefix(source, patches, commit):
    actual = source_hashes(source)
    with tempfile.TemporaryDirectory(prefix="openmw-frame-patch-prefix-") as temporary:
        pristine = Path(temporary) / "source"
        pristine.mkdir()
        extract_pinned_source(source, commit, pristine)
        if actual == source_hashes(pristine):
            return 0
        for index, patch in enumerate(patches, start=1):
            run(["git", "apply", str(patch)], cwd=pristine)
            if actual == source_hashes(pristine):
                return index
    return None


def prepare_source(source, patches_dir, commit, check_only=False):
    source = Path(source).resolve()
    patches = canonical_patches(patches_dir)
    prefix = identify_prefix(source, patches, commit)
    if prefix is None:
        raise ValueError(
            "Source does not match the pinned pristine tree or any complete canonical "
            "patch prefix; refusing to modify it (custom or partial edits may be present)."
        )
    print(f"Recognized canonical patch prefix: {prefix}/{len(patches)}")
    if check_only:
        return prefix
    for patch in patches[prefix:]:
        print(f"Applying {patch.name}")
        run(["git", "-C", str(source), "apply", str(patch)])
    return prefix


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", help="pinned source Git checkout")
    parser.add_argument("patches", help="directory containing canonical *.patch files")
    parser.add_argument("commit", help="pinned pristine Git commit")
    parser.add_argument("--check-only", action="store_true", help="recognize without modifying source")
    args = parser.parse_args(argv)
    try:
        prepare_source(args.source, args.patches, args.commit, args.check_only)
    except (OSError, subprocess.CalledProcessError, ValueError) as exc:
        detail = getattr(exc, "stderr", None)
        if detail:
            detail = detail.decode(errors="replace").strip()
        print(f"prepare_source: {detail or exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
