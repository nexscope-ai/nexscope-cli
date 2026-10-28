# Contributing

Open an issue with a reproducible command, exact version, OS/Python version,
expected outcome and a small fictional input. Remove credentials, account IDs,
private responses and billing records. Do not run paid APIs for a contribution
without a separately approved request/effect budget.

Use Python 3.11+. Install the reviewed dependency profile and run:

```sh
python -m pip install --require-hashes -r cli/nexscope_cli/dependencies.lock
python -m pip install --no-deps .
python -m unittest discover -s tests -v
python scripts/check_resources.py
python -m build
python -m twine check dist/*
python scripts/verify_wheel.py dist/nexscope_cli-0.1.2-py3-none-any.whl --with-dependencies
```

The tests use fictional data and injected/local peers. Build tools are development
dependencies and do not belong in the application lock. Changes to schemas or
catalog snapshots must include their source, timestamp, digest and coverage diff.
Do not hand-edit a generated catalog to conceal a server compatibility problem.
Keep existing command output compatibility and add a failing regression for bugs.

Nexscope maintains this repository. Use the repository Issues for support;
no private security email address or response-time SLA is asserted here.
