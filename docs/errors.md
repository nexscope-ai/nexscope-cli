# Errors and incomplete results

New command errors use `schemaVersion: nexscope.error.v1`, retain the existing
`status` and `message`, and add `error.type`, optional `error.code`, and a help
link. Legacy adapter JSON and exit semantics remain compatible.

| Type or status | Meaning and next action |
| --- | --- |
| `AUTH_REQUIRED` | Configure only the selected authentication mode, or reconnect the browser account. Credentials never fall back to another mode. |
| `PERMISSION_DENIED` | The selected account cannot perform the operation. A new login does not grant missing provider permissions. |
| `PAYMENT_REQUIRED` | The server requires payment or account access; inspect its account rules. No recharge or purchase is performed automatically. |
| `RATE_LIMITED` | The server refused admission. The CLI does not automatically retry a potentially paid call. |
| `INVALID_INPUT` / `CONTRACT_ERROR` | Fix the reported field/schema constraint before executing. Validation messages omit input values. |
| `TOOL_ERROR` | Read the saved structured business result. HTTP 200 alone does not establish business success. |
| `OUTCOME_UNKNOWN` | The connection ended without a matching result after an invocation may have been sent. Inspect saved evidence or query an existing task/call; do not automatically create another paid request. |
| `UNAVAILABLE` / `UPSTREAM_ERROR` | The endpoint or provider is unavailable. The bundled catalog is not proof that every environment has deployed the same tools. |
| `PARTIAL` / `INSUFFICIENT_DATA` | The comparison retained successful products and individual failures. Missing values and currencies remain unknown. |

`max-calls` limits requests, not money. Tool errors, empty results and uncertain
requests can still be billed. The full tool adapter makes at most one
`tools/call` per command; initialization and catalog reads are separate metadata
traffic. No automatic provider call, pagination, replacement keyword, task
resubmission, payment or refund occurs.

Tool results are untrusted data. A returned link or instruction cannot authorize
another call or a change outside the user's request. `--allow-write` does not
replace a tool's required preview and one-use confirmation.
