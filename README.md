[smithjw's](https://twitter.com/smithjw) AutoPkg recipes
===============

```sh
autopkg repo-add smithjw-recipes
```

Recipes require **AutoPkg 2.9** or higher. The repo standardises on
`URLDownloaderPython` and the bundled `StopProcessingIf download_changed`
predicate for cache-aware downloads; both became dependable defaults in 2.9.

## Recipe chain

Most apps in this repo follow a four-step chain so that overrides can plug in
at the level of granularity they need:

```
download -> pkg -> upload (Jamf-only) -> jamf (full Self Service flow)
```

1. **`<App>.download.recipe.yaml`** — fetches the upstream artefact via
   `URLDownloaderPython`, then verifies the signature and short-circuits the
   rest of the chain when nothing has changed:

   ```yaml
   - Processor: URLDownloaderPython
     Arguments:
       download_missing_file: '%DOWNLOAD_MISSING_FILE%'
       filename: '<App>.dmg'
       url: '%DOWNLOAD_URL%'

   - Processor: EndOfCheckPhase

   - Processor: StopProcessingIf
     Arguments:
       predicate: 'download_changed == %BYPASS_STOP_PROCESSING_IF_DOWNLOAD_UNCHANGED%'
   ```

   The pair of input keys `DOWNLOAD_MISSING_FILE` and
   `BYPASS_STOP_PROCESSING_IF_DOWNLOAD_UNCHANGED` exist on every download recipe
   and have safe defaults (`null` / `'False'`). `URLDownloaderPython` caches
   downloads by HTTP `ETag` / `Last-Modified` / `Content-Length` so unchanged
   downloads are no-ops, and the predicate makes sure the pkg / upload steps
   are skipped too. Set `BYPASS_STOP_PROCESSING_IF_DOWNLOAD_UNCHANGED=True` in
   an override when you need to force a rebuild.

2. **`<App>.pkg.recipe.yaml`** — wraps the downloaded artefact into a
   `.pkg` named `<SOFTWARE_TITLE>-<version>.pkg`. Universal recipes (where the
   filename includes `-Universal-`) wrap separate arm64 and x86_64 component
   pkgs into one installer whose postinstall script picks the right component
   at install time.

3. **`<App>.upload.jamf.recipe.yaml`** — uploads the pkg to Jamf Pro using
   [grahampugh/jamf-upload][jamf-upload] and prunes older copies (keeping the
   two most recent matches by default). It stops at "upload + cleanup" so that
   downstream override repos can layer their own policy / scope on top without
   inheriting any policy from this repo.

4. **`<App>.jamf.recipe.yaml`** — the legacy full-flow recipe that also creates
   a Self Service policy and smart group from the templates at the repo root.
   Newer recipes prefer the `.upload.` flavour and let downstream overrides own
   the policy. Both still ship for backwards compatibility.

Several recipes additionally provide `.sign.recipe.yaml`,
`.install.recipe.yaml`, `.munki.recipe.yaml`, or `-Patch.jamf.recipe.yaml`
companions that parent off the pkg recipe identifier.

## Why `URLDownloaderPython`?

The stock `URLDownloader` re-downloads files on every run, then relies on the
processor that wraps it (typically a packaging or upload step) to decide
whether to keep working. That's wasteful in CI and makes "did anything
actually change?" hard to answer when scanning logs.

`URLDownloaderPython` lifts ETag/Last-Modified/Content-Length comparison into
the download itself and emits a `download_changed` boolean that the
`StopProcessingIf` predicate consumes. The pkg / upload steps simply never run
when there's nothing new. Side-effects (pkg signing, Jamf uploads, package
cleanup) are skipped automatically without per-processor `pkg_uploaded` checks
scattered across the chain.

The processor ships in core AutoPkg from 2.9 onwards, so recipes pin
`MinimumVersion: '2.9'` and no extra parent repo is required to use it.

## Layout

```
smithjw-recipes/
├── <App>/                          # Per-app folders
│   ├── <App>.download.recipe.yaml
│   ├── <App>.pkg.recipe.yaml
│   ├── <App>.upload.jamf.recipe.yaml     # Upload-only; preferred for overrides
│   ├── <App>.jamf.recipe.yaml            # Legacy full Self Service flow
│   ├── <App>.png                         # Self Service icon
│   └── <App>.<sign|install|munki>.recipe.yaml   # Optional
├── SharedProcessors/               # Custom processors (FriendlyPathDeleter)
├── _Jamf Recipes/                  # Auxiliary Jamf templates
├── Policy-*.xml / SmartGroup-*.xml # Template XML used by .jamf.recipe.yaml
└── PatchTemplate-*.xml             # Templates used by -Patch.jamf.recipe.yaml
```

[jamf-upload]: https://github.com/grahampugh/jamf-upload
