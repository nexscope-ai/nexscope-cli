# Upgrade, compatibility and rollback

Install an exact reviewed version in a dedicated Python 3.11+ environment:

```sh
python -m pip install --index-url https://pypi.org/simple --upgrade nexscope-cli==0.1.2
nexscope --version
nexscope doctor --offline
```

The command remains `nexscope` and the module remains `nexscope_cli`. Existing
`get-skills`, `auth`, `account`, `run`, `export`, `data`, `workflow` and `report`
entry points remain. The complete server tool catalog is available through
`tools list/describe/call/refresh`; the two bundled legacy Skill adapters are
counted separately from this catalog.

Browser credentials remain in the same origin-specific OS store. Env mode reads
only the original `NEXSCOPE_API_KEY` and `NEXSCOPE_PROXY_BASE`; it neither initializes
keyring nor logs in. Switching modes is explicit, and failure never switches
accounts. Report directories are user data and are never installer state.

Bundled adapters require exactly `nexscope-cli==0.1.2`. Upgrade an independently
distributed Skill only together with its matching reviewed core dependency.
This CLI release does not replace previously published standalone Skills or
plugins. Their current distributions continue to use their own pinned resources.

Roll back into the same isolated environment with:

```sh
python -m pip install --index-url https://pypi.org/simple --force-reinstall nexscope-cli==0.1.0
nexscope --version
```

Restore any separately upgraded Skill resources to their reviewed 0.1.0 pins.
The old version does not have the full `tools` command. Uninstall and rollback
leave reports, unrelated plugin credentials and environment keys intact. Use a
fresh output name when repeating an offline example. The 0.1.0 release remains
available for this compatibility cycle; a support cutoff must be announced by
the maintainers rather than inferred from a version number.
