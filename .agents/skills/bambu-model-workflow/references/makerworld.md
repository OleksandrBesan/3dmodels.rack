# MakerWorld browser workflow

Use the project-scoped Playwright MCP server for MakerWorld. Prefer accessibility snapshots and role/name/label locators; use screenshots when visual confirmation adds evidence.

## Discovery and downloads

1. Search the live site and keep the stable model/profile URL for every candidate.
2. Compare model purpose, dimensions, required hardware, printer compatibility, print-profile details, creator notes, photos, makes/comments, and update date.
3. Record creator, model/profile ID, selected variant, displayed license, required attribution, source URL, and download date alongside the local artifact.
4. Download only when the user requested a download and the selected variant and license are clear. Use a workspace path under `.bambu-preflight/downloads/`; do not silently replace an existing file.
5. Run local STL/3MF preflight before opening or modifying the artifact. Treat creator-provided profiles as inputs to review, not proof that they fit the user's printer, nozzle, plate, filament, or firmware.

## Authentication

- Use the Playwright project profile rather than copying browser cookies or bearer tokens into config.
- Let the user perform sign-in, CAPTCHA, two-factor authentication, or account recovery manually in the headed browser.
- Do not expose session state, cookies, access tokens, printer access codes, or account data in output or repository files.
- Do not call reverse-engineered MakerWorld/Bambu Cloud APIs for authenticated actions when the normal website supports the workflow.

## Publishing assistance

1. Complete local preflight and Bambu Studio Preview before preparing an upload.
2. Prepare title, description, tags, category, license, bill of materials, assembly instructions, compatibility, source/attribution, renders/photos, and tested print profile as local draft material.
3. If the user asked for a web draft, fill only draft fields and report whether the site auto-saved. Stop before any final publish/submit control.
4. Immediately before upload or publication, summarize the exact files, visibility, license, attribution, and text that will become public. Require explicit authorization for that final action.
5. After an authorized action, verify the resulting page/status and return the canonical URL. Never claim success based only on a click.

Treat likes, favorites, follows, comments, ratings, report actions, uploads, and publishing as external writes requiring explicit user authorization. Do not bypass anti-bot controls or site warnings. If MakerWorld changes its fields or workflow, inspect the current UI rather than relying on remembered selectors.
