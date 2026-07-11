# AGENTS.md — smithjw-recipes

## Identifiers & naming

- **Namespace:** `com.github.smithjw.<type>.<App>` (NOT `smithjw-actions`). `<type>` = `download`, `pkg`, `jamf.upload`, `jamf`.
- **Files:** `<App>.<type>.recipe.yaml`; `<App>` = folder name in PascalCase_With_Underscores.
- **`MinimumVersion: '2.9'`** everywhere. `SOFTWARE_TITLE` = `<App>` (matches folder, no spaces).
- `ParentRecipe` references the parent's **Identifier** (download ← pkg ← jamf.upload).

## The download recipe (modern pattern — copy a migrated app, not a legacy one)

Reference apps: `OpenCode/`, `OpenAI/Codex`, `Anthropic/Claude`, `iTerm2/`, `Figma/`. Each
download recipe is: source info provider → **`URLDownloaderPython`** (never stock
`URLDownloader`) → `EndOfCheckPhase` → `StopProcessingIf` → `CodeSignatureVerifier`.

**StopProcessingIf predicate — exactly once per download recipe, after `EndOfCheckPhase`:**

```yaml
predicate: 'download_changed == False AND %BYPASS_STOP_PROCESSING_IF_DOWNLOAD_UNCHANGED% == False'
```

Two clauses on purpose: default `BYPASS_..._UNCHANGED: 'False'` gives CI idempotency (stop
only when the artefact is unchanged); set the input to any other value (`Bypass`, `True`)
to force the chain past the check. Don't blank it — an empty value errors. Never put this
predicate in pkg/upload recipes.

**DMG-of-app idiom (common here):** when the version doesn't come from an info provider,
use `AppDmgVersioner` (`dmg_path: '%pathname%'`) then verify `input_path: '%pathname%/<App>.app'`.
Quote the Team ID in the requirement; drop `cdhash`; skip `deep`/`strict` only when a
bundled framework or OR-clause requirement needs it (see the skill).

## Packaging & Jamf upload

- `pkg`: `AppPkgCreator` → `%RECIPE_CACHE_DIR%/%SOFTWARE_TITLE%-%version%.pkg`.
- `upload.jamf`: grahampugh `JamfPackageUploader` → `LastRecipeRunResult` →
  `StopProcessingIf %REMOVE_OLD_PACKAGES% == false` → `JamfPackageCleaner`
  (`PKG_NAME_MATCH: '%SOFTWARE_TITLE%-'`, `PKG_TO_KEEP: '2'`).

## Legacy recipes — don't use as templates

This repo also still holds **not-yet-migrated** recipes: `MinimumVersion '2.3'`, stock
`URLDownloader`, and a download → pkg → sign → install/jamf chain. Don't copy those for new
work — copy a migrated app instead.

## Testing (do not skip — see the skill's "Testing & verification")

There is no `mise`/`fnox` here yet, so run autopkg directly from the repo root:

```bash
export GITHUB_TOKEN=$(gh auth token)
autopkg run <App>/<App>.download.recipe.yaml -vvv --search-dir=.
autopkg run <App>/<App>.pkg.recipe.yaml -vvv --search-dir=.
```

`--search-dir=.` resolves custom processors (`URLDownloaderPython` ships in `jgstew-recipes`;
`FriendlyPathDeleter` in this repo's `SharedProcessors/`). `download` + `pkg` need **no**
Jamf creds — only `upload.jamf` does. Read the `-vvv` output: confirm the right asset
matched, the version is correct, and `Signature is valid`. Each recipe has its own cache
keyed by Identifier; to rebuild after a cached run, `rm -rf <cache>/<Identifier>` and run
with defaults (don't set `BYPASS=True` on a fresh download).

## Validation & commits

- Pre-commit (`.pre-commit-config.yaml`) runs the macadmin recipe checks plus
  forbid-overrides / forbid-trust-info. Run `pre-commit run -a` (or let the commit hook fire).
- There is **no** JSON schema in this repo (unlike `smithjw-actions-recipes`).
- Conventional Commits, e.g. `feat(<App>): add download/pkg/upload recipes`; `--no-gpg-sign`.
- Don't commit until asked.
