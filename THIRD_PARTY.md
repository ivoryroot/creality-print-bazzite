# Attribution and upstream sources

This is an unofficial compatibility repack of Creality Print. Creality Print,
its artwork, and product names belong to their respective owners. This project
is not affiliated with or endorsed by Creality or the Bazzite project.

| Component | Origin | License / notes |
| --- | --- | --- |
| Creality Print 7.3.0.6157 | [Official release](https://github.com/CrealityOfficial/CrealityPrint/releases/tag/v7.3.0) | [Upstream AGPL-3.0 license](https://github.com/CrealityOfficial/CrealityPrint/blob/59ae8cbb0437dcc7236e27433ecd4aeb52be0244/LICENSE.txt); dependencies retain their own licenses |
| Original AppRun | Copied verbatim from the verified upstream AppImage into `packaging/upstream-AppRun` | Same upstream license; retained for comparison |
| Compatibility launcher, builder, tests and documentation | crealityprint-bazzite contributors, 2026 | AGPL-3.0-only; see `LICENSE` |
| Added libbzip2 1.0.8 | Copied from the build host's x86_64 bzip2 library | Julian R. Seward; notice in `licenses/bzip2-1.0.8.txt`; [source](https://sourceware.org/bzip2/downloads.html) and [Fedora packaging](https://src.fedoraproject.org/rpms/bzip2) |
| AppImage runtime | Reused from the verified upstream AppImage | [AppImage type2-runtime](https://github.com/AppImage/type2-runtime); runtime is not modified |
| appimagetool | Supplied by the builder; not added to the app | [Official project](https://github.com/AppImage/appimagetool) |

The source commit referenced by the upstream `v7.3.0` tag when inspected was
[`59ae8cbb0437dcc7236e27433ecd4aeb52be0244`](https://github.com/CrealityOfficial/CrealityPrint/tree/59ae8cbb0437dcc7236e27433ecd4aeb52be0244).
That identifies the published tag; it does not prove that every binary in the
release can be reproduced from that commit.

The builder preserves upstream payload files and existing notices except for
the documented launcher, desktop name and Expat changes. It adds this notice,
the AGPL license, the bzip2 notice, build metadata, and compatibility sources to
the AppImage under `usr/share`.

For a public binary release, provide the corresponding source and notices for
the distributed components alongside the binary. The compatibility repository
contains the repackaging changes, not Creality Print's full source or the full
source of its bundled dependencies. Publishing the build recipe alone does not
require uploading the upstream binary. See [publishing notes](docs/PUBLISHING.md).
