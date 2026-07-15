# 3ds Max FBX Compatibility — Sprint 0

Date: 2026-07-15  
Environment: Autodesk 3ds Max 2026.3, Windows, meter system units

## Result

All three normalized Hunyuan-derived FBX files imported successfully through
`3dsmaxbatch.exe`. Geometry was present and the imported Z extent matched the
target height exactly for every sample.

| Run | Objects | Vertices | Faces | Imported dimensions (m) | Target height | Result |
| --- | ---: | ---: | ---: | --- | ---: | --- |
| RUN-S0-001 | 1 | 904,895 | 1,473,982 | 21.7101 × 21.5590 × 48.0000 | 48 m | Pass |
| RUN-S0-002 | 1 | 978,800 | 1,493,722 | 28.0441 × 27.9458 × 60.0000 | 60 m | Pass |
| RUN-S0-003 | 1 | 841,505 | 1,486,004 | 6.9598 × 7.46659 × 6.0000 | 6 m | Pass |

Tolerance: 0.02 m.

## Texture warning

3ds Max emitted `Could not read/write file type` warnings for packed texture
references whose generated filenames have no image extension. This did not
prevent mesh import or alter scale, but it means the current FBX package is not
yet a clean portable textured package. The MVP only requires geometry with a
dummy material, so the recommended normalization step is to strip or replace
Hunyuan texture references before final export.

## Reproduction

Run `spikes/sprint0/scripts/verify_fbx_3dsmax.ms` with Autodesk
`3dsmaxbatch.exe`. The script resets the scene for each sample, sets system
units to meters, imports the FBX, counts geometry, measures the world bounding
box, and writes the TSV evidence file.

Machine-readable evidence:
`spikes/sprint0/artifacts/benchmark-results/3dsmax-fbx-compatibility.tsv`

## Recommendation

**Go** for FBX geometry and meter-scale compatibility across Blender and 3ds
Max. Add deterministic dummy-material cleanup to the production normalization
pipeline; do not depend on Hunyuan's packed texture filenames.
