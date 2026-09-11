# Models intentionally not distributed

The following parts remain only in the private development repository. No old
history, meshes, projects, copied previews, or construction snapshots for them
were imported into this repository.

| Excluded model | Private filename/group | Reason |
| --- | --- | --- |
| TP-Link TL-SG116P shelf | `TL_SG116P_shelf.stl/.3mf`, all revisions | Derived from Benjamin Kott's rack CAD; recorded Standard Digital File License |
| Shaped TP-Link front retaining caps | `tplink_closures/front_cap.stl/.3mf` | Outline copied from that shelf, so not treated as independent geometry |
| Full shaped TP-Link rear cover | `tplink_closures/rear_cover.stl/.3mf` | Same shelf-derived outline |
| Raspberry Pi 4 PoE-HAT carrier | `KWS_RPi4_original_PoE_HAT_carrier.stl/.3mf` | Adapted KWS geometry; recorded MakerWorld Exclusive License |
| KWS snap handle | `KWS_snap_handle.stl/.3mf` | KWS-derived geometry |
| KWS-to-Kott 2U frame | `KWS_snap_frame_for_Benjamin_Kott_rack_2U.stl/.3mf` | KWS geometry plus Kott mounting-source geometry |

Recorded source licenses were checked during development on 2026-09-09.
The exact source pages were not accessible during this release audit. Treat
these parts as withheld unless the rights holders give adequate redistribution
permission or verifiable alternative license evidence is established.
Attribution and personal modifications do not by themselves provide permission.

Sources:

- [Benjamin Kott — Modular 10-inch Server Rack, 1452571](https://makerworld.com/en/models/1452571-modular-10-server-rack).
- [ilanKush — Rack Snap-in system, 2314737](https://makerworld.com/en/models/2314737-rack-snap-in-system-8-bay-raspberry-pi-cluster).

The three simple TP-Link strips in this repository are distinct from the
shaped covers: their original generator constructs rectangles, rounded-square
openings, vents and text using primitives, without importing the restricted
shelf or rack mesh. Their mounting dimensions were used for compatibility.
