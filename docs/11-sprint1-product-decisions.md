# Sprint 1 Product Decisions

Date: 2026-07-15  
Authority: Product Owner

These decisions supersede conflicting feasibility recommendations in Sprint 0
reports and govern Sprint 1 implementation.

## Provider usage

Provider imagery acquisition and retention are not treated as a product legal
gate or engineering risk. No legal-review task blocks implementation.

## Hunyuan download boundary

Hunyuan model download is manual in the MVP. Manual download must not block
other buildings:

1. each submitted building receives a persistent Job and Run ID;
2. after generation, its state becomes `awaiting_manual_download`;
3. the worker continues processing other eligible jobs;
4. Hunyuan results may remain open in a bounded number of browser tabs;
5. the operator downloads completed models in any order;
6. the application detects or accepts each downloaded file, associates it with
   Building ID/Run ID, and resumes Blender processing automatically.

## Height estimation

No independent ground-truth or golden height dataset is required. Height is
estimated from available evidence: visible floors, shadows, comparable
buildings, aerial scale, and human correction. The target remains the best
practical estimate, normally within approximately one floor where evidence is
usable.

## Building-image matching

The MVP does not require a complex numeric confidence score. The system stores
the selected source and any ambiguity note, then the operator confirms or
corrects the match at the reference approval step.

## Texture behavior

Real facade appearance must remain consistent across front, back, left, right,
and top images supplied to Hunyuan. Generation must not replace the building
with white/gray clay output or alter materials between directions.

Hunyuan model texture references are a separate output concern. Valid model
textures may be preserved. Missing or unreadable texture files must not fail
geometry delivery; the model may fall back to a dummy material without changing
the five-view generation contract.
