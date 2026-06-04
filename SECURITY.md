# Security Policy

## Supported versions

This project is pre-1.0. Security fixes are applied to the latest released version on
the `main` branch.

## Reporting a vulnerability

Please **do not** open a public issue for security vulnerabilities.

Report them privately through GitHub's
[private vulnerability reporting](https://github.com/SeenkaMedia/django-agent/security/advisories/new),
or by email to **diegolis@seenka.com**.

Include a description of the issue, the affected version, and steps to reproduce.
We will acknowledge your report as soon as possible and keep you updated on the fix.

## Scope notes

django-agent can modify your application's data, so it is designed around guardrails:
Django permission checks per operation, mandatory user confirmation before any write,
and an audit log. The optional source-code access tools are read-only, sandboxed to a
configured root, block path traversal, and redact lines that look like secrets — and
are disabled by default.

If you find a way to bypass any of these guardrails (e.g. perform a write without
confirmation, act beyond the user's permissions, read files outside the configured
root, or surface secret values), please report it as described above.
