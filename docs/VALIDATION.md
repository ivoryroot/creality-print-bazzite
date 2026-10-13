# Local validation — 2026-10-13

| Item | Observed |
| --- | --- |
| OS | Bazzite 44, `44.20261011.0 (Kinoite)`, build `Stable (F44.20261012)` |
| Architecture | x86_64 |
| Desktop session | KDE Plasma, Wayland with XWayland available |
| GPU | NVIDIA GeForce RTX 3080 |
| NVIDIA driver | 615.78.08 |
| Creality Print | 7.3.0.6157 |
| Compatibility revision | 1.0.0 |
| Host bzip2 package | `bzip2-libs-1.0.8-23.fc44.x86_64` |
| Host Expat package | `expat-2.8.5-1.fc44.x86_64` |
| Packaging tool | appimagetool continuous build 313, git `854e19e`, 2026-10-04 |

## Passed

- Original image SHA-256 matched the digest on the official upstream release:
  `55dedb43928b792e311d3223bc8072402d84ed456cc05239e027a10297c89955`.
- 14 automated regression tests passed. They cover paths with spaces and
  Unicode, symlinks, argument boundaries, environment overrides, desktop-wide
  Wayland defaults, PRIME offload, exit status, missing-library diagnostics,
  input verification, overwrite refusal and safe library replacement.
- Bash syntax and ShellCheck 0.11.0 checks passed for the launcher.
- Build completed without FUSE or root, using the verified upstream runtime.
- The rebuilt AppImage's SHA-256 sidecar verified successfully.
- Extracted payload comparison confirmed that the slicer executable, printer
  profiles and all other original payload files are unchanged apart from
  AppRun, the desktop name and the two removed Expat files. Added files are the
  bzip2 copy, compatibility sources, build metadata and notices.
- The embedded desktop entry passed `desktop-file-validate`.
- `--compat-diagnostics` passed both through normal AppImage mounting and
  `--appimage-extract-and-run`, with `GDK_BACKEND=x11`, DMABUF disabled and
  `LC_ALL=C`.
- Direct library resolution found no missing libraries or Expat symbol-version
  warnings. Expat resolved to the host; bzip2, x264 and Speex DSP resolved from
  the AppImage.
- The rebuilt app stayed running for a 45-second desktop smoke test. Its
  XWayland window was inspected: the Prepare workspace, controls and 3D build
  plate rendered. The test instance was then closed.
- [The captured application window](images/creality-print-bazzite.png) shows
  that local GUI result. It is an actual screenshot, not a mockup.

## Limits

The application still logs GTK layout warnings. These did not prevent the
observed launch or rendered workspace. The test log did not contain the
previous missing-bzip2 failure, Expat version warnings or Wayland Error 71.

The smoke test did not cover slicing a model, G-code correctness, cloud login,
printer discovery, cameras, sending a print or physical printing. No claims
are made for those functions or for other distributions, GPUs or driver
versions. Automated CI checks the scripts only; it does not run this GUI test.

Exact hashes of the output and build inputs are recorded in the generated
`.AppImage.build.json` sidecar. Raw local diagnostic logs and temporary build
directories are intentionally excluded from the repository.
