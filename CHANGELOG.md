# Changelog

## 0.1.5

- Add 11 WooCommerce public store tools with production schemas, bringing the bundled snapshot to 576 entries.
- Synchronize short API paths and schema digests; retain authentication and paid/write execution gates.
- Update paired adapter pins and package metadata to 0.1.5 without changing adapter behavior.

## 0.1.4

- Fix HTTPS from the standalone binaries: they now use the bundled certifi CA
  certificates (unless `SSL_CERT_FILE` or `SSL_CERT_DIR` is set). In 0.1.3 the
  macOS binaries failed every online request, including `nexscope login`.
- Fix `nexscope login` to open the server's `loginUrl`; it now opens the browser
  and waits as intended.
- Certificate failures are reported as such instead of "Network unavailable".

## 0.1.3

- `nexscope login` signs in in one step: it opens the browser and waits until
  the connection completes (`--no-browser` only prints the link). `auth login`
  and `auth poll` are unchanged.
- `tools call` accepts inline `key=value` input typed from the tool schema,
  e.g. `keyword="portable blender"`, as an alternative to `--input FILE`.
  Without `--out`, results go to a new `<tool>-<timestamp>` folder. Paid calls
  still require `--execute --allow-paid` and, unless read-only, `--allow-write`.
- The README starts with three steps: install, sign in, search.

## 0.1.2

- Publish standalone binaries for macOS, Linux and Windows (amd64 and arm64)
  with release checksums, plus one-line installers (`install.sh`, `install.ps1`)
  that need no Python. Skill scripts also run from the standalone binary.
- Print rating scales in plain notation (10, not 1E+1) in reports and datasets.
- Omit the bundled catalog's internal export origin from `tools list` and
  `tools describe`; `--live` and `--catalog` still report the selected origin.

## 0.1.1

- Add a versioned 565-tool MCP snapshot, searchable discovery, complete schemas,
  explicit catalog refresh and bounded calls through both existing auth modes.
- Validate local and live tool schemas, including the deployed numeric-bound
  serialization compatibility case, without external schema fetching.
- Preserve complete redacted tool results and evidence; refuse redirects,
  implicit retries and unapproved effects, and report uncertain outcomes.
- Add public offline examples, structured error guidance, compatibility/rollback
  and contribution/support documentation.
- Preserve the existing Amazon comparison and CSV/JSON report behavior. Full
  catalog coverage does not certify every paid API, host workflow or R2 gate.

## 0.1.0

First independent release: two adapted Amazon research capabilities, bounded
comparison workflows, explicit browser/env authentication and offline reports.
