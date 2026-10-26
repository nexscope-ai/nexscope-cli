# CLI acceptance record

Date: 2026-10-26, Asia/Taipei. Current version: `0.1.0` (first independent version).
The acceptance source baseline is `0.1.2.dev9` at
`0252b0ec8a02ecdceb4deb691f3c3d0c12b8ed65`. The user selected `0.1.0` for the
first independent version after dev11 source verification. Historical
records below retain their original uncommitted/local-candidate context.

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
| macOS install, OS keyring and upgrade/rollback | PASS locally for arm64/macOS 27.0, Python 3.11.15/3.12.13; real Keychain dev9↔dev10 and uninstall persistence/cleanup on Python 3.12.13, with an explicitly approved browser connection; see completion record below |
| Real search/detail response shapes, balance, pricing, billed/refund outcomes | PARTIAL: Mac live comparison and 2-success/1-failure case pass with 6 calls / 230-credit reconciliation; search failed, so live resume is BLOCKED. Earlier Windows 145 credits are separate. Refund/server-attribution gates remain unaccepted |
| Codex/Claude Code natural-language three-ASIN, keyword and partial tasks | Offline/mock tasks pass in both actual hosts. Claude dev10 and fresh configured Codex dev11 live direct/partial pass. Live search/resume and published-plugin gates remain unaccepted; see fresh-session correction below |
| Registration → effective call → payment/refund server attribution | Existing CLI metadata only; backend/web chain not implemented or certified here |
| Named pilot owners, compatibility window, support and acceptance sample | Needs product/release assignment |
| Source commit and CI | Verify the checked-out commit with `git rev-parse HEAD` and inspect its actual CI results; the local evidence above predates source publication |
| Versioned releases and downstream Skills/plugin migration | No package release, tag or plugin upload; separate acceptance and release authorization remain required |
| Official published plugin contents | Not inspected or modified |

Do not mark the R2 release accepted, replace existing published Skills, or
describe fictional fixtures as live acceptance until the relevant gates pass.
The three known CLI defects are addressed; these external gates remain explicit.

## Local macOS free-phase record, 2026-10-26 (Asia/Taipei)

Actual checkout: `main`, HEAD `0252b0ec8a02ecdceb4deb691f3c3d0c12b8ed65`;
new clone, initially clean. No pre-existing checkout or user changes were replaced.
Platform: **macOS 27.0 (26A428), arm64**. Executed interpreters:
Python **3.11.15** (uv) and **3.12.13** (mise). System Python 3.9.6 was not used
for the package. No x86_64, other local OS, or post-change hosted CI claim is made.

The final dev10 candidate is that HEAD **plus local uncommitted fixes and version
pins**, not an immutable dev10 Git commit. No commit, push, tag, release, PyPI
publication or downstream plugin update was performed. Wheel bytes were compared
against every current packaged source/resource file and matched.

| Artifact | Actual SHA-256 |
| --- | --- |
| Initial Mac dev9 wheel, `dist/nexscope_cli-0.1.2.dev9-py3-none-any.whl` | `55606905a9c5acf5c0d5c7e63c517a7525109e825922a0388dc8446ff73ea13c` |
| Rebuilt, verified dev9 predecessor, `dist/rebuilt/nexscope_cli-0.1.2.dev9-py3-none-any.whl` | `618c18c6c7e134eb992479242d60fa672d9ac99bfd2519b8b3529bc2d7fff02e` |
| Final local dev10, `dist/dev10/nexscope_cli-0.1.2.dev10-py3-none-any.whl` | `eb36658d08cf523c714444bb82ce5fc3acf16a305248fbcbd688f3c5fc25744e` |

### PASS

- `python scripts/check_resources.py`: resource integrity and paired adapter
  pins pass. Historical `sourceSnapshot` hashes are unchanged.
- Actual wheels installed into fresh environments outside the checkout;
  source-path injection removed and imports checked against `site-packages`.
  Dev9: **30 installed regressions per interpreter**. Dev10: **31 per
  interpreter**, offline reports, space/non-ASCII paths, failure exits, output
  preservation and fictional loopback dual-auth checks pass.
- Real `keyring.backends.macOS` on Python 3.12.13: unique synthetic credential
  write/read, dev9→dev10→dev9→dev10 persistence, uninstall/reinstall retention,
  and deletion verification pass. Only verifier-owned synthetic entries were
  deleted; Keychain protections were not changed. Python 3.11 rollback/version
  and user-report retention pass; real-store persistence was exercised on 3.12.
- User logged into the test frontend and explicitly approved **Connect
  Nexscope** before a persistent CLI Key was created. Installed dev10 completed
  `auth poll`; browser and CLI account matched. Credential exists in Keychain,
  pending credential was removed, and its value was absent from this run's
  controlled text artifacts. This is not a whole-disk secret audit.
- Browser-account `account` with an unrelated environment sentinel still
  matched the browser account. Installed-wheel negative checks show that an
  empty browser namespace does not use an environment key, and missing env-mode
  variables neither read Keychain nor fall back to the connected browser.
  Both negatives exited 1 with network blocked. Loopback positive dual-auth
  coverage remains distinct from two real-account positive modes.
- Actual **Codex CLI 0.163.0** and **Claude Code 2.1.308** received natural-language
  tasks and drove the installed dev10 CLI: three-product COMPLETE (3 successes,
  exit 0, 3 mock requests), keyword CANDIDATES_READY (1), saved `--resume`
  COMPLETE (2 new requests, cumulative 3, exit 0), PARTIAL (2 successes + 1
  EMPTY_DATA, exit 1, 3 requests), all three report formats and offline
  re-export. Search evidence was byte-identical on resume, and ASIN-selected
  mock detail fields now match their candidates. These are **offline/mock host
  runs**, not live data or published-plugin acceptance. Both hosts also ran the
  original dev9; its original outputs and the discovered mismatch are retained.
- Own-account **API Access → Call Details** provides a read-only reconciliation
  entry with UTC time, masked key, route, actual credits, request and diagnostic
  IDs. Only older calls appeared in the observed latest page; the new Mac key
  had no data-call row. No CSV/key export, credential discovery or database access
  was used. The whole account balance delta was not attributed to this task.

### FAIL, preserved and corrected

- Original `verify_wheel.py` copied the Python executable. Both local Python
  distributions aborted with SIGABRT; direct reproduction showed dyld could not
  find relative `libpython3.12.dylib`. A failing verifier regression was added
  before the fix. Using the platform's normal venv symlink behavior on POSIX
  fixed both interpreters; Windows retains copies. The external-wheel regression
  and final installed checks pass. Original failure logs remain unchanged.
- Actual Claude host inspection exposed known mock ASINs receiving another
  fixture's title/price in detail responses. The new regression failed for the
  three candidates before the correction. Dev10 selects a matching fixture by
  ASIN, preserving the existing deterministic fallback for arbitrary fictional
  IDs. Both hosts re-executed against the rebuilt dev10 and confirmed matching
  fields. Static mock keyword data remains intentionally fictional.

### BLOCKED / separate gates

- Live successful multi-product comparison, keyword/resume, real partial
  completion and corresponding live-host tasks: **this free-phase checkpoint preceded the later 20-call authorization;
  see the post-approval record below for actual outcomes**. Prior four-call authorization is
  exhausted. No new live product/search request has been sent.
- A second real env-api-key account has not been provisioned or used. Positive
  real env-mode account isolation is unaccepted; no browser credential was
  exported into the environment to simulate it.
- Refunds, complete server-side attribution, registration/payment funnel,
  Linux desktop keyrings, named pilot/support ownership and downstream release
  gates remain separate. Existing Codex host startup reported a stale
  `nexscope_test` MCP OAuth `invalid_grant`; offline CLI tasks used no MCP query
  and no host settings were changed. Published-plugin discovery was not tested.

New **Nexscope data calls: 0; automatic data retries: 0**. Five CLI auth/account
HTTP requests were made: one start, one poll, one acknowledgement and two account
reads; browser login/approval traffic is separate. No newly attributed data
debit exists in this run's evidence; this is not a complete account-ledger audit.
The old **145 credits** remain historical and are not charged to this Mac run.
Claude's two host runs separately reported model list-price costs of
USD 0.4659312 and 0.6272848; these are not independently reconciled charges or
Nexscope credits. Codex supplied token usage without a monetary amount.

Commands (replace `python` with the recorded 3.11 or 3.12 interpreter):

```sh
python -m pip wheel --no-deps --wheel-dir dist/dev10 .
python scripts/check_resources.py
python scripts/verify_wheel.py dist/dev10/nexscope_cli-0.1.2.dev10-py3-none-any.whl --previous-wheel dist/rebuilt/nexscope_cli-0.1.2.dev9-py3-none-any.whl --with-dependencies --with-os-keyring
python scripts/test_verify_wheel.py dist/dev10/nexscope_cli-0.1.2.dev10-py3-none-any.whl
```

Python 3.11 ran the verifier with `--previous-wheel`, without the two keyring/
dependency flags. Private evidence: **`dist/macos-20261026/` (Git ignored)**,
including original failures, build/install/verification transcripts, auth/account
snapshots without keys, read-only billing table, host prompts/events, copied host
outputs, `acceptance-summary.json` and file hashes. Offline reruns are explicitly
labeled and never replace original failures. The external `live-env` and host
working directories under `~/.local/share/nexscope-cli-acceptance/20261026/` are
retained for pending acceptance; no task worktrees or branches were created.

## Post-approval live acceptance on this Mac

The user explicitly expanded authorization to **20 data calls, no credit ceiling**,
and delegated sample selection. Fixed samples: `B072MQ5BRX`, `B07FZ8S74R`, with
`B08N5WRWNW` solely as the historical failure sample; one keyword,
**`wireless mouse`**, on `amazon.com`. All runs used the installed dev10 wheel
SHA-256 `eb36658d08cf523c714444bb82ce5fc3acf16a305248fbcbd688f3c5fc25744e`
outside the checkout, origin `https://test-claw-callback.nexscope.ai`, and the
approved Mac browser-account Keychain connection. Source remains the recorded
dev9 HEAD plus local uncommitted dev10 changes. No production call occurred.

| Gate | Status and evidence |
| --- | --- |
| Actual Claude Code direct two-product workflow | **PASS**: COMPLETE, 2/2 successes, exit 0; 2 requests, no cache hits/retries; three report formats and original responses |
| Single live keyword search | **FAIL, upstream**: business 13007, empty candidates, exit 1; 1 request; original failure preserved |
| Live keyword `--resume` | **BLOCKED**: no completed CANDIDATES_READY checkpoint; no duplicate search, altered keyword or extra selection |
| Actual Claude Code partial workflow | **PASS**: B072MQ5BRX and B07FZ8S74R succeed; B08N5WRWNW EMPTY_DATA; PARTIAL, 2/3 successes, exit 1, 3 requests; three formats retain errors |
| Live dataset offline re-export | **PASS**: direct and partial outputs re-export into HTML/CSV/Markdown, preserving source data, original request bytes/hashes, errors, accounting and relative evidence links; clearly offline revalidation |
| Actual Codex CLI live execution | **BLOCKED**: workspace-write host sandbox produced KeyringError before workflow artifacts; the host execution failed and was not retried. No Keychain or sandbox protections were weakened. Offline host checks remain separate PASS |
| Bounded read-only billing reconciliation | **PASS**: six new-key call-detail rows and new-key summary match 6 requests / 230 charged credits; separate from old key's 145 credits |

**Actual data calls: 6 / 20; unused: 14; automatic retries: 0.** Five details and
one search were sent. The direct result contains coffee and Echo Dot products;
this is functional comparison acceptance, not a claim they are competing
products. Both remote `$` currencies remain unresolved, prices unknown for
comparison, with original numeric prices retained as evidence.

| Phase, UTC 2026-10-26 | ASIN/query | Actual CLI outcome | Visible charged credits |
| --- | --- | --- | --- |
| Direct, 10:02:03 | B072MQ5BRX | SUCCESS | 45 |
| Direct, 10:02:04 | B07FZ8S74R | SUCCESS | 90 |
| Search, 10:05:00 | wireless mouse | BUSINESS_13007, no candidates | `—` in call detail; no additional numeric debit in matched key summary |
| Partial, 10:06:08 | B072MQ5BRX | SUCCESS | 45 |
| Partial, 10:06:09 | B07FZ8S74R | SUCCESS | 45 |
| Partial, 10:06:10 | B08N5WRWNW | EMPTY_DATA | 5 |

The five numeric detail charges total **230 credits**, matching the new key's
six-call summary. The empty-data debit is real and was not refunded. Do not
translate the search detail's dash into an independently certified zero, or use
response `cost` as credits. API usage labels all six admitted requests SUCCESS;
that label does not override the saved CLI business failure or empty result.
Matching uses the isolated new key, UTC intervals and routes; private billing
request/diagnostic IDs are retained. Detail payload trace IDs were null, and
the search provider trace ID is not asserted equal to the billing diagnostic ID.
Full distributed tracing and refund/server attribution remain separate gates.

Earlier account call-table snapshots had no new rows. A fresh page and current
Last 7 days query subsequently exposed all six; those initial snapshots remain
unaltered, and their temporary billing BLOCKED status is superseded by this
bounded reconciliation. The account balance also changed with concurrent work;
its delta was never used as this run's expense.

Installed commands were driven by natural-language prompts in actual Claude
Code, with the CLI pinned and no MCP data calls. Each phase saved a dry-run and
one execution: direct `--asins B072MQ5BRX,B07FZ8S74R --max-calls 2`; search
`--keyword "wireless mouse" --max-calls 3`; partial
`--asins B072MQ5BRX,B07FZ8S74R,B08N5WRWNW --max-calls 3`. Executions used
`--market amazon.com --auth-mode browser-account --execute --allow-paid --format all`.
Exact commands, UTC times and exits are in the private transcripts.

Private evidence: `dist/macos-20261026/live/`, including original host failure,
live bundles, offline re-exports, call-table/key-summary text, `live-summary.json`
and hashes. External `live-codex/` and `live-claude/` directories under the
recorded acceptance root are retained for pending gates. The persistent approved
test connection remains in Keychain and can be revoked in API Access. No key
value was exported into the environment or a file, no Windows credentials were
copied, and no refund/database write/deployment/publication was performed.

**Disposition remains partial acceptance.** Do not spend the remaining allowance
on automatic retries, new keywords or extra ASINs. Successful live search/resume,
supported Codex live credential access, positive real env-mode isolation, refund/
full server attribution and downstream release gates remain unaccepted.

### Final local dev11 correction and offline verification

Claude's partial-case offline re-export found another preflight defect:
`report compare --dry-run` returned PLAN_READY for a missing output parent,
while export failed. The existing output-preservation regression was extended
and failed before the fix. Dev11 checks the parent directory and output/evidence
collisions before either dry-run or export, without creating directories or
overwriting files. Repeated export after explicitly creating a parent is labeled
an **offline rerun**, never a new live call. Original host/export failures remain.

Final wheel: **`dist/dev11/nexscope_cli-0.1.2.dev11-py3-none-any.whl`**, SHA-256
**`5c94b388da7f691841aef346195806887fae9f1a6148f62aed130f6c1f2afa5c`**.
Its packaged bytes match the current local source/resources. Source HEAD is
unchanged; this remains an uncommitted local candidate. Version pins and current
adapter hashes match dev11; historical snapshots are unchanged.

**PASS**: source 31 regressions; actual dev11 installed wheel 31 regressions on
each Python 3.11.15/3.12.13; offline/loopback cases and resource checks; 3.12
hash-pinned dependency/legacy checks plus real macOS Keychain dev10↔dev11
write/read/rollback/uninstall retention/cleanup; 3.11 version/report rollback.
The separate external-environment verifier regression also passes. Commands:

```sh
python scripts/check_resources.py
python scripts/verify_wheel.py dist/dev11/nexscope_cli-0.1.2.dev11-py3-none-any.whl --previous-wheel dist/dev10/nexscope_cli-0.1.2.dev10-py3-none-any.whl --with-dependencies --with-os-keyring
python scripts/test_verify_wheel.py dist/dev11/nexscope_cli-0.1.2.dev11-py3-none-any.whl
```

The 3.11 verifier again omitted dependency/OS-keyring flags. Installed dev11
re-exported both original live dev10 datasets into all three formats offline,
preserving products/errors/accounting and every original request byte. Missing
parent dry-runs now exit 1 without creating outputs. **No dev11 live request was
sent**; live host outcomes above belong to the exact dev10 wheel, not dev11.
`live/dev11-offline-revalidation.json` records this distinction.

Additional Claude live-stage model usage reported USD 0.7058736 (direct),
0.2560884 (keyword) and 0.695398 (partial). These provider-reported list-price
figures are not independently reconciled payments and are separate from the
230 Nexscope credits. All raw live/host/export failures, final transcripts,
source diff and SHA-256 index remain in the ignored evidence directory.

## Fresh Codex session retest and permission-profile correction

The user requested a new session after suspecting a changed conversation key,
then explicitly narrowed further work to **Codex only**. No old Codex session
was resumed. The original `KeyringError` records remain unchanged.

**PASS / test-setup correction:** earlier child Codex runs had been launched
with an extra `--sandbox workspace-write` override. The user's existing local
configuration was already `sandbox_mode = "danger-full-access"`. A local
diagnostic reproduced `keyring.backends.macOS` → `KeyringError` → native
`Error(-50)` under the extra sandbox; Codex's denial capture reported blocked
`mach-lookup com.apple.securityd.xpc` and `com.apple.SecurityServer`. The same
credential read succeeded in the current host. This identifies an added test
restriction rather than an expired Nexscope connection. An initial diagnostic
script mistakenly called `client.store.load` and raised AttributeError; that
diagnostic failure was retained, corrected to `client.load`, and is not treated
as a CLI defect.

A fresh `codex exec --ephemeral --skip-git-repo-check --json` run, **without a
sandbox override**, inherited the user's existing permissions. No global config,
Keychain protection or OS security setting was changed; no new key was created,
and no credential was exported. Installed CLI was dev11, with the same recorded
wheel hash and unchanged local source HEAD.

| Fresh configured Codex gate | Outcome |
| --- | --- |
| Normal `account` | **PASS**, existing approved Mac account connected |
| Direct B072MQ5BRX/B07FZ8S74R | **PASS**, COMPLETE, 2 successes, exit 0, 2 requests |
| Single `wireless mouse` search | **FAIL**, BUSINESS_13007, exit 1, 1 request, no candidates |
| Real keyword `--resume` | **BLOCKED**, no completed candidates; not a Codex conversation-resume operation |
| Fixed three-ASIN partial case | **PASS**, 2 successes + B08N5WRWNW EMPTY_DATA, PARTIAL, exit 1, 3 requests |
| All reports and offline re-export | **PASS**, direct/partial HTML/CSV/Markdown; manifests and original request bytes preserved |

This closes **Codex live account/direct/partial acceptance for the user's current
configured profile**, not Keychain access under workspace-write restrictions.
New conversation creation does not resolve the server search error. A bounded
read-only log query for the new search trace returned zero matches; its deeper
provider cause remains unconfirmed. No backend fix or retry was attempted.

Before the user narrowed scope, one extra fresh Claude session re-tested only
the failed keyword (not its already-passing direct/partial cases): 1 request,
BUSINESS_13007, no resume. This extra call is explicitly counted. No further
Claude task was launched after the Codex-only instruction.

**New configured Codex requests: 6, charged 185 credits** (direct 45+45;
partial 45+45+5). The additional search detail rows display `—`; new-key summary
reconciles **13 cumulative Mac calls / 415 charged credits**. This is the earlier
6/230, one extra failed Claude search, plus Codex 6/185. **7 of 20 calls remain
unused; automatic retries 0.** Each repeated search was an explicit user-requested
fresh-session retest, not an automatic retry. The historical Windows key's 145
credits remain separate; account balance deltas and response `cost` are unused.

Private original/fresh-session prompts, exits, diagnostic exceptions/denials,
live dev11 bundles, offline reports and read-only billing rows are under
`dist/macos-20261026/retest/`, indexed by `retest-summary.json` and the parent
SHA-256 index. Original failures are retained. External `retest-codex/`,
`retest-codex-configured/`, and `retest-claude/` directories are retained for
reproducibility. No source/runtime change or publication was needed for this
retest. Remaining gates include live successful search/resume, positive real
env-key isolation, full backend/refund attribution and release authorization.

## First independent version: 0.1.0

At the user's request, the current version is **0.1.0**, replacing the development
version label. Package metadata, module version, dependency locks, paired Skill
requirements/adapter pins, installation instructions and CI wheel path agree.
Historical test versions and original failures above are preserved as recorded.
No runtime behavior or outstanding acceptance status changed with this renumbering.

Built from source baseline `430461255eff13a2119486912682742e68d7582e` plus this
version change: `dist/version-0.1.0/nexscope_cli-0.1.0-py3-none-any.whl`, SHA-256
`5703a4c748d32759903270fb4fbeeb2b84ea5e905e3c7dd29204eb551c8a9a47`.
Resource checks pass. Actual external installed-wheel verification passes on
Python 3.11.15 and 3.12.13: **31 regressions each**, offline/loopback checks and
version-transition/report preservation against the exact prior dev11 wheel.
Python 3.12 additionally passes hash-pinned dependencies/legacy checks and real
Keychain write/read, version-transition/uninstall persistence and cleanup.
This is a version transition, not a claim that 0.1.0 sorts above 0.1.2.dev11.
No new paid call was made; cumulative usage remains 13/20 and 415 credits.
Private transcripts are in ignored `dist/version-0.1.0/`. Source push is
authorized; PyPI, GitHub Release assets/tags and plugin publication are separate.
