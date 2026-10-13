#!/usr/bin/env python3
"""Repackage the pinned upstream AppImage without changing the host OS."""
# SPDX-License-Identifier: AGPL-3.0-only
import argparse
import hashlib
import json
import mmap
import os
from pathlib import Path
import platform
import shutil
import struct
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent.parent


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def squashfs_offset(path):
    """Find a v4 superblock, ignoring 'hsqs' strings in the ELF runtime."""
    with Path(path).open("rb") as stream:
        if stream.read(11) != b"\x7fELF\x02\x01\x01\x00AI\x02":
            raise ValueError("Expected a little-endian, 64-bit type-2 AppImage")
        with mmap.mmap(stream.fileno(), 0, access=mmap.ACCESS_READ) as data:
            offset = -1
            while True:
                offset = data.find(b"hsqs", offset + 1)
                if offset < 0:
                    raise ValueError("No valid SquashFS v4 superblock found")
                if offset + 96 > len(data):
                    continue
                major, minor = struct.unpack_from("<HH", data, offset + 28)
                used = struct.unpack_from("<Q", data, offset + 40)[0]
                if (major, minor) == (4, 0) and 96 <= used <= len(data) - offset:
                    return offset


def require_x86_64_library(path):
    with path.open("rb") as stream:
        header = stream.read(20)
    if (header[:6] != b"\x7fELF\x02\x01" or
            len(header) < 20 or struct.unpack_from("<H", header, 18)[0] != 62):
        raise ValueError(f"Expected an x86_64 ELF library: {path}")


def find_bzip2():
    # Fedora first; multilib installations must never select the i686 library.
    for directory in ("/usr/lib64", "/lib64", "/usr/lib/x86_64-linux-gnu",
                      "/lib/x86_64-linux-gnu"):
        for name in ("libbz2.so.1.0", "libbz2.so.1"):
            candidate = Path(directory) / name
            if candidate.is_file():
                require_x86_64_library(candidate)
                return candidate.resolve()
    raise ValueError("No x86_64 libbz2 found on this host")


def patch_appdir(appdir, bzip2, metadata):
    library_dir = appdir / "usr/lib"
    if not (appdir / "bin/CrealityPrint").is_file() or not library_dir.is_dir():
        raise ValueError("Unsupported AppDir layout")
    expected = json.loads((ROOT / "packaging/upstream.json").read_text())
    if sha256(appdir / "AppRun") != expected["apprun_sha256"]:
        raise ValueError("Upstream AppRun has changed; review the launcher before patching")
    shutil.copyfile(ROOT / "packaging/AppRun", appdir / "AppRun")
    (appdir / "AppRun").chmod(0o755)
    target = library_dir / "libbz2.so.1.0"
    # Do not follow an existing symlink when installing the compatibility copy.
    target.unlink(missing_ok=True)
    shutil.copyfile(bzip2, target)
    target.chmod(0o644)

    # Host WebKit requires Fedora's versioned Expat symbols. Leaving upstream's
    # unversioned libexpat in the search path produces loader warnings.
    removed = []
    for library in sorted(library_dir.glob("libexpat.so*")):
        removed.append(library.name)
        library.unlink()
    metadata["removed_bundled_libraries"] = removed

    desktop = appdir / "CrealityPrint.desktop"
    desktop.write_text(desktop.read_text().replace(
        "Name=CrealityPrint\n", "Name=Creality Print (Bazzite)\n"))
    notices = appdir / "usr/share/licenses/crealityprint-bazzite"
    notices.mkdir(parents=True)
    for name in ("LICENSE", "THIRD_PARTY.md"):
        shutil.copyfile(ROOT / name, notices / name)
    shutil.copyfile(ROOT / "licenses/bzip2-1.0.8.txt", notices / "bzip2-1.0.8.txt")
    info = appdir / "usr/share/crealityprint-bazzite"
    info.mkdir(parents=True)
    # Ship the actual compatibility sources with the generated binary.
    shutil.copytree(ROOT / "packaging", info / "packaging")
    shutil.copyfile(ROOT / "scripts/build.py", info / "build.py")
    (info / "build.json").write_text(json.dumps(metadata, indent=2) + "\n")


def check_dependencies(appdir):
    env = os.environ.copy()
    env["LC_ALL"] = "C"
    env["LD_LIBRARY_PATH"] = f"{appdir}/bin:{appdir}/usr/lib"
    # Do not let a developer's local overrides hide a packaging error.
    env.pop("LD_PRELOAD", None)
    result = subprocess.run(["ldd", str(appdir / "bin/CrealityPrint")],
                            env=env, text=True, capture_output=True, check=False)
    output = result.stdout + result.stderr
    if result.returncode or "not found" in output or "no version information" in output:
        raise ValueError("Dependency check failed on this build host:\n" + output)


def build(args):
    if platform.system() != "Linux" or platform.machine() != "x86_64":
        raise ValueError("Build on x86_64 Linux; the tested target is Bazzite 44")
    upstream = json.loads((ROOT / "packaging/upstream.json").read_text())
    source = args.input.expanduser().resolve(strict=True)
    tool = args.appimagetool.expanduser().resolve(strict=True)
    output = args.output.expanduser().absolute()
    if output.exists() or output.is_symlink():
        raise ValueError(f"Output already exists; choose a new --output: {output}")
    if not os.access(tool, os.X_OK):
        raise ValueError("appimagetool must be executable (chmod +x)")
    print("Verifying the upstream AppImage…", flush=True)
    if sha256(source) != upstream["sha256"]:
        raise ValueError("Input SHA-256 does not match packaging/upstream.json. "
                         "Use the original 7.3.0.6157 release, not a patched AppImage.")
    for program in ("unsquashfs", "ldd"):
        if not shutil.which(program):
            raise ValueError(f"Required build tool is missing: {program}")
    bzip2 = find_bzip2()
    # The bundled notice is for this version; fail if the host switches versions.
    if bzip2.name != "libbz2.so.1.0.8":
        raise ValueError("Expected bzip2 1.0.8; review its license before updating")
    offset = squashfs_offset(source)
    metadata = {
        "project": "crealityprint-bazzite",
        "compatibility_version": upstream["compatibility_version"],
        "upstream_version": upstream["version"],
        "upstream_url": upstream["url"],
        "upstream_sha256": upstream["sha256"],
        "upstream_source_url": upstream["source_url"],
        "launcher_sha256": sha256(ROOT / "packaging/AppRun"),
        "builder_sha256": sha256(Path(__file__)),
        "appimagetool_sha256": sha256(tool),
        "bzip2_version": "1.0.8",
        "bzip2_sha256": sha256(bzip2),
        "build_os": platform.freedesktop_os_release().get("PRETTY_NAME", "Linux"),
        "architecture": "x86_64",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    manifest = output.with_name(output.name + ".build.json")
    checksum = output.with_name(output.name + ".sha256")
    for sidecar in (manifest, checksum):
        if sidecar.exists() or sidecar.is_symlink():
            raise ValueError(f"Refusing to overwrite existing metadata: {sidecar}")
    # Keep staging on the destination filesystem. No FUSE, root, or automatic
    # downloads are needed for either extraction or packaging.
    with tempfile.TemporaryDirectory(prefix=".crealityprint-build-", dir=output.parent) as temp:
        work = Path(temp)
        appdir = work / "AppDir"
        subprocess.run(["unsquashfs", "-no-xattrs", "-no-progress", "-o", str(offset),
                        "-d", str(appdir), str(source)], check=True)
        runtime = work / "runtime-x86_64"
        with source.open("rb") as stream:
            runtime.write_bytes(stream.read(offset))
        metadata["runtime_sha256"] = sha256(runtime)
        patch_appdir(appdir, bzip2, metadata)
        check_dependencies(appdir)
        packaged = work / "crealityprint-bazzite.AppImage"
        env = os.environ.copy()
        env.update(ARCH="x86_64", APPIMAGE_EXTRACT_AND_RUN="1")
        for name in ("LD_LIBRARY_PATH", "LD_PRELOAD", "APPDIR", "APPIMAGE", "VERSION"):
            env.pop(name, None)
        print("Packaging with the verified upstream runtime…", flush=True)
        subprocess.run([str(tool), "--runtime-file", str(runtime),
                        "--mksquashfs-opt", "-no-xattrs", str(appdir), str(packaged)],
                       env=env, check=True)
        packaged.chmod(0o755)
        metadata["output_sha256"] = sha256(packaged)
        # Hard-link publication is atomic and cannot overwrite an existing file.
        os.link(packaged, output)
    manifest.write_text(json.dumps(metadata, indent=2) + "\n")
    checksum.write_text(f"{metadata['output_sha256']}  {output.name}\n")
    print(f"Built: {output}\nManifest: {manifest}\nChecksum: {checksum}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="Original upstream AppImage")
    parser.add_argument("--appimagetool", required=True, type=Path,
                        help="Path to a trusted executable appimagetool")
    parser.add_argument("--output", type=Path,
                        default=ROOT / "dist/crealityprint-bazzite.AppImage")
    args = parser.parse_args()
    try:
        build(args)
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"Build failed: {error}\n")


if __name__ == "__main__":
    main()
