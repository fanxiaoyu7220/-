# Changelog

All notable changes to ACAN Studio are documented here. The project follows a
lightweight versioning scheme: patch releases fix regressions, minor releases
add creator-facing capabilities, and major releases may change workflows.

## [Unreleased] — 1.2.0 development

### Added

- Dependency-light `acan_studio.core` modules for URL and content detection,
  media formatting, SRT conversion, download command construction, and failure
  suggestions.
- A first automated core test suite and GitHub Actions workflow.
- `CONTRIBUTING.md`, issue templates, a pull request template, and
  `ROADMAP.md`.

### Changed

- The desktop application now delegates pure media and downloader logic to
  the reusable core modules while keeping the existing GUI workflow.
- Project version is centralized in `VERSION` and packaging scripts default to
  1.2.0.

### Fixed

- Douyin and Weibo download attempts no longer read Chrome cookies unless a
  cookie source is explicitly enabled in Settings.
- Pasted URLs have surrounding share-text punctuation removed.
- SRT timestamps correctly carry rounded milliseconds into the next second.

## [1.1.8] — 2026-08-29

- Improved YouTube JavaScript challenge support with bundled Deno and EJS
  components in the compatibility build.
- Added resilient YouTube transport fallbacks and Apple Silicon/Intel macOS
  compatibility packaging.

[Unreleased]: https://github.com/fanxiaoyu7220/-/compare/v1.1.8...HEAD
[1.1.8]: https://github.com/fanxiaoyu7220/-/releases/tag/v1.1.8
