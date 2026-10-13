"""Regression tests for the launcher contract and safe repackaging."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("builder", ROOT / "scripts/build.py")
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class LauncherTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="creality test ' ")
        self.addCleanup(self.temp.cleanup)
        self.appdir = Path(self.temp.name) / "App Dir é"
        (self.appdir / "bin").mkdir(parents=True)
        (self.appdir / "usr/lib").mkdir(parents=True)
        shutil.copyfile(ROOT / "packaging/AppRun", self.appdir / "AppRun")
        (self.appdir / "AppRun").chmod(0o755)
        executable = self.appdir / "bin/CrealityPrint"
        executable.write_text(
            "#!/usr/bin/env python3\nimport json, os, sys\n"
            "print(json.dumps({'args': sys.argv[1:], 'env': dict(os.environ)}))\n"
            "sys.exit(int(os.environ.get('TEST_EXIT', '0')))\n")
        executable.chmod(0o755)
        self.env = os.environ.copy()
        for key in ("GDK_BACKEND", "WEBKIT_DISABLE_DMABUF_RENDERER", "LD_LIBRARY_PATH",
                    "LD_PRELOAD", "APPDIR", "TEST_EXIT", "CREALITYPRINT_GDK_BACKEND",
                    "CREALITYPRINT_WEBKIT_DISABLE_DMABUF_RENDERER"):
            self.env.pop(key, None)
        self.env["__GLX_VENDOR_LIBRARY_NAME"] = "test-explicit-vendor"

    def run_launcher(self, *args, launcher=None, **variables):
        return subprocess.run([str(launcher or self.appdir / "AppRun"), *args],
                              cwd="/", env=self.env | variables, text=True,
                              capture_output=True, check=False)

    def test_path_spaces_unicode_and_model_arguments(self):
        arguments = ["model with spaces.stl", "quote's model.3mf", "$(literal).obj", "--help"]
        result = self.run_launcher(*arguments)
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["args"], arguments)
        self.assertEqual(payload["env"]["APPDIR"], str(self.appdir))
        self.assertEqual(payload["env"]["GDK_BACKEND"], "x11")
        self.assertEqual(payload["env"]["WEBKIT_DISABLE_DMABUF_RENDERER"], "1")
        self.assertEqual(payload["env"]["LC_ALL"], "C")
        self.assertEqual(payload["env"]["LD_LIBRARY_PATH"],
                         f"{self.appdir}/bin:{self.appdir}/usr/lib")

    def test_explicit_overrides_and_library_path_are_preserved(self):
        result = self.run_launcher(CREALITYPRINT_GDK_BACKEND="wayland",
                                   CREALITYPRINT_WEBKIT_DISABLE_DMABUF_RENDERER="0",
                                   LD_LIBRARY_PATH="/custom libraries:/another")
        env = json.loads(result.stdout)["env"]
        self.assertEqual(env["GDK_BACKEND"], "wayland")
        self.assertEqual(env["WEBKIT_DISABLE_DMABUF_RENDERER"], "0")
        self.assertEqual(env["__GLX_VENDOR_LIBRARY_NAME"], "test-explicit-vendor")
        self.assertEqual(env["LD_LIBRARY_PATH"],
                         f"{self.appdir}/bin:{self.appdir}/usr/lib:/custom libraries:/another")

    def test_symlink_and_exit_status(self):
        link = Path(self.temp.name) / "launcher link"
        link.symlink_to(self.appdir / "AppRun")
        result = self.run_launcher(launcher=link, TEST_EXIT="37")
        self.assertEqual(result.returncode, 37)
        self.assertEqual(json.loads(result.stdout)["env"]["APPDIR"], str(self.appdir))

    def test_desktop_global_settings_do_not_defeat_compatibility(self):
        result = self.run_launcher(GDK_BACKEND="wayland", WEBKIT_DISABLE_DMABUF_RENDERER="0")
        env = json.loads(result.stdout)["env"]
        self.assertEqual(env["GDK_BACKEND"], "x11")
        self.assertEqual(env["WEBKIT_DISABLE_DMABUF_RENDERER"], "1")

    def test_prime_offload_does_not_force_mesa(self):
        self.env.pop("__GLX_VENDOR_LIBRARY_NAME")
        result = self.run_launcher(__NV_PRIME_RENDER_OFFLOAD="1")
        self.assertNotIn("__GLX_VENDOR_LIBRARY_NAME", json.loads(result.stdout)["env"])

    def test_diagnostics_flags_missing_libraries_without_starting_gui(self):
        info = self.appdir / "usr/share/crealityprint-bazzite"
        info.mkdir(parents=True)
        (info / "build.json").write_text('{"test": true}\n')
        ldd = self.appdir / "bin/ldd"
        ldd.write_text("#!/bin/sh\nprintf 'libmissing.so => not found\\n'\n")
        ldd.chmod(0o755)
        result = self.run_launcher("--compat-diagnostics",
                                   PATH=f"{self.appdir}/bin:{self.env['PATH']}")
        self.assertEqual(result.returncode, 1)
        self.assertIn("libmissing.so => not found", result.stdout)
        self.assertNotIn('"args":', result.stdout)


class BuildTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="creality build tests ")
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)

    def test_squashfs_offset_ignores_magic_in_runtime(self):
        header = bytearray(256)
        header[:11] = b"\x7fELF\x02\x01\x01\x00AI\x02"
        header[40:44] = b"hsqs"
        filesystem = bytearray(128)
        filesystem[:4] = b"hsqs"
        struct.pack_into("<HH", filesystem, 28, 4, 0)
        struct.pack_into("<Q", filesystem, 40, 128)
        appimage = self.directory / "fixture.AppImage"
        appimage.write_bytes(header + filesystem)
        self.assertEqual(builder.squashfs_offset(appimage), 256)

    def test_invalid_appimage_rejected(self):
        path = self.directory / "not an AppImage"
        path.write_bytes(b"bad input")
        with self.assertRaisesRegex(ValueError, "type-2 AppImage"):
            builder.squashfs_offset(path)

    def test_i686_library_rejected(self):
        path = self.directory / "libbz2.so.1"
        path.write_bytes(b"\x7fELF\x01\x01" + b"\x00" * 32)
        with self.assertRaisesRegex(ValueError, "x86_64 ELF"):
            builder.require_x86_64_library(path)

    def fixture_appdir(self):
        appdir = self.directory / "AppDir"
        (appdir / "bin").mkdir(parents=True)
        (appdir / "bin/CrealityPrint").write_bytes(b"unchanged slicer")
        (appdir / "usr/lib").mkdir(parents=True)
        (appdir / "CrealityPrint.desktop").write_text("[Desktop Entry]\nName=CrealityPrint\n")
        shutil.copyfile(ROOT / "packaging/upstream-AppRun", appdir / "AppRun")
        return appdir

    def test_patch_copies_bzip2_and_removes_expat_without_touching_symlink_target(self):
        appdir = self.fixture_appdir()
        external = self.directory / "external-library"
        external.write_bytes(b"do not overwrite")
        (appdir / "usr/lib/libbz2.so.1.0").symlink_to(external)
        (appdir / "usr/lib/libexpat.so.1").symlink_to(external)
        bzip2 = self.directory / "libbz2.so.1.0.8"
        bzip2.write_bytes(b"bzip fixture")
        metadata = {}
        builder.patch_appdir(appdir, bzip2, metadata)
        self.assertEqual(external.read_bytes(), b"do not overwrite")
        installed = appdir / "usr/lib/libbz2.so.1.0"
        self.assertFalse(installed.is_symlink())
        self.assertEqual(installed.read_bytes(), b"bzip fixture")
        self.assertFalse((appdir / "usr/lib/libexpat.so.1").exists())
        self.assertEqual((appdir / "bin/CrealityPrint").read_bytes(), b"unchanged slicer")
        self.assertTrue((appdir / "usr/share/licenses/crealityprint-bazzite/LICENSE").exists())

    def test_changed_launcher_rejected_before_mutation(self):
        appdir = self.fixture_appdir()
        (appdir / "AppRun").write_text("unexpected new launcher")
        with self.assertRaisesRegex(ValueError, "AppRun has changed"):
            builder.patch_appdir(appdir, self.directory / "unused", {})
        self.assertEqual((appdir / "AppRun").read_text(), "unexpected new launcher")

    def test_failed_dependency_resolution_is_fatal(self):
        completed = subprocess.CompletedProcess([], 0, "libnew.so => not found\n", "")
        with patch.object(builder.subprocess, "run", return_value=completed):
            with self.assertRaisesRegex(ValueError, "Dependency check failed"):
                builder.check_dependencies(self.directory)

    def test_existing_output_and_original_input_are_preserved(self):
        output = self.directory / "existing.AppImage"
        output.write_bytes(b"keep this original")
        result = subprocess.run([
            "python3", str(ROOT / "scripts/build.py"), "--input", str(output),
            "--appimagetool", "/bin/true", "--output", str(output)],
            capture_output=True, text=True, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Output already exists", result.stderr)
        self.assertEqual(output.read_bytes(), b"keep this original")

    def test_wrong_input_checksum_rejected(self):
        source = self.directory / "wrong.AppImage"
        source.write_bytes(b"wrong upstream release")
        output = self.directory / "output.AppImage"
        result = subprocess.run([
            "python3", str(ROOT / "scripts/build.py"), "--input", str(source),
            "--appimagetool", "/bin/true", "--output", str(output)],
            capture_output=True, text=True, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("SHA-256 does not match", result.stderr)
        self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
