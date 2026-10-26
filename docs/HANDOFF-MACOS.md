# macOS acceptance handoff

Date: 2026-10-26. Current version: `0.1.0` (first independent version).
The original dev9 handoff below remains historical context; see the completion
record at the end for actual Mac results and remaining gates.
The user has authorized source publication and selected `0.1.0` as the first version.
Historical local/uncommitted descriptions below refer to the recorded test
phases. PyPI, GitHub Releases and downstream plugin publication remain separate.
Repository: <https://github.com/nexscope-ai/nexscope-cli>.

## Objective and boundaries

Continue acceptance of the standalone CLI on macOS. Read `README.md` and
`ACCEPTANCE.md` before running checks. The published plugin and independently
distributed Skills are separate consumers; do not overwrite or release them
as part of these tests. The CLI source is maintained here.

No real credentials, account snapshots, private infrastructure configuration,
paid-run response bundles or local verification environments are in Git. The
original operator retains those artifacts in an ignored local directory. Do not
copy Windows Credential Manager entries to the Mac. Connect a suitable test
account through the normal browser flow so that credentials enter macOS Keychain.
Use the approved non-production API origin supplied privately by the operator.

The previous real-data authorization was **four calls and is exhausted**. Obtain
a fresh explicit request budget before further paid calls. A request count is
not a monetary cap. Do not automatically retry ambiguous calls, switch auth
contexts after failure, or test production by default. Refunds, backend writes,
deployments, package releases and plugin uploads need their own authorized scope.

## What is already verified

Source publication is complete: the repository is public and `main` contains
the implementation. The initial runtime commit is
`d5ed885ef87a248f82827a8c6252760e340d7a7a`. Its
[installed-wheel CI run](https://github.com/nexscope-ai/nexscope-cli/actions/runs/40296830306)
passed all six Windows/Ubuntu/macOS × Python 3.11/3.12 jobs. Later documentation
commits retain that runtime; inspect the actual checks on the commit you use.
The hosted Mac jobs do not establish local Keychain persistence or live login.

| Area | Evidence and limits |
| --- | --- |
| Windows Python 3.12.14 | 30 installed-wheel regressions, offline reports/plans, loopback dual-auth, compatibility adapters and browser runner |
| Ubuntu WSL2 Python 3.12.3 | The same 30 installed-wheel cases; source imports excluded; native macOS is still a separate check |
| Windows credential store | Real OS-store write/read, dev8↔dev9 persistence, uninstall/reinstall persistence and cleanup using an isolated synthetic entry |
| Windows/WSL upgrade and rollback | dev8↔dev9 executable versions and preservation of user reports |
| Hosted CI from the immutable initial commit | All six installed-wheel jobs passed on Windows, Ubuntu and macOS with Python 3.11/3.12; no paid queries were made |
| Real existing-account browser connection | Approved test user matched the CLI account; credentials stayed in the OS store |
| Live dev9 detail | `B072MQ5BRX`, Amazon US: COMPLETE / SUCCESS, exit 0, one product |
| Actual billing sample | Four data calls, no CLI retries; three ledger debits total 145 credits (90 + 10 + 45); failed search cost 0 |
| Failure evidence and offline reports | Original failed runs retained unchanged, including remote provenance and errors; offline revalidation is labeled separately |

The old dev8 wheel SHA-256 was
`653e86eb614ee649fddd58b10b36631dc9ce2c949af534c6b3371fc9b18b1024`.
The dev9 wheel tested on Windows/WSL and in the live detail call had SHA-256
`eaf560de2d949444b266308f9058acd679cfc622027e66f8ec616fb15f68a5e5`.
Documentation and publication metadata may change subsequent wheel bytes. Record
the commit and hash of the actual Mac build; do not assume it has either hash.
These are historical artifacts, not published release claims.

## Build and run the macOS checks

Use Python 3.11 and 3.12 where available; record macOS version and arm64/x86_64.
Do not claim architectures or Python versions that were not executed. A CI job
passing on a hosted Mac does not certify the local user's Keychain or browser.

```sh
git clone https://github.com/nexscope-ai/nexscope-cli.git
cd nexscope-cli
git rev-parse HEAD
python3 -m venv .venv
. .venv/bin/activate
python -m pip wheel --no-deps --wheel-dir dist .
python scripts/check_resources.py
python scripts/verify_wheel.py dist/nexscope_cli-0.1.2.dev9-py3-none-any.whl --with-dependencies --with-os-keyring
shasum -a 256 dist/nexscope_cli-0.1.2.dev9-py3-none-any.whl
```

The verifier creates another clean venv outside the checkout, installs the actual
wheel, removes Python source-path injection, runs the installed test suite and
CLI scenarios, and uses a fictional loopback HTTP service. These commands do not
query Nexscope's live data. Online dependency installation is hash-pinned.

`--with-os-keyring` writes a random value under a unique fictional `.invalid`
service name, checks persistence through uninstall/reinstall and deletes its
own entry. It must report the real `keyring.backends.macOS` backend. If macOS
requires user interaction, allow the user to handle the OS prompt; do not weaken
Keychain protections or substitute a plaintext backend to make the test pass.

For actual upgrade/rollback coverage, supply a separate reviewed prior wheel:

```sh
python scripts/verify_wheel.py dist/nexscope_cli-0.1.2.dev9-py3-none-any.whl --previous-wheel /absolute/path/to/reviewed-prior.whl --with-dependencies --with-os-keyring
```

Use the historical dev8 artifact only if the operator transfers it and its hash
matches the recorded value. Otherwise select a later reviewed prior commit with
a different version. Do not fabricate a rollback wheel by editing version text.

Check paths containing spaces and non-ASCII characters, installed command
resolution, resource integrity, failure exit codes and output preservation.
The verifier already exercises these paths; retain its transcript and summary.

## Real-service work still required

First arrange the test origin, test account, explicit maximum request count and
how billing will be verified. Do not carry forward the exhausted Windows budget.
Use an installed wheel outside the source checkout for the real tests as well.

1. **macOS browser connection:** install the pinned online dependency profile,
   run `auth login`, review the approved origin and account in the browser,
   confirm the connection at the appropriate authorization step, then run
   `auth poll` and `account`. Check that browser-account ignores an unrelated
   environment key, and that env-api-key never reads Keychain or falls back to
   browser login. Do not disclose either credential.
2. **Direct live comparison:** use two or three verified real ASINs from the
   same market. Record the plan, requested/sent calls, original responses,
   status/exit code and all three report formats. A successful single detail
   does not establish a successful comparison.
3. **Keyword continuation:** one authorized search page must produce candidates.
   Select two or three identifiers from that saved evidence and execute
   `workflow compare --resume <candidates> --select-asins ...` into a new output
   directory. Verify that no second search is sent and accounting includes the
   original search. Check that the complete folder can be moved and re-exported
   offline with working relative evidence links.
4. **Real partial completion:** obtain an authorized case with at least two
   successful products and one failure. Require PARTIAL, exit 1 and traceable
   errors, rather than COMPLETE. Do not manufacture success by editing evidence.
5. **Billing:** reconcile the exact calls against authoritative ledger records.
   Shared-account balance deltas can include concurrent activity. Keep costs
   unknown in CLI estimates unless a contract supplies them; response `cost` is
   not a credit charge. Empty data may still have been billed. Do not perform
   refunds without separate authorization and an approved test procedure.
6. **Actual hosts:** complete direct-ASIN, keyword-selection and partial-result
   tasks through the intended Codex/Claude integrations. Pin the CLI version;
   isolated command-line tests do not establish natural-language host acceptance.

Get the exact command syntax from `README.md`/`--help`. Browser auth uses the
global `--api-base` option before the command. Env mode uses only privately
configured `NEXSCOPE_API_KEY` and `NEXSCOPE_PROXY_BASE` and rejects `--api-base`.

## Known live observations

- Search `desk lamp` returned business 13007. The provider reported no matching
  results and no candidates, so live keyword/resume acceptance was blocked.
- `B08N5WRWNW` returned an empty product array and was charged 10 credits. It is
  not a reliable positive sample for a new paid test.
- `B072MQ5BRX` returned a product with numeric price `15.27`, currency `$` and no
  explicit rating scale. Dev8 incorrectly rejected the whole product. Dev9 keeps
  the product, preserves unresolved price/currency, and leaves comparable price,
  currency and unscaled rating unknown. The symbol must not be guessed as USD.
- Stock/provider behavior can change. A previously successful ASIN does not
  guarantee a future successful or equally priced request.

## What remains for Windows and Linux

No repeated Windows/WSL offline regression campaign is required without new
changes or failures. Run normal regression checks after any code change.
Remaining successful live comparison, keyword/resume, real partial completion,
refund/attribution and host acceptance can be continued from the Mac.

The WSL host had `keyring.backends.fail`; fail-closed rejection was verified.
Positive Secret Service/KWallet persistence requires an actual supported Linux
desktop session. A Mac Keychain pass does not close that Linux gate. Hosted CI
can cover ordinary Linux and Windows/Python installation combinations, but not
the unavailable desktop credential session.

Backend registration → effective result → payment/refund attribution, named pilot
owners, compatibility support window and downstream published-package acceptance
are still separate release gates. Do not mark R2 fully accepted on the basis of
the local CLI tests alone.

## Handoff completion record

Update `ACCEPTANCE.md` with the exact source commit, artifact hash, platform,
architecture, Python version, command, status and bounded-call usage. Distinguish
PASS, FAIL and BLOCKED. Preserve original failures, identify offline replays,
and keep private evidence outside Git. Do not publish credentials or paid-run
account data in issues, logs, screenshots, commits or CI artifacts.

### Completed on this Mac, 2026-10-26 (Asia/Taipei)

Actual source HEAD: `0252b0ec8a02ecdceb4deb691f3c3d0c12b8ed65`, branch `main`,
initially clean. Local uncommitted changes fix POSIX verifier venv creation and
mock ASIN/detail consistency, with failing-before/passing-after regressions.
The runtime correction is versioned **0.1.2.dev10** locally; there is no dev10
commit or publication. All paired adapter pins/current hashes were updated,
preserving historical source snapshots. No existing plugin was changed.

Platform: **macOS 27.0, build 26A428, arm64**; Python **3.11.15 / 3.12.13**.
Final actual wheel: `dist/dev10/nexscope_cli-0.1.2.dev10-py3-none-any.whl`, SHA-256
`eb36658d08cf523c714444bb82ce5fc3acf16a305248fbcbd688f3c5fc25744e`.
Reviewed rollback wheel: locally rebuilt/tested dev9, SHA-256
`618c18c6c7e134eb992479242d60fa672d9ac99bfd2519b8b3529bc2d7fff02e`.
These are different from the historical Windows wheels above.

| Status | Actual result |
| --- | --- |
| PASS | Dev9 installed-wheel 30 regressions per interpreter; corrected dev10 31 per interpreter, offline/loopback/report/legacy checks, resources and external-venv source isolation |
| PASS | Real `keyring.backends.macOS` write/read, dev9↔dev10 rollback, uninstall/reinstall retention and synthetic-entry cleanup on Python 3.12.13; version/report rollback on both Pythons |
| PASS | Explicit user approval before persistent test CLI Key creation; browser account matches installed CLI; credential remains in Keychain and pending entry cleared; unrelated env key ignored |
| PASS | Browser/env failure paths do not cross modes or fall back; positive modes pass with loopback fixtures. Real second-account env mode remains unaccepted |
| PASS, offline host only | Codex CLI 0.163.0 and Claude Code 2.1.308 actually executed natural-language three-ASIN, keyword/resume and 2-success/1-failure workflows, all reports and offline re-export; no live data implied |
| PASS, read-only prerequisite | Own-account API Access Call Details has UTC/key/path/actual-credit/request/diagnostic fields for later per-call reconciliation; no new Mac-key data rows observed, no balance-delta attribution |
| FAIL → fixed | Original verifier copied-interpreter SIGABRT/dyld failure on both Pythons; original logs retained, POSIX symlink correction passes |
| FAIL → fixed in dev10 | Known fictional ASINs received another fixture's title/price; regression first failed, matched-ASIN selection now passes in installed wheels and both real hosts |
| BLOCKED | 8-request plan approved; credit-budget value, second positive ASIN and single keyword await specification; live comparison/resume/partial/live-host gates remain incomplete |
| BLOCKED / separate | Real positive env-mode account, refunds/server attribution, Linux desktop keyring, published-plugin discovery and release acceptance |

Executed commands:

```sh
python scripts/check_resources.py
python -m pip wheel --no-deps --wheel-dir dist/dev10 .
python scripts/verify_wheel.py dist/dev10/nexscope_cli-0.1.2.dev10-py3-none-any.whl --previous-wheel dist/rebuilt/nexscope_cli-0.1.2.dev9-py3-none-any.whl --with-dependencies --with-os-keyring
python scripts/test_verify_wheel.py dist/dev10/nexscope_cli-0.1.2.dev10-py3-none-any.whl
```

The 3.11 verifier omitted dependency/OS-keyring flags. Auth used only
`https://test-claw-callback.nexscope.ai` and `https://www-test.nexscope.ai`:
`auth login --source-client python-cli --source-channel github`, explicit browser
confirmation, `auth poll`, then `account` with an unrelated env sentinel.
**Data calls 0; automatic data retries 0; CLI auth/account HTTP requests 5.**
No new data debit is attributed; this does not certify the whole ledger. Old
145-credit charges remain historical. Host model usage costs are separate;
see ACCEPTANCE.md for reported, unreconciled amounts.

Private raw failures, transcripts, host outputs, no-key account snapshots and
read-only billing evidence are in `dist/macos-20261026/`, ignored by Git. The
source baseline, wheel/source/script hashes, exact host prompts and results are
indexed in `acceptance-summary.json`. Offline reruns are explicitly separated.
The external installed `live-env` and host directories under
`~/.local/share/nexscope-cli-acceptance/20261026/` are retained for pending work.
No task worktree, branch, commit, push, release or publication was created.

### Post-approval live completion record

The user subsequently authorized **at most 20 data calls, no credit ceiling**,
and delegated fixed sample/keyword selection. This supersedes the earlier
8-call proposal. Samples: `B072MQ5BRX`, `B07FZ8S74R`; historical failure sample
`B08N5WRWNW`; sole keyword **`wireless mouse`**; marketplace `amazon.com`.
The final installed dev10 wheel/hash and source baseline above are unchanged.
No automatic retries, replacement ASINs/keywords or production calls occurred.

| Status | Actual live outcome |
| --- | --- |
| PASS | Actual Claude Code drove a direct two-product comparison: COMPLETE, 2/2 successful, exit 0, 2 requests; HTML/CSV/Markdown and original evidence retained |
| FAIL, upstream | The single keyword request returned business 13007, no candidates, exit 1; exact failed response and manifest retained |
| BLOCKED | Live `--resume` cannot run without a completed candidates checkpoint; search was not repeated or replaced |
| PASS | Actual Claude Code drove a three-product partial case: B072MQ5BRX/B07FZ8S74R successful, B08N5WRWNW EMPTY_DATA; PARTIAL, 2/3 successful, exit 1, 3 requests |
| PASS | Direct and partial datasets re-export offline into all three formats, preserving original request bytes, hashes, remote provenance, errors and accounting |
| PASS, bounded reconciliation | Own-account call detail rows and new-key summary match **6 calls / 230 charged credits**; no whole-account balance-delta attribution |
| BLOCKED | Actual Codex CLI workspace-write sandbox returned KeyringError before workflow artifacts/data requests; no sandbox/Keychain protection was weakened and this command was not retried |

**Used 6 of 20 authorized data calls; 14 unused; automatic retries 0.**
There are five detail calls and one search. Direct details cost **45 + 90**;
partial details cost **45 + 45 + 5**. Search's detail row displays `—`, not a
numeric zero; the new-key summary totals 6 calls and 230 credits, matching the
five numeric detail charges. The failed empty-data sample's **5 credits are a
real charge**. No refund was requested or performed. The prior Windows key's
145 credits remain separate. Response `cost` values are not credit amounts.

Earlier billing snapshots showed only old rows. A newly opened API Access page,
with a refreshed Last 7 days query, subsequently exposed all six Mac-key rows;
original incomplete snapshots are retained. Matched UTC rows are at
10:02:03/04 (direct), 10:05:00 (search), 10:06:08/09/10 (partial), all on
2026-10-26. Private per-row request/diagnostic IDs and key mask are recorded in
`dist/macos-20261026/live/billing-final-call-details.txt`; key-only summary is
`billing-final-key-summary.txt`. This reconciles visible call charges, not a
complete distributed trace, refund flow or independently audited ledger.

Exact host prompts, command/exit transcripts, raw response bundles and offline
re-exports are saved under `dist/macos-20261026/live/` (ignored), indexed by
`live-summary.json` and `SHA256SUMS`. External `live-codex/` (original failed
host attempt) and `live-claude/` (live original bundles) are retained under
`~/.local/share/nexscope-cli-acceptance/20261026/`. All private evidence remains
local. No source commit, publication, deployment or plugin update was made.
The persistent test connection remains in Keychain and can be revoked through
API Access; no key value was exported to a file or the environment.

Remaining acceptance: successful live keyword/resume, Codex live credential
access under supported host permissions, a separately authorized positive real
env-api-key context, full server attribution/refunds, and release ownership.
The unused call allowance is not a reason to retry or switch samples. R2 remains
partially accepted.

### Final installed candidate: dev11

The live data runs above used dev10. An offline-only preflight defect was then
reproduced: missing report parents returned PLAN_READY under `--dry-run` but
failed on export. An existing regression was extended and failed first; the
small correction checks parent/output collisions before dry-run as well.

Final local wheel: `dist/dev11/nexscope_cli-0.1.2.dev11-py3-none-any.whl`, SHA-256
`5c94b388da7f691841aef346195806887fae9f1a6148f62aed130f6c1f2afa5c`.
HEAD is still `0252b0ec8a02ecdceb4deb691f3c3d0c12b8ed65` with uncommitted fixes
and paired dev11 pins. Source/resource byte matching and resource checks pass.

**PASS**: 31 source regressions; 31 installed regressions on both Python
3.11.15 and 3.12.13; real Keychain dev10↔dev11 persistence, uninstall retention
and cleanup on 3.12; version/report rollback on 3.11; verifier regression;
all six direct/partial report re-exports from original live datasets into the
installed dev11 pass **offline**, with original request bytes preserved.
Missing-parent dry-runs now exit 1. Exact commands match the dev10 verifier
commands above with dev11 as current and dev10 as previous wheel.

No new live call was made after this correction: final total remains **6/20,
230 Nexscope credits, no automatic retry, 14 unused**. Do not relabel the dev10
live runs as dev11 live acceptance. The final external `live-env` contains dev11;
`dev11-offline/` preserves offline-only report results. Full commands, hashes and
original failures are indexed in `dist/macos-20261026/live/live-summary.json`.
Model usage costs are recorded separately in ACCEPTANCE.md. Release, refund,
full server attribution and remaining host/search gates remain incomplete.

### Fresh Codex retest: Keychain gate resolved for the configured host

The user requested a new session, then restricted further testing to Codex.
Earlier child runs had an extra `--sandbox workspace-write` override, whereas
the user's existing configuration was `danger-full-access`. A local diagnostic
captured native Keychain `Error(-50)` plus sandbox denials for
`com.apple.securityd.xpc` / `com.apple.SecurityServer`. The same installed CLI
could read the credential in the current host. Original errors and one mistaken
diagnostic AttributeError are retained separately.

Fresh `codex exec --ephemeral --skip-git-repo-check --json`, with **no sandbox
override**, inherited the existing profile; no global/OS/Keychain protections
were changed, no key recreated or exported. Version remains dev11, wheel
SHA-256 `5c94b388da7f691841aef346195806887fae9f1a6148f62aed130f6c1f2afa5c`.

- **PASS:** account connected; direct two-product COMPLETE/exit0/2 requests;
  partial case 2 successes + B08N5WRWNW EMPTY_DATA, PARTIAL/exit1/3 requests;
  all three original reports and six offline re-exports preserve evidence.
- **FAIL:** the single Codex `wireless mouse` search again returned 13007,
  exit1/1 request. A bounded exact-trace log query returned no rows, so the
  deeper provider reason is not certified.
- **BLOCKED:** live CLI `--resume` still lacks a completed candidates checkpoint.
  It reads local search evidence and is distinct from resuming a Codex chat.

This closes Codex live acceptance under the user's configured profile, not
workspace-write Keychain compatibility. Before the Codex-only clarification,
one additional fresh Claude search also failed (1 request); no already-passing
Claude direct/partial case was repeated and no further Claude task was started.

Read-only new-key billing summary now matches **13 total Mac calls / 415
credits**: previous 6/230, the extra Claude search, then Codex 6/185. Codex's
five detail debits are 45+45+45+45+5; search rows show `—`, not a numeric zero.
**7/20 requests remain unused, no automatic retry.** Old Windows 145 credits
are separate. No balance-delta attribution, refund or backend change occurred.

Exact fresh prompts, commands, UTCs, exit codes, raw bundles, OS diagnostic
denials, offline outputs and billing receipts are under ignored
`dist/macos-20261026/retest/`, indexed by `retest-summary.json`. The external
`retest-codex/`, `retest-codex-configured/`, and `retest-claude/` directories are
retained for reproduction. No commit, release, deployment or plugin change was
made. Next work remains successful live search/resume and the other independent
release/refund/env-mode gates, without automatically spending the unused calls.

### Current version: 0.1.0

The user selected **0.1.0** for the first independent version. Current package,
module, locks, paired Skill/adapter pins, README and CI agree. Historical dev
version evidence above remains unchanged; the version change does not close
outstanding live search/resume or other independent acceptance gates.

Wheel: `dist/version-0.1.0/nexscope_cli-0.1.0-py3-none-any.whl`, SHA-256
`5703a4c748d32759903270fb4fbeeb2b84ea5e905e3c7dd29204eb551c8a9a47`.
Source baseline: `430461255eff13a2119486912682742e68d7582e` plus version changes.
**PASS:** resources; actual external installed-wheel 31 regressions on each local
Python 3.11.15/3.12.13; offline/loopback and previous-dev11 version/report retention;
Python 3.12 real Keychain write/read, persistence across version changes and
uninstall/reinstall, and cleanup. The numerical version moves from dev11 to 0.1.0
by explicit user choice; install the reviewed wheel with force-reinstall when
replacing a higher-numbered development build. No new live requests; 13/20 and
415 credits remain the totals. Private logs are ignored in `dist/version-0.1.0/`.
No PyPI/Release/tag/plugin publication is implied by the source push.
