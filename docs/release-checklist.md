# Release review — 2026-09-11

This is a **private draft**, not legal clearance or a guarantee of printable fit.

## Completed

- New repository initialized independently; no private development history imported.
- Restricted-source shelf, shaped covers, Pi carrier/handle and KWS frame excluded.
- Ten current printable variants: four cable-panel/insert variants, three
  strip panels and three cleanup patches. One upstream cable source mesh is
  also present and subject to its original license.
- Personal absolute paths removed from public documentation/configuration.
- New commits use a GitHub no-reply identity, not a personal email address.
- Optional MCP integrations disabled by default; offline Bambu tool allowlist.
- 9 model/layout tests and 22 validator tests passed.
- Structural checks passed for 10 STL/3MF pairs and the upstream source STL.
  Usual Preview/fit limitations remain; the cleanup-islands part intentionally
  contains multiple components.
- Targeted credential/path scan of the candidate files and 3MF contents found
  no matches. This is not a full third-party security certification.
- Temporary logs and diagnostic scripts remain ignored, outside the public tree.

## Before changing visibility

- [x] Owner approved CC BY-NC-SA 4.0 for original models and MIT for code,
  documentation and Codex setup on 2026-09-11; scope recorded in `LICENSE.md`.
- [ ] Confirm the precise upstream CC BY-NC-SA version and add the correct
  license notice/link for the cable-panel source and derivative. Alternatively,
  withhold that geometry and adjust dependent tests/tools/docs before publication.
- [ ] Review the exact staged/pushed file list and the license scope again.
- [ ] Owner explicitly approves making this prepared repository public.

## Not claimed

- No new physical print tests or Bambu layer review were performed for this export.
- Codex MCP project-config activation and fresh optional-server startup were
  not verified; see [setup notes](codex.md).
- This review does not grant rights to excluded upstream geometry or remove
  its restrictions merely because modifications were made locally.
