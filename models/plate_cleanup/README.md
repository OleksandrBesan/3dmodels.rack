# PETG residue lifting patch

Current files are paired `.stl` and `.3mf` files in this folder. The three shapes serve different residue patterns; none is an older revision of another.

## Source and MakerWorld references

Locally created from the user's failed-print/residue photographs, including `IMG_0023.HEIC`. **No MakerWorld geometry or model reference was used for these cleanup aids.** They are print utilities, not rack components. [Project packager](../../tools/build_support_footprint_3mf.py).

## Use

These cleanup aids lift very thin PETG residue from a textured PEI plate when
the residue is too thin to catch with flexing or a plastic scraper.

- `PETG_residue_lift_patch_50x50x1mm` is the small test tile.
- `PETG_support_footprint_lift_patch_100x140x1mm` follows the photographed
  failed-support footprint. Its connected top band, long left leg, short right
  leg, and peel foot cover the visible residue while leaving the center open.
  The fit is estimated from the photo, so align it over the residue in Bambu
  Studio before slicing.
- `PETG_remaining_support_islands_lift_patch_1mm` corrects the areas visible in
  `IMG_0023.HEIC` that the U-shaped patch missed. It contains six disconnected
  pickup pads for the three round islands, inner-left trace, center fragments,
  and lower-right support/tree trace. The project preserves their positions in
  the same 100 x 140 mm reference frame as the U-shaped patch. Do not use
  auto-arrange; if the U-shaped project was moved before printing, align these
  pads visually over the remaining residue instead.

1. First test the method on a small affected area. In Bambu Studio, move and
   rotate the selected patch directly over the residue. Scale only X/Y if an
   adjustment is needed; keep Z at 1 mm.
2. Print with the same PETG that left the residue. The supplied P2S project uses
   the 0.20 mm Standard process, five bottom and top shell layers with no sparse
   infill, no brim, and no supports. The 1 mm tile is therefore fully solid.
3. Let the plate reach room temperature before removal. If it does not release,
   put the fully cooled plate in a freezer for 10-20 minutes, then gently peel
   the patch. Do not force it if the PEI coating starts to lift.
4. Remove each disconnected island pad separately after cooling. Repeat with a
   repositioned pad if residue falls outside its photographed estimate. Wash
   the plate with plain dish soap and warm water afterward.

Do not use a metal blade or acetone. This method is not risk-free: PETG can bond
strongly to PEI, so use the smallest patch that covers the residue and test first.
