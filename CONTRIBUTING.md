# Contributing to django-agent

Thanks for your interest in improving django-agent! Contributions of all kinds are
welcome — bug reports, documentation, and code.

## Reporting bugs and requesting features

Please use the [issue tracker](https://github.com/SeenkaMedia/django-agent/issues).
For bugs, include the Django and Python versions, what you expected, what happened,
and a minimal way to reproduce it.

## Development setup

```bash
git clone https://github.com/SeenkaMedia/django-agent.git
cd django-agent
python -m venv .venv && source .venv/bin/activate
pip install -e .
```

Run the test suite:

```bash
python runtests.py            # fast, offline (deterministic)
python runtests.py --live     # also runs tests against real Gemini
```

The `--live` tests require `GOOGLE_APPLICATION_CREDENTIALS` and `AGENT_VERTEX_PROJECT`
to be set; they are skipped otherwise. CI runs only the fast suite.

## Pull requests

1. Fork the repo and create a topic branch (`feat/...`, `fix/...`, `docs/...`).
2. Keep changes focused and the diff small.
3. Add or update tests for behavior changes; the fast suite must pass.
4. Match the existing style: short, clearly named functions, minimal comments, and no
   unnecessary logging.
5. Update `CHANGELOG.md` under `[Unreleased]`.
6. Open the PR with a clear description of the change and its motivation.

## Source files

New Python files should carry the standard header:

```python
# Copyright 2026 Seenka
# SPDX-License-Identifier: Apache-2.0
```

## License of contributions

By contributing, you agree that your contributions are licensed under the project's
[Apache-2.0 license](LICENSE), and that the [NOTICE](NOTICE) attribution to Seenka as
the original author is preserved.
