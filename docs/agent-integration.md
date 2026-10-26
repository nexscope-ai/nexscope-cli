# Agent integration and complete comparison tasks

Existing entry points discover `nexscope get-skills core`. Its legacy `skills`
mapping stays compatible and separately reports `apiTools` and `workflows`.
Read `nexscope get-skills product-comparison` to obtain the bundled task guide
and current pilot contract. Both Codex and Claude adapters consume that same
installed guide; task rules remain in `nexscope_cli.workflows.compare`.

The guide handles direct ASINs, a saved keyword-candidate continuation, partial
completion and user CSV/JSON. The host reuses existing account and request
authorization and asks only for missing or expanded scope. It returns actual
report/evidence links rather than a shell command for the user to assemble.

The old `get-skills <name>`, `run <name> -- <legacy args>` and independently
invoked env-key adapters retain their original parameters and output semantics.
The complete API catalog is a separate contract inventory, not a claim that
hundreds of business Skills have been copied or relicensed into this package.

MCP workflow helpers that require interactive host execution remain subject to
the host's exact tool/account selection and one-use server claim protocol.
The terminal adapter does not impersonate an enabled host tool or silently
execute arbitrary instructions returned by a server.

Update an already published plugin or standalone Skill through its own reviewed
distribution lifecycle and exact core pin. This release provides the shared
guide and runtime; it does not silently replace the user's installed plugins.
