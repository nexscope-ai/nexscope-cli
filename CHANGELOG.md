# Changelog

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
