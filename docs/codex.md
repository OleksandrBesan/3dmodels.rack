# Optional Codex setup

No Codex subscription or MCP connection is needed to open the printable files.
The standalone validator uses Python's standard library.

## Start here

1. Install Codex through the [official setup instructions](https://developers.openai.com/codex/quickstart).
2. Start it from this repository's root (`codex`). Review the repository and
   trust it only if you want its project configuration loaded.
3. Read `AGENTS.md` and the included Bambu workflow skill.
4. Optional integrations are declared in `.codex/config.toml`, all disabled by
   default. Enable only the servers you need, then restart Codex.

The template uses commands found on `PATH`, not one developer's home directory.
It does not override your chosen model, provider or authentication. Its default
workspace sandbox and approval policy do not grant printer or publishing permission.

## Optional integrations

| Server | Prerequisites | Scope |
| --- | --- | --- |
| Blender | `uvx`, Blender, companion Blender MCP add-on/server | Inspect and edit geometry; community integration |
| Playwright | `npx`, Node.js, Chrome | Browser inspection; normal sign-in/CAPTCHA remain manual |
| Bambu modeling | `npx`, Bambu Studio, local `SLICER_PATH` environment variable | Offline model operations and slicing; community integration |

Version pins preserve the development setup, not a claim that these packages
are the latest or vulnerability-free. Review them before execution. The Blender
add-on must be installed and its server enabled separately. No add-ons, npm
packages, or Python packages are vendored or automatically installed by cloning.

Set `SLICER_PATH` in your own environment to your installed Bambu Studio
executable. Do not commit the local path. Browser profiles and tool output use
relative directories under `.bambu-preflight/`; launch Codex from the root so
these resolve consistently. Never reuse or commit a personal browser profile.

The Bambu server uses an explicit offline tool allowlist. Network/printer-control
tools are not enabled. `default_tools_approval_mode = "writes"` requests approval
for tools not marked read-only; tool annotations are not a substitute for review.

Use `codex mcp list` or `/mcp` to inspect connections. TOML parsing and safe
defaults were checked. The audit CLI listed only its global servers, not this
new project's definitions, so project-config activation is **not verified**.
After reviewing/trusting the project, confirm the three definitions appear
before enabling them. Optional server startup, hardware connections and GUI
slicing have not been tested in a fresh third-party environment.

Configuration fields were checked against the [official MCP documentation](https://developers.openai.com/codex/mcp)
and [configuration reference](https://developers.openai.com/codex/config-reference)
on 2026-09-11. Authentication belongs in your user-level Codex configuration or
keychain, never this repository.
