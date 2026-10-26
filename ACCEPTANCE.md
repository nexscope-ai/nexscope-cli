# Development candidate acceptance

Date: 2026-10-26, Asia/Shanghai. Current candidate: `0.1.2.dev9`.

This record covers implementation in the independent CLI repository, adapted
from plugin commit `814f28016af6b3ff57ef12093a6bb133c4fb20b9`.
It does not certify the entire R2 release or any published plugin package.

## Implemented

- Prefer documented numeric `extractedPrice`, falling back to numeric `price`
  only when the first is absent/null; preserve zero, reject invalid numbers.
- Preserve products with unqualified remote currency symbols. Comparable price
  and currency remain unknown; `unresolvedCurrency`/`unresolvedPrice` and exact
  response evidence preserve the source values. Never infer USD from `$`.
- `workflow compare --resume` validates a completed candidates checkpoint,
  imports its search evidence, rebuilds registered detail requests and applies
  the original cumulative budget. Market, source type, auth mode and origin
  remain bound. Historical search imports do not enter session caches.
- Versioned datasets can generate HTML/CSV/Markdown offline while preserving
  provenance, input hashes, errors and request accounting. Raw input receipts
  and original dataset references have distinct meanings.
- Bounded manifests, duplicate-key/non-finite checks, safe relative filenames,
  link/reparse refusal, field validation, evidence/product/request/plan/result
  consistency, non-overwriting outputs and portable report links.
- Raw input limits: 10 MiB and 10,000 rows. Normalized datasets: 32 MiB;
  complete evidence: 64 MiB. Large CSV fields respect the file limit and restore
  the standard library's previous field limit afterward.
- Public standard-library regressions, resource/version checker, wheel verifier,
  six-job CI matrix, independent repository documentation and corrected notices.
  Current resource hashes change; historical Skill source snapshot hashes do not.

## Real-service acceptance and dev9 correction

The user authorized real paid testing and separately confirmed the browser's
connection action. An already logged-in **test-environment** account approved
the connection; CLI credentials were stored only in Windows Credential Manager.
The existing production environment key was not used. New persistent access was
confirmed before creation, and the authorized test connection remains available
for revocation in the test site's API Access page.

Maximum authorized data calls: **4**. Actual data calls: **4** (one search, three
details). CLI automatic retries: **0**. No further data request was issued after
the budget was exhausted. Authentication/account reads are separate from these
four data calls. No production database write, deployment or refund was made.

| Invocation | Actual result | Confirmed charge |
| --- | --- | --- |
| dev8 keyword search, one page, `desk lamp` | Business 13007; upstream errcode 10000, no matching results; no candidates | 0 credits, provider diagnostic |
| dev8 detail `B072MQ5BRX` | Server code 0 with one product, but CLI rejected `currency: "$"` as INVALID_PRODUCT | 90 credits, ledger |
| dev8 detail `B08N5WRWNW` | Server code 0, empty products; CLI EMPTY_DATA | 10 credits, ledger |
| dev9 detail `B072MQ5BRX`, one explicit verification call after the fix | COMPLETE / SUCCESS, exit 0, one product; no cache hit | 45 credits, ledger |

**Total attributed charge: 145 credits**, confirmed by three test-ledger debit
records and their user/route/time matches. The 10-credit empty-data debit remains
a real charge; no refund was requested or performed. The whole account balance
also changed because of concurrent activity, so its total delta was not used as
the attribution measure. The bounded provider-log sample includes the original
three attempts; the last verification is independently evidenced by its saved
request/response and matching ledger time/route. Complete distributed-trace
correlation and the registration/payment funnel are not certified here.

The live defect was reproduced with a failing regression, then fixed in the
shared validator and mapper. Remote currency metadata must be a string; an
unqualified symbol is retained as unresolved metadata, while normalized currency
and comparable price stay null. The saved real response revalidates offline with
dev9 and preserves the original source price `15.27` and symbol `$`. The original
dev8 FAILED record is unchanged, rather than relabeled as a successful run.

Historical pre-publication wheel: `dist/nexscope_cli-0.1.2.dev9-py3-none-any.whl`, SHA-256
`eaf560de2d949444b266308f9058acd679cfc622027e66f8ec616fb15f68a5e5`.
Installed-wheel regressions: **30 pass on Windows and 30 on Ubuntu WSL2**;
offline commands, loopback dual-auth, legacy adapters/runner, and dev8↔dev9
upgrade/rollback pass. Windows's real isolated OS-store persistence and cleanup
checks also pass. The live detail succeeded after these checks. Bundled adapter
version pins and current hashes were updated; historical source snapshots were
retained.

Evidence is under `dist/live-20261026-1600/` (Git ignored): immutable dev8/dev9
request bundles, filtered account snapshots, the four-call journal, read-only
ledger evidence, bounded redacted log metadata, offline revalidation, and three
original-failure audit report formats. `live-test-summary.json` indexes hashes
and results. Secrets and raw unfiltered logs are excluded. The failure reports
faithfully retain zero successful products from the original run; they are not
presented as a successful comparison.

**Disposition: partial acceptance.** Real account connection, valid live detail,
charge reconciliation and the currency correction pass. Successful keyword
selection/resume and a complete live multi-product comparison remain unaccepted
because the search returned no candidates and the original second detail was
empty. Mock/replay checks do not substitute for those missing live outcomes.

## Initial local verification (before the additional acceptance below)

- All 28 regression tests pass on Windows with Python 3.11.9 and 3.12.14.
- Actual wheel built with Python 3.12.14, pip 26.2.1, setuptools 84.0.0.
- Fresh venv outside the checkout; actual wheel installed without editable mode
  or dependencies. Source path injection removed; imports checked against
  `site-packages` in that environment. Wheel subpackages, resources and license
  files inspected. No bytecode or plugin metadata included in the wheel.
- Network and keyring/requests imports blocked for offline checks: template,
  samples, schema, doctor, plans, three report formats, versioned re-exports,
  fictional three-ASIN task, keyword selection/resume and partial failure.
  Paths contain spaces and Chinese characters.
- 10,000-row input and a near-10-MiB input with a larger normalized output;
  rejection of row/byte overflow, malformed input and inconsistent evidence.
- Fictional loopback HTTP service exercises both auth contexts, keyword resume,
  price-only detail responses and authenticated redirect refusal. Browser auth
  uses an in-memory fake keyring backend. It never accesses a real OS credential
  store, service account or billable Nexscope endpoint.
- Standalone installed legacy scripts preserve page/batch input, flags and env
  behavior. The legacy browser `run` path also passes with reviewed hash-pinned
  dependencies installed from PyPI. No arbitrary dependency is auto-installed
  during a query.
- Explicit old wheel supplied to the verifier: install `dev7`, upgrade to `dev8`,
  roll back to `dev7`, restore `dev8`; command version checks pass. User-report
  and test environment-key sentinels survive. This does not test real OS-keyring
  credential persistence across installer operations.

## Public source and hosted CI

The repository is public at <https://github.com/nexscope-ai/nexscope-cli> and the
initial implementation was pushed to `main` as commit
`d5ed885ef87a248f82827a8c6252760e340d7a7a`. Its
[installed-wheel workflow](https://github.com/nexscope-ai/nexscope-cli/actions/runs/40296830306)
completed successfully on Windows, Ubuntu and macOS with Python 3.11 and 3.12:
all six jobs passed. These are builds from an immutable Git commit. Private
live-test artifacts and credentials were excluded from the commit and push.

This closes the corresponding hosted installation/offline/loopback matrix,
including Windows Python 3.11. It does not certify a local Mac's Keychain,
real-account connection, real comparison workflows, Linux desktop credential
services, refunds or host integrations. No package release, tag or plugin upload
was made. See `docs/HANDOFF-MACOS.md` for the remaining Mac work.

## Additional executable acceptance, 2026-10-26

The same wheel was tested again, without changing its runtime code:
`nexscope_cli-0.1.2.dev8-py3-none-any.whl`, SHA-256
`653e86eb614ee649fddd58b10b36631dc9ce2c949af534c6b3371fc9b18b1024`.

| Acceptance item | Evidence and outcome |
| --- | --- |
| Windows external wheel installation | PASS: Python 3.12.14; 28 installed regressions, offline CLI/report/workflow cases, loopback dual-auth and legacy scripts/runner |
| Windows real Credential Manager | PASS: actual `keyring.backends.Windows`, unique fictional service entry, write/read and fingerprint verification; original account entries untouched |
| Windows credential persistence | PASS: test credential survives dev8→dev7→dev8 and package uninstall/reinstall; final deletion confirmed |
| Ubuntu WSL2 external installation | PASS: Python 3.12.3, glibc 2.39, Linux 6.6.87.2 WSL2; 28 installed regressions, offline cases, loopback dual-auth and legacy scripts/runner |
| Ubuntu WSL2 upgrade/rollback | PASS: dev7→dev8→dev7→dev8, executable version checks and user-report preservation |
| Linux desktop credential store prerequisite | BLOCKED: actual backend is `keyring.backends.fail`; CLI rejection confirmed (`UNAVAILABLE_FAIL_CLOSED`); no plaintext fallback |
| Real test API unauthenticated account request | PASS for negative authentication only: GET `/api/cli/account`, HTTP 200, business code 12003, no data returned; one request, no credentials sent |
| Live-data prerequisites before paid-test approval | The configured environment key belonged to production and was not used; later paid testing used a separately approved test browser connection as recorded above |

Ubuntu's system Python lacks `ensurepip`, and passwordless sudo was unavailable.
The verifier instead created an ordinary isolated venv and bootstrapped pip from
the explicit Python-bundled `pip-25.0.1-py3-none-any.whl`, SHA-256
`c46efd13b6aa8279f33f2864459c8ce587ea6a1a59ee20de055868d8f7688f7f`.
Application imports still came exclusively from the new venv's `site-packages`.
No system package, sudo configuration or WSL configuration was changed.

Repeat the Windows OS-store check with:

```sh
python scripts/verify_wheel.py dist/nexscope_cli-0.1.2.dev8-py3-none-any.whl --previous-wheel /path/to/nexscope_cli-0.1.2.dev7-py3-none-any.whl --with-dependencies --with-os-keyring
```

For WSL2, run the same verifier with its Linux Python, use mounted absolute wheel
paths and supply `--pip-wheel /path/to/reviewed/pip.whl` if ensurepip is missing.
`--with-os-keyring` requires a working real desktop credential store; the regular
dependency check also records availability and verifies fail-closed rejection.

Evidence files, ignored by Git and containing no credential values:

- `dist/verification-windows-os-keyring-py312.txt`
- `dist/verification-linux-wsl2-py312.txt`
- `dist/live-route-prerequisites.json`
- `dist/credential-prerequisites.json`
- `dist/acceptance-20261026.json` (artifact/test/verifier fingerprints)

That pre-live acceptance changed only verification scripts and documentation.
Its dev8 artifact and provenance remain unchanged. The later live correction is
separately versioned dev9, with its own wheel and checks recorded above.

The historical local wheel hashes and external-install transcripts are saved in
`dist/`, which is ignored by Git. Those tests predated source publication. Record
`git rev-parse HEAD` and the actual built wheel hash for each subsequent run;
documentation and build timestamps can change wheel bytes. A versioned release
still requires review and verification from an immutable source commit.

## Outstanding release gates

| Gate | Status |
| --- | --- |
| Windows fresh wheel, offline and loopback checks | Locally verified as described above |
| Real Windows OS keyring | Verified with isolated synthetic credentials, including upgrade/rollback/uninstall and cleanup |
| Real Nexscope login and valid test-account calls | PASS for an existing logged-in test account, approved CLI connection, and one successful dev9 live detail; new-user registration is not tested |
| Linux WSL2 install, offline, loopback and upgrade/rollback | Verified locally on Ubuntu Python 3.12.3; does not certify all Linux hosts |
| Linux Secret Service/KWallet | BLOCKED on this headless WSL2 host: `keyring.backends.fail`, fail-closed rejection verified; no desktop-store persistence acceptance |
| macOS install, OS keyring and upgrade/rollback | Hosted macOS/Python 3.11 and 3.12 installed-wheel jobs pass; local Keychain persistence, previous-wheel rollback and real browser connection still require the local Mac |
| Real search/detail response shapes, balance, pricing, billed/refund outcomes | PARTIAL: search upstream failure, detail/empty cases and 145-credit ledger reconciliation observed; fixed currency adapter passes live detail. Refunds and complete live comparison remain untested; future-call cost is still unknown |
| Codex/Claude Code natural-language three-ASIN, keyword and partial tasks | Not tested in real hosts |
| Registration → effective call → payment/refund server attribution | Existing CLI metadata only; backend/web chain not implemented or certified here |
| Named pilot owners, compatibility window, support and acceptance sample | Needs product/release assignment |
| Source commit and CI | Verify the checked-out commit with `git rev-parse HEAD` and inspect its actual CI results; the local evidence above predates source publication |
| Versioned releases and downstream Skills/plugin migration | No package release, tag or plugin upload; separate acceptance and release authorization remain required |
| Official published plugin contents | Not inspected or modified |

Do not mark the R2 release accepted, replace existing published Skills, or
describe fictional fixtures as live acceptance until the relevant gates pass.
The three known CLI defects are addressed; these external gates remain explicit.
