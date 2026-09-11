---
name: bambu-model-workflow
description: Validate STL and 3MF files for predictable Bambu Studio import; inspect or repair meshes with Blender, prepare printer-specific Bambu 3MF and sliced output, and use Playwright for reviewed MakerWorld search, download, and draft-publishing workflows. Use for Bambu model preflight, slicing readiness, print-profile packaging, or MakerWorld work.
---

# Bambu Model Workflow

Produce an evidence-backed `PASS`, `WARN`, or `FAIL` handoff. Never describe a model as guaranteed printable: automated checks cannot prove physical tolerances, adhesion, material behavior, support quality, or successful printing.

## Route the request

- For STL/3MF validation or Bambu Studio import readiness, follow [references/preflight.md](references/preflight.md).
- For MakerWorld discovery, downloads, attribution, or publishing assistance, follow [references/makerworld.md](references/makerworld.md).
- For a request spanning both, finish the local preflight before preparing a MakerWorld upload or print profile.

## Default workflow

1. Preserve the source model. Make repairs and transformations on a copy in `.bambu-preflight/`.
2. Run the bundled validator by resolving `scripts/validate_model.py` relative to this `SKILL.md`:

   ```bash
   python3 <skill-dir>/scripts/validate_model.py <model.stl-or-3mf> --json
   ```

3. For an STL, state that STL is unitless and cannot contain printer, plate, nozzle, filament, support, or process settings. Confirm millimeter scale and obtain the target printer/profile facts before slicing.
4. Use Blender MCP for visual inspection or mesh repair when structural validation fails or visual risks need review. Modify a copy, export it, and rerun the validator.
5. Prefer a known-good Bambu Studio 3MF template for printer-specific configuration. Use the offline `bambu_modeling` MCP tools to inspect, orient, template, and slice. Preserve the template and generated artifact separately.
6. Validate the project 3MF with `--require-bambu-settings`; validate sliced output with `--require-sliced`.
7. Open the result in Bambu Studio Preview and inspect layers, first-layer contact, thin features, supports, seams, bridges, material mapping, and collisions. Record anything not verified.
8. Report source path, output path, commands/tools used, validation status, remaining warnings, and the exact manual review still required.

## Safety boundaries

- Treat downloaded STL/3MF files as untrusted. Do not extract 3MF archives manually; the validator reads them with entry-count, path, size, CRC, and XML checks.
- Keep MakerWorld and Bambu credentials in the browser/application session. Never place cookies, tokens, access codes, or printer credentials in repository files, prompts, logs, or third-party MCP configuration.
- Browsing and preparing local drafts are allowed within the user request. Require explicit user authorization immediately before uploading, publishing, commenting, favoriting, starting a print, or sending files to a printer.
- Do not bypass CAPTCHA, anti-bot checks, two-factor authentication, license restrictions, or site warnings. Pause for the user when manual authentication is required.
- The configured `bambu_modeling` server is community software and is restricted to offline model/slicing tools. Do not enable its printer-control tools without a separate request and security review.
