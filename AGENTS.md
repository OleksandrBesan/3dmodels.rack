# Repository work contract

- This repository is a curated release boundary. Read `docs/excluded-models.md`
  before adding any upstream geometry or copying files from another checkout.
- Keep current printable variants under `models/<collection>/`, each with a
  README stating dimensions, print assumptions, validation status and sources.
- Preserve input models. Build drafts under ignored `.bambu-preflight/` and
  only replace current exports after tests and inspection.
- Model coordinates are millimeters. Confirm axis, total change versus change
  per side, hole-center span, aperture size and mating surfaces before editing.
  Do not globally scale mounting holes or remove connectors inadvertently.
- Use `.agents/skills/bambu-model-workflow/SKILL.md` for model preflight.
  Automated topology checks are not Bambu Preview or physical fit tests.
- Run `python3 -m unittest discover -s .agents/skills/bambu-model-workflow/tests`.
  Run the modeling suite with the dependency command in `tools/README.md`.
- Do not upload, publish, send a model to a printer or start printing without
  explicit user authorization. Do not change repository visibility as a side effect.
- Never commit login cookies, access codes, `.env` files, local absolute paths,
  personal photos or application screenshots. Keep external MCP servers optional.
- Use `apply_patch` for source edits. Do not discard unrelated working changes.
