# Nexscope CLI

Create product comparison reports from your own CSV or JSON, entirely offline.
No account, API key, keyring, LLM or upload is needed. HTML, CSV and Markdown
reports include the exact input, validated rows and evidence hashes.

This is the independent CLI repository. Version **0.1.2.dev9** is a development
candidate, not a claim of production, billing or cross-platform acceptance.
The published Codex plugin and independent Skills are separate distributions.

## Install and try your own data

Python 3.11 or newer is required. Build the wheel from this repository, or obtain
the exact reviewed wheel and its SHA-256 from a release of this repository.
Do not install an unverified package just because it has the same name.

From source on macOS or Linux:

```sh
git clone https://github.com/nexscope-ai/nexscope-cli.git
cd nexscope-cli
python3 -m venv .venv
. .venv/bin/activate
python -m pip wheel --no-deps --wheel-dir dist .
python -m pip install --no-index --no-deps dist/nexscope_cli-0.1.2.dev9-py3-none-any.whl
```

On Windows PowerShell, create the environment with `py -3 -m venv .venv` and use
`.venv\Scripts\python.exe` for the Python commands; activation is optional.
There is no need to change PowerShell's execution policy.

If you already have the reviewed wheel, install it with:

```sh
python -m pip install --no-index --no-deps /absolute/path/nexscope_cli-0.1.2.dev9-py3-none-any.whl
nexscope doctor --offline
nexscope report template --format csv --out products.csv
nexscope report describe --schema
nexscope report demo --format json --out sample.json
nexscope report compare --input sample.json --format html --out comparison.html
nexscope report compare --input sample.json --format csv --out comparison.csv
nexscope report compare --input sample.json --format markdown --out comparison.md
```

Use fresh output names. Reports never overwrite files or silently fall back to
another directory. Keep each report with its sibling `.evidence` directory.
The samples are fictional. `nexscope demo product-comparison --out demo-output`
also exercises the complete three-product workflow without credentials or network.

`product_id` and `title` are required. A price requires an explicit currency;
a rating requires its explicit positive scale. Missing values stay unknown.
Identifiers must be strings and unique within a marketplace. Additional input
columns are retained as metadata. There is no inferred sales, profit, currency
conversion or ranking across different markets, currencies or rating scales.
Remote currency symbols such as `$` are ambiguous. The CLI keeps the product and
records `unresolvedCurrency`/`unresolvedPrice` alongside its raw evidence, while
leaving comparable currency and price unknown. It never infers USD from a symbol
or marketplace. Version `0.1.2.dev9` fixes the rejection of these valid products
observed during real-service testing of `dev8`; successful live comparison and
the keyword continuation remain separate acceptance gates.

Raw UTF-8 CSV/JSON inputs are limited to 10 MiB and 10,000 products. Local imports
have no three-product limit. CSV errors use logical record numbers including the
header; JSON errors use one-based array positions. Invalid rows are explained,
never silently dropped. Versioned datasets allow 32 MiB because normalization
adds metadata; evidence bundles allow 64 MiB. See `report describe` for fields.

## Product comparison workflows

Remote planning is free of network and credential access:

```sh
nexscope workflow compare --asins B000000001,B000000002,B000000003 --dry-run
nexscope workflow compare --keyword lamp --dry-run
```

The bounded workflow accepts two or three distinct ASINs, or one search page
followed by explicit selection of two or three candidates. Use `--mock complete`
for fictional execution. `--mock partial` demonstrates partial completion.

```sh
nexscope workflow compare --keyword lamp --execute --mock complete --max-calls 4 --out candidates
nexscope workflow compare --resume candidates --select-asins B000000001,B000000002 --dry-run --mock complete
nexscope workflow compare --resume candidates --select-asins B000000001,B000000002 --execute --mock complete --format all --out finished
nexscope report compare --input finished/dataset.json --format markdown --out another.md
```

`--resume` imports the original search evidence, sends only the selected detail
requests and carries forward the original budget. One search plus two details
is three total requests. The original marketplace, source type, auth mode and
origin must agree; a resumed budget cannot increase. Omitted marketplace, auth
mode and max-calls inherit the checkpoint. `--keyword --select-asins` retains its
existing meaning of a new search plus details; use `--resume` after selection
to avoid paying for another search.

Only completed `CANDIDATES_READY` outputs with a valid manifest may be resumed.
Failed/incomplete outputs are never automatically replayed. A deliberate new
command using the same candidates starts another branch of work; there is no
server-side spending lock. `max-calls` is a request limit, not a monetary cap.
Ambiguous failures consume a call. No automatic retries, pagination or ASIN
expansion occur. Exit code 1 marks failures, partial or insufficient results;
inspect saved results and evidence before deciding what to do next.

Historical search imports are explicit user-selected evidence, not cache hits,
fresh live queries, proof of account identity or server-signed records. They are
never inserted into a credential context's cache. New requests use only the
currently selected credentials. Each finished directory contains the original
search plan/response, current plan, all details and hashes, with relative links.

`report compare` can read this version's `dataset.json` without refreshing data.
It checks the complete bundle, input digest, request contracts, product mappings,
selection and accounting, preserving `sourceType`, retrieval times, errors and
the original `inputName/inputSha256`. `report-input.json` separately identifies
the exact input selected for re-export. These hashes detect inconsistent edits
or corruption; they do not authenticate an author who can rewrite the whole
bundle. Do not treat third-party bundles as verified live market data.
Older preview datasets without manifests must be regenerated; this version does
not silently relabel them as user imports.

## Connect

Online browser/plugin use needs the existing hash-pinned dependency profile:
Set `APPROVED_API_ORIGIN` to the approved service origin. For paid data, set
`ASIN_1` and `ASIN_2` to verified real identifiers and explicitly approve the
request budget. The fictional identifiers used by mock examples are not live
test inputs; empty responses can still incur charges.

```sh
python -m pip install --require-hashes -r /absolute/checkout/cli/nexscope_cli/dependencies.lock
nexscope --api-base "$APPROVED_API_ORIGIN" auth login --source-client python-cli --source-channel github
# Complete the returned connection URL in your browser, then:
nexscope --api-base "$APPROVED_API_ORIGIN" auth poll
nexscope --api-base "$APPROVED_API_ORIGIN" account
nexscope --api-base "$APPROVED_API_ORIGIN" workflow compare --asins "$ASIN_1,$ASIN_2" --max-calls 2 --execute --allow-paid --out live-comparison
```

Browser credentials use the OS credential store. Supported backends are Windows
Credential Manager, macOS Keychain, Secret Service and KWallet. The CLI does not
read an environment key in `browser-account` mode or fall back when login fails.
`--api-base` is a global option before the command when a different approved
browser API origin is needed. Authenticated redirects are refused.

Independent Skills and explicit `--auth-mode env-api-key` use only
`NEXSCOPE_API_KEY` and `NEXSCOPE_PROXY_BASE`, privately configured in your shell.
They require no browser login or keyring. Do not put keys into command history,
documents or Git. Omit `--api-base` in this mode. Credential failure never
switches modes. Cache entries are valid-success-only, memory-only, expire after
300 seconds and are isolated by immutable auth context, origin, capability,
parameters, marketplace and contract. Separate processes never share a cache.

`get-skills`, browser-account `run ... -- <old script arguments>` and `export`
remain available. The bundled standalone scripts require exactly this wheel
version and preserve their JSON argument, `--inline`, `--no-cache`, original
environment configuration and legacy response/exit semantics. They forward a
legacy batch/page once without the bounded workflow's three-ASIN/one-page limits.
Legacy JSON business errors can still exit zero: inspect the response code/error.
Do not replace published Skills with these adapters before installation and live
compatibility acceptance. No dependencies are auto-installed at query time.

Only Amazon search/detail are adapted. Credits are unknown (`null`); response
`cost` is not treated as a credit charge. Real account, balance and billing
acceptance remain separate gates. Reports contain no telemetry or automatic
upload. Review product data before sharing a report or its evidence.

## Development and verification

```sh
python -m pip install --no-deps .
python -m unittest discover -s tests -v
python scripts/check_resources.py
python -m pip wheel --no-deps --wheel-dir dist .
python scripts/verify_wheel.py dist/nexscope_cli-0.1.2.dev9-py3-none-any.whl
```

The standard-library test suite runs with no service credentials. The wheel
verification creates a fresh environment outside the checkout, clears source
path injection, installs the actual wheel without dependencies, blocks network
and keyring for offline checks, then runs the installed test suite and CLI cases.
It also tests old adapters against a fictional loopback server. Loopback fixtures
do not constitute live Nexscope acceptance. CI runs the same checks on Windows,
macOS and Linux with Python 3.11 and 3.12; a configured matrix is not a passing run.

Use a separate environment for upgrades and rollback. Install the prior exact
verified wheel, and restore any paired Skill directory to its matching version.
The verification script accepts `--previous-wheel /path/to/prior.whl` to exercise
upgrade/rollback while checking that user reports and test credential sentinels
survive. No public package, tag, release or plugin upload is made by these scripts.

On a machine with a real supported OS credential store, add `--with-os-keyring`
alongside `--with-dependencies` to test an isolated fictional credential. The
verifier checks write/read, upgrade/rollback and uninstall persistence, then
deletes only its own uniquely named entry. It does not log in to a service or
modify an existing account credential. A missing desktop credential store is
reported as a prerequisite failure; it never falls back to plaintext storage.

For an Ubuntu host without `ensurepip`, use `--pip-wheel /path/to/reviewed/pip.whl`
to bootstrap pip inside the fresh venv from an explicit trusted wheel, such as
Python's bundled ensurepip wheel. This does not install into the system Python.
Windows and Ubuntu WSL2 installation acceptance has been run locally; WSL2 does
not certify macOS or a Linux desktop credential store.

When intentionally changing a bundled adapter, run
`python scripts/check_resources.py --update` and review the catalog diff. This
updates current-file hashes only; historical source snapshot hashes are retained.
Keep CLI behavior here and have consumers pin its version; do not maintain a
second CLI copy in the published plugin.

See [ACCEPTANCE.md](ACCEPTANCE.md) for verified scope and outstanding release gates,
and [the macOS handoff](docs/HANDOFF-MACOS.md) for the remaining acceptance work.
Report reproducible problems, without keys or private reports, in
[GitHub Issues](https://github.com/nexscope-ai/nexscope-cli/issues). Nexscope is the
maintainer; named pilot/release ownership still needs assignment before release.

Apache-2.0. Initial source: plugin commit
`814f28016af6b3ff57ef12093a6bb133c4fb20b9`. Original Skill provenance remains in
the catalog. See `NOTICE`, `ASSET-NOTICES.md` and `THIRD-PARTY-NOTICES.md`.
