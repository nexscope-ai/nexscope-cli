# macOS acceptance handoff

Date: 2026-10-26. Current development version: `0.1.2.dev9`.
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

| Area | Evidence and limits |
| --- | --- |
| Windows Python 3.12.14 | 30 installed-wheel regressions, offline reports/plans, loopback dual-auth, compatibility adapters and browser runner |
| Ubuntu WSL2 Python 3.12.3 | The same 30 installed-wheel cases; source imports excluded; native macOS is still a separate check |
| Windows credential store | Real OS-store write/read, dev8↔dev9 persistence, uninstall/reinstall persistence and cleanup using an isolated synthetic entry |
| Windows/WSL upgrade and rollback | dev8↔dev9 executable versions and preservation of user reports |
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
