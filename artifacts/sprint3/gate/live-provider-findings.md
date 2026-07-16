# Sprint 3 live provider findings

Date: 2026-07-16  
Target: Vanak, Tehran — 35.7577, 51.4099

## Google

Direct Street View navigation loaded a 3D map perspective rather than a verified
building-level panorama. The result is retained as `google-candidate.png` and is
classified as **not suitable**. No false attribution is created.

## Neshan

Coordinate navigation and map zoom were available. No selectable 360 panorama or
stable camera metadata was exposed in the tested web state. The result is retained
as `neshan-candidate-unavailable.png` and is classified as **MissingReference**.

## Product behavior verified

- Provider failure is evidence, not a parser crash.
- An unsuitable observation is not silently assigned to the building.
- Manual-project-pool replacement can be selected and approved.
- MissingReference creates an independent pending Telegram intervention event.
- Other buildings remain processable.

## Gate status

Conditional. Deterministic provider-neutral ranking, manual fallback, approval and
resume are implemented. The live Gate still requires one verified building-level
candidate from each provider, or explicit Product Owner acceptance that a provider
with no coverage is represented by an unavailable observation rather than an image.
