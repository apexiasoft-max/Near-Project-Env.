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

## Product Owner variance

On 2026-07-16 the Product Owner directed the MVP to continue with Google while
Neshan 360 is unavailable. Neshan remains an explicit unavailable observation;
it is not removed from the provider contract and receives no synthetic image.

## Verified Google evidence

The user opened a real Google Street View panorama at camera coordinates
35.784297, 51.3741911. The URL exposes heading 241.14°, a 75° view, panorama ID
`CIHM0ogKEICAgICRlNCugQE`, and the page shows capture date March 2023. The facade
is dominant and clear with minor pole/wire occlusion. The retained evidence is
`google-verified-streetview.png`.

## Gate status

Go with Google-only Product Owner variance. Manual fallback, MissingReference,
reference approval and independent resume remain mandatory and are demonstrated.
