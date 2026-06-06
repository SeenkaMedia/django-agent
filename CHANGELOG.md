# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.3] - 2026-06-05

### Fixed

- `query`/`get`/`create`/`update`/`delete` no longer crash with
  `TypeError: Object of type ZoneInfo is not JSON serializable` when a model field
  holds a `dict`/`list` (e.g. a `JSONField` or `ArrayField`) containing nested
  values that are not JSON-native (timezone-aware datetimes, `ZoneInfo`, `Decimal`,
  etc.). `_jsonable` now recurses into dicts and lists instead of returning them
  untouched, so every nested value is normalized before the tool result is persisted.

## [0.1.2] - 2026-06-04

### Changed

- The Conversation admin now renders the conversation as a readable chat transcript
  (user/assistant bubbles, compact tool-call notes) instead of raw inline rows. The
  ActionLog admin gained a readable action summary, a colored result badge, and
  pretty-printed arguments/result.

## [0.1.1] - 2026-06-04

### Added

- Read-only Django admin views for the agent's own models (`Conversation` with its
  `Message` inline, `Message`, and `ActionLog`), so conversations and the audit log
  are browsable from the admin.

## [0.1.0] - 2026-06-04

### Added

- Floating chat widget injected into the Django admin via middleware (no template
  changes required).
- Automatic CRUD over admin-registered models (`describe_models`, `query`, `get`,
  `create`, `update`, `delete`), with field schemas derived from model metadata and
  foreign-key resolution by primary key or natural name.
- Per-operation Django permission checks (`view`/`add`/`change`/`delete`).
- Confirmation card for every write, with a value preview and an old → new diff for
  updates; audit log of every executed write.
- Server-side conversation persistence (one per user) that survives navigation and
  reloads, plus a "new conversation" reset.
- Page-context awareness so the assistant knows which model the user is looking at.
- Optional, read-only, sandboxed source-code access tools (`search_code`, `outline`,
  `read_file`) with a secret denylist and redaction; disabled by default.
- Gemini backend on Vertex AI via Application Default Credentials, including support
  for Gemini 3.x thought signatures.
- Manual test suite (`runtests.py`) with a fast offline path and an opt-in `--live`
  path against real Gemini.

[Unreleased]: https://github.com/SeenkaMedia/django-agent/compare/v0.1.3...HEAD
[0.1.3]: https://github.com/SeenkaMedia/django-agent/compare/v0.1.2...v0.1.3
[0.1.2]: https://github.com/SeenkaMedia/django-agent/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/SeenkaMedia/django-agent/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/SeenkaMedia/django-agent/releases/tag/v0.1.0
