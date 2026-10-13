# 7.3.0.6157 — Bazzite compatibility revision 1

Unofficial x86_64 compatibility repack of Creality Print 7.3.0.6157.

- Bundle libbzip2 1.0.8 as `libbz2.so.1.0`.
- Default to XWayland and disable WebKit's DMABUF renderer.
- Use the host's Expat to avoid bundled-library symbol-version warnings.
- Fix launcher paths containing spaces and preserve incoming library paths.
- Preserve model arguments, locale workaround and hybrid-GPU handling; honor
  explicit graphics overrides and PRIME offload.
- Add `--compat-diagnostics`, build provenance, notices and compatibility
  sources inside the AppImage.
- Add a checksum-verified, offline build recipe and regression tests.

Target: Bazzite 44 KDE Plasma Wayland, x86_64. See
[validation results](VALIDATION.md) for the exact local checks and limitations.
This release does not claim support for every Linux distribution or graphics
driver. Application binaries and printer profiles remain upstream's versions.
