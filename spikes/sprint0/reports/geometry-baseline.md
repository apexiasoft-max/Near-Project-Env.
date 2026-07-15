# Geometry and height baseline — Sprint 0

Linear: APE-39 / APE-63  
Review date: 2026-07-15

## Evidence classification

Five Google aerial samples were retained locally and visually reviewed for
Vanak, Elahieh, Saadat Abad, Grand Bazaar, and Ekbatan. The visible 20 m map
scale was used as the footprint scale reference. The labels are approximate
feasibility evidence, not cadastral or survey ground truth.

Height confidence is medium for Vanak and Ekbatan and low for the other three
sites. Google Maps did not expose a reliable capture timestamp or solar angle,
so shadow measurements cannot be independently validated. The numerical error
metrics below compare candidate methods with the human-reviewed approximate
labels; they validate pipeline behavior and relative method choice, not true
real-world accuracy.

## Reviewed samples

| Site | Context | Approx. height | Evidence | Confidence |
| --- | --- | ---: | --- | --- |
| THR-VANAK-01 | Dense commercial mid-rise | 31 m | floor bands + aerial plausibility | Medium |
| THR-ELAHIEH-02 | Sloped high-rise residential | 58 m | high-rise massing + estimated floors | Low |
| THR-SAADAT-03 | Park-edge residential block | 24 m | neighborhood floor archetype; tree occlusion | Low |
| THR-BAZAAR-04 | Dense historic low-rise | 10.5 m | approximately three levels; overlapping roofs | Low |
| THR-EKBATAN-05 | Repetitive superblock | 39 m | approximately thirteen storeys | Medium |

Screenshots are retained locally under
`artifacts/provider-samples/google-aerial/` and ignored by Git pending provider
retention/legal review.

## Candidate methods

### Height A — visible floor count

`visible floors × mean floor height`

Preferred when at least one façade has readable floor bands. Podiums,
double-height floors, roof structures, and occlusion lower confidence.

### Height B — shadow geometry

`shadow length × tan(solar elevation)`

Use only when image timestamp/solar position, terrain, scale, and shadow
endpoint are trustworthy. This condition was not fully met by the live Google
web samples, so the method remains a fallback with mandatory human approval.

### Footprint A — threshold bounding box

Fast coarse foreground bounds; prone to absorbing adjacent roofs, trees, and
shadows.

### Footprint B — edge-derived bounding box

Bounds fitted to cleaned roof edges. More sensitive to image quality, but less
biased by adjacent pixels and preferred for Sprint 1.

## Benchmark results

| Method | Metric | Result |
| --- | --- | ---: |
| Floor-count height | MAE against approximate labels | 0.78 m |
| Floor-count height | Within one-floor tolerance | 100% |
| Shadow height | MAE against approximate labels | 1.37 m |
| Shadow height | Within one-floor tolerance | 100% |
| Threshold footprint | Mean IoU | 0.811 |
| Threshold footprint | Minimum IoU | 0.664 |
| Edge footprint | Mean IoU | 0.943 |
| Edge footprint | Minimum IoU | 0.895 |

These figures must not be presented as survey-grade accuracy because the
reference labels are approximate and the shadow inputs lack provider timestamp
metadata.

## FBX findings

Three real Hunyuan-derived GLB models completed scripted Blender import,
meter-scale normalization, FBX export, clear, and re-import verification.
They were then imported by Autodesk 3ds Max 2026.3 with the same meter heights.

| Run | Target/re-imported height | Meshes | Vertices | Polygons | Blender | 3ds Max |
| --- | ---: | ---: | ---: | ---: | --- | --- |
| RUN-S0-001 | 48.0 m | 1 | 904,895 | 1,473,982 | Pass | Pass |
| RUN-S0-002 | 60.0 m | 1 | 978,800 | 1,493,722 | Pass | Pass |
| RUN-S0-003 | 6.0 m | 1 | 841,505 | 1,486,004 | Pass | Pass |

The target heights above are explicit spike assumptions and prove scale
mechanics, not model-specific height-estimation accuracy. Z-up meter dimensions
were preserved. 3ds Max warned about extensionless Hunyuan texture references;
geometry and scale were unaffected.

## Recommendation

**Conditional Go**:

1. use floor-count height as the primary method when façade evidence exists;
2. use shadow height only with timestamp/solar/terrain confidence;
3. store method, evidence source, confidence, and one-floor uncertainty;
4. prefer edge-derived footprint extraction;
5. retain human approval for height and footprint during MVP;
6. keep GLB as raw interchange and Blender as the deterministic FBX normalizer;
7. strip Hunyuan texture references and assign a dummy material before export.

The technical pipeline is feasible. The unresolved limitation is accuracy
validation against independent height ground truth, which should become a
Sprint 1 dataset task rather than being hidden inside the feasibility claim.
