# ACAN Studio roadmap

The roadmap is intentionally staged around a small, reliable creator
workflow. Status is maintained in this file and in the repository's GitHub
Issues; download counts, stars, and adoption claims will only be reported when
they can be verified.

## 1.2.x — maintainer-ready foundation

- [x] Extract dependency-light core helpers without replacing the working GUI.
- [x] Make browser-cookie use explicitly opt-in for all download paths.
- [x] Add automated core tests and a lightweight CI check.
- [x] Document contribution, security, release, and issue workflows.
- [x] Rename the GitHub repository from `-` to `ACAN-Studio` and update links.
- [ ] Publish a clean 1.2.0 release with refreshed screenshots and checksums.

## 1.3.x — creator workflow improvements

- [ ] Add a visible task queue with cancellation and retry state.
- [ ] Add configurable filename templates and a preview before download.
- [ ] Improve batch compression and output-size verification.
- [ ] Add fixture-based tests for representative platform responses without
  shipping real user media.

## 1.4.x — collaboration and distribution

- [ ] Add release automation for signed/notarized macOS artifacts when signing
  credentials are available.
- [ ] Provide an English documentation page and a short contributor guide for
  new platform engines.
- [ ] Evaluate Windows and Linux support only after the macOS workflow is
  stable and the backend interfaces are platform-neutral.

## Explicit non-goals

ACAN Studio will not bypass DRM, paywalls, login controls, or other platform
access restrictions. Platform support means processing content the user is
authorized to access.
