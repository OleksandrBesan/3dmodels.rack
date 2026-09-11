# Licenses

Owner-approved policy, 2026-09-11. This repository uses separate licenses for
original models, code/documentation, and upstream geometry.

## Original models — CC BY-NC-SA 4.0

Copyright (c) 2026 OleksandrBesan. The following original STL/3MF models are
licensed under [Creative Commons Attribution–NonCommercial–ShareAlike 4.0
International](https://creativecommons.org/licenses/by-nc-sa/4.0/):

- All model files in `models/tplink_panels/`.
- All model files in `models/plate_cleanup/`.
- `models/cable_passthrough/PatchPanel_BLANKING_INSERT_V1.stl` and `.3mf`.
- `models/cable_passthrough/PatchPanel_CABLE_INSERT_8MM_V1.stl` and `.3mf`.
- `models/cable_passthrough/PatchPanel_CABLE_INSERT_10MM_V1.stl` and `.3mf`.

Credit OleksandrBesan and link to [this repository](https://github.com/OleksandrBesan/3dmodels.rack).
Retain attribution, indicate changes, use noncommercially, and share adaptations
under the same license. The [full legal terms](https://creativecommons.org/licenses/by-nc-sa/4.0/legalcode.en)
govern. This license does not grant rights to trademarks or excluded upstream works.

## Code, documentation and Codex setup — MIT

Original code and documentation in `tools/` (excluding `tools/sources/`),
`.agents/`, `.codex/`, `docs/`, model READMEs/reports, and repository-root
documentation/configuration are covered by [the MIT license](LICENSE-MIT.txt).
Illustrations of third-party geometry retain the applicable upstream rights;
MIT does not relicense the depicted models. License texts retain their own terms.

## Upstream cable geometry — original BY-NC-SA terms

`models/cable_passthrough/PatchPanel_TOP_ENTRY_12MM_V1.stl` and `.3mf`, and
`tools/sources/cable_panel_blank.stl`, retain Dawnchaser's recorded `BY-NC-SA`
terms. The numerical version must still be confirmed before public release.
The owner's approval above does **not** replace the upstream license with 4.0
or grant rights the owner does not hold.

Third-party software dependencies are not vendored; their own terms apply.
Restricted-source models are excluded, rather than relicensed.

See [provenance](docs/sources.md) and [excluded models](docs/excluded-models.md).
Keep the repository private until the release blockers are resolved.
