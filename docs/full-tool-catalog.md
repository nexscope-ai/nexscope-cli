# Complete tool catalog

The 0.1.1 snapshot contains **565 registered MCP tools**, exported from the
selected server through initialized, paginated `tools/list`. It covers commerce
research, advertising, SEO, patents, creative generation, result retrieval and
workflow helpers. Counts are versioned snapshots, not permanent product totals.

The production public HTTP manifest contained 545 entries and the test legacy
manifest 559 at this export. The modern MCP catalog additionally exposes workflow
helpers. Environment differences and publication timing explain these counts;
never treat a bundled entry as proof of production deployment or live acceptance.

## Discover and validate offline

```sh
nexscope tools list
nexscope tools list --search tiktok
nexscope tools describe nexscope_amazon_search
nexscope tools call nexscope_amazon_search --input search.json --dry-run
```

`search.json` can contain `{"keyword":"desk lamp"}`. Examples are illustrative;
read the exact tool schema before using live data. Discovery and dry-run commands
use bundled resources and do not read credentials or connect to a server. Input
validation supports JSON Schema composition, required groups and nested values.
External schema references are refused. A compatibility adapter converts only
numeric schema bounds affected by the Java Long serializer; identifiers, enums
and input values are never converted.

## Select an account and make one reviewed call

Use the existing browser connection or explicitly select `env-api-key` with
`NEXSCOPE_API_KEY` and `NEXSCOPE_PROXY_BASE`. Do not place keys in command arguments.
`--api-base` is a global browser-origin option before `tools`; omit it in env mode.

```sh
nexscope tools list --live
nexscope tools call nexscope_amazon_search --input search.json --execute --allow-paid --allow-write --out search-result
nexscope tools call nexscope_amazon_search --auth-mode env-api-key --input search.json --execute --allow-paid --allow-write --out key-search-result
```

Execute only after authorizing the real request and effects. The server does not
declare most paid tools read-only, so those tools also require `--allow-write`.
Inspect `annotations` and the operation's own preview/confirmation protocol;
this flag never synthesizes a preview, confirmation token or purchasing approval.

Before execution, the CLI reads the selected server's complete catalog again,
checks availability and validates the live input schema. It invokes exactly one
tool, with no retry, implicit page expansion or result cache. Generic tool cache
semantics are intentionally unspecified; the separately verified Amazon comparison
workflow retains its existing isolated session-success cache and request budget.

The new output directory contains the plan, redacted input, complete redacted
tool response, result and evidence manifest. Standard secret fields and the active
API key are removed from both structured results and duplicated JSON text. A tool
response has status `RESULT_READY`; this does not certify that an asynchronous job or host handoff has finished;
inspect its actual status and use the originating result-retrieval operation.
This adapter does not advertise client-side sampling, elicitation or host execution.
Such a server request returns `INTERACTION_REQUIRED`, rather than inventing an action.

## Refresh a snapshot explicitly

```sh
nexscope tools refresh --out current-tools.json
nexscope tools list --catalog current-tools.json
nexscope tools describe nexscope_amazon_search --catalog current-tools.json
```

Refresh performs metadata discovery only and requires the selected connection.
It writes a new file and cannot replace an existing snapshot. Runtime refresh
does not modify the installed package. Upstream schema changes need review;
catalog hashes detect corruption, not the identity of a party able to rewrite
the entire catalog. Only the selected, origin-bound server receives authentication.

## Verification scope

`tools describe` includes the versioned `api-contract.json` binding: exact MCP
name, schema hash, public endpoint and Skill identifier where the public docs
declare one. The two packaged comparison adapters additionally map their script
to the original research route. Missing public bindings remain unknown; the CLI
never guesses a REST path or claims to bundle every proprietary Skill instruction.

All 565 input schemas are checked, and all names/arguments are exercised through
the injected MCP transport. JSON/SSE framing, pagination, redirects, scope gates,
business errors, redaction and uncertain-result handling have regressions.
These checks are not 565 live billable acceptance tests. The previously recorded
real search `13007`, successful-search continuation and independent billing gates
remain explicitly unaccepted until verified separately.
