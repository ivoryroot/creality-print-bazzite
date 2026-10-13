# Publishing on GitHub

Suggested repository name: **crealityprint-bazzite**

Suggested description:

> Unofficial Creality Print AppImage compatibility fixes for Bazzite: bundled
> bzip2, XWayland defaults, and a repeatable local build recipe.

Suggested topics: `bazzite`, `creality-print`, `appimage`, `fedora`, `linux`,
`3d-printing`.

## Repository page

`README.md` is the GitHub repository landing page. No website build or GitHub
Pages deployment is required. The repository includes the launcher, builder,
tests, issue template, CI workflow, documentation, and notices.

Create an empty repository in your GitHub account. From this project directory:

```bash
git init -b main
git add README.md LICENSE THIRD_PARTY.md .gitignore .github packaging scripts tests docs licenses
git commit -m "Add Bazzite compatibility packaging for Creality Print 7.3.0"
```

Then use the remote URL GitHub provides for your repository:

```bash
git remote add origin YOUR_REPOSITORY_GIT_URL
git push -u origin main
```

Replace `YOUR_REPOSITORY_GIT_URL` with the actual URL. No repository owner or
download URL has been invented in the README. After publishing a release, add
its real download link to the Run section.

`.gitignore` excludes AppImages, build output, extracted directories, local
tools, backups and logs. Keep the 180 MB binaries out of Git history.

## Binary release

Use a tag such as **v7.3.0.6157-bazzite.1**. Copy the release notes from
`docs/RELEASE_NOTES.md`, including the tested platform and verification limits.

Attach the generated files together:

- `crealityprint-bazzite.AppImage`
- `crealityprint-bazzite.AppImage.sha256`
- `crealityprint-bazzite.AppImage.build.json`
- Corresponding source and third-party notices for the distributed components.

The upstream source/tag links and provenance are in `THIRD_PARTY.md` and
`packaging/upstream.json`. The repository's automatic source archive contains
the compatibility scripts; it does not contain the source for the complete
upstream slicer or its dependencies. Prepare the matching source materials
before distributing a binary. Publishing this source repository and local
build instructions is also useful on its own.

CI checks the scripts and regression tests. A successful CI run does not
certify graphics compatibility, printer communication or a completed print.

## Updating the pinned input

1. Obtain a new official AppImage and verify its upstream checksum.
2. Extract it separately and review its AppRun and bundled libraries.
3. Update `packaging/upstream.json` and the verbatim `packaging/upstream-AppRun`.
4. Adapt the compatibility launcher and build changes to the new layout.
5. Run the tests and rebuild; verify diagnostics and a desktop launch.
6. Test model import, slicing, preview and the printer features you intend to
   advertise. Update the validation record and release notes.

The builder refuses an existing output. Keep the previous version under
another filename until the replacement has been tested.
