# Tehran imagery provider feasibility — Sprint 0

Linear: APE-37 / APE-61  
Observation dates: 2026-07-14 to 2026-07-15

## Test design

Five representative Tehran contexts were tested in both Google and Neshan:
Vanak, Elahieh, Saadat Abad, Grand Bazaar, and Ekbatan. Structured results are
stored in `provider-matrix/provider-observations.json`.

Google aerial screenshots were retained locally for human review under
`artifacts/provider-samples/google-aerial/`. They are excluded from Git pending
an owner/legal review of provider retention and automation terms. No cookies,
tokens, credentials, or browser profile data were retained.

## Provider comparison

| Capability | Google | Neshan |
| --- | --- | --- |
| Public web map access | Available in all five samples | Available in all five samples |
| Aerial imagery | Available and visually reviewed in all five | Not proven in this spike |
| Street/360 signal | Linear coverage or photo spheres in 4/5 tested contexts | Neshan 360 control visible, but building-level selection not proven |
| Stable camera coordinate | Not exposed as a reliable web contract | Not observed |
| Heading / field of view | Not exposed as a reliable web contract | Not observed |
| Building attribution | Medium at best; ambiguous with occlusion/repetition | Unproven |
| Automation dependency | Provider UI and session behavior | Provider UI and coordinate-navigation behavior |

## Per-site Google result

| Site | Street/360 signal | Attribution confidence | Primary failure mode |
| --- | --- | --- | --- |
| Vanak | Linear coverage + photo spheres | Medium | occlusion and target-building attribution |
| Elahieh | No discoverable path/sphere at tested viewport | None | missing or undiscoverable coverage |
| Saadat Abad | Linear coverage | Medium | capture date and attribution not proven |
| Grand Bazaar | Fragmented photo spheres | Low | dense fabric and incomplete coverage |
| Ekbatan | Linear coverage + photo spheres | Medium | repetitive blocks create ambiguity |

## Camera metadata finding

Map coordinates are available from navigation state, but camera position,
heading, capture date, and field of view were not exposed as a stable,
machine-readable contract on either provider's tested public UI. The pipeline
must treat these fields as optional and reconstruct attribution geometrically
when possible. Missing metadata is a distinct result, not a parser failure.

## Failure modes

- no street/360 coverage;
- fragmented photo-sphere-only coverage;
- old or unknown capture date;
- façade occlusion by trees, traffic, or adjacent buildings;
- repetitive-building attribution ambiguity;
- coordinate navigation not selecting the intended building;
- missing heading/FOV/camera metadata;
- login, CAPTCHA, throttling, or provider UI changes;
- image quality too low for façade reconstruction.

## Operational and legal constraints

The spike proves technical web access only. It does not establish permission to
bulk download, retain, transform, or redistribute provider imagery. Before a
production collector is enabled, the product owner must obtain a current terms
and legal review for Google and Neshan. Until then, provider screenshots remain
local, non-committed feasibility artifacts and human approval remains required.

## Recommendation

**Conditional Go.** Use Google as the first aerial/street candidate and Neshan
as a best-effort fallback. Every candidate image must carry provider, capture
availability, attribution confidence, and failure state. Do not accept an image
only because a 360 control or coverage overlay exists. Keep the approval gate
until building-level attribution and permitted acquisition are proven.
