# Sprint 0 Review

Date: 2026-07-15  
Milestone: M0 — Feasibility Gate  
Gate: APE-88

## Sprint Goal

Reduce the three critical feasibility risks before building the production
application: Tehran imagery access and attribution, authenticated browser
automation across ChatGPT/Hunyuan, and geometry/height/FBX processing.

## Delivered Evidence

- five Tehran Google/Neshan provider observations and five retained local
  Google aerial review samples;
- three five-view runs with independent directional images;
- two documented completed Hunyuan web-generation/download outcomes;
- three real Hunyuan-derived GLB models;
- three verified meter-scaled FBX files;
- Blender 5.0 round-trip results and Autodesk 3ds Max 2026.3 imports;
- five-sample height/footprint benchmark with explicit confidence limits;
- 24 deterministic unit tests;
- sanitized run manifests, hashes, reports, scripts, and runbook guidance.

## Story Results

### APE-37 — Validate Tehran imagery providers

**Pass / Conditional Go.** Google aerial access is usable in all five samples;
street/360 coverage is uneven. Neshan's public UI is accessible, but stable
building-level 360 selection and camera metadata were not proven. Provider
terms and retention require owner/legal review before production collection.

### APE-38 — Prove web generation automation

**Pass / Conditional Go.** Active ChatGPT and Hunyuan sessions can be reused.
The five-view-to-Hunyuan pipeline produced real models. UI automation is
fragile, and Hunyuan download required reload or a human click in observed
failure cases. Nine failure states are classified distinctly.

### APE-39 — Establish geometry baselines

**Pass / Conditional Go.** Five aerial samples were human reviewed with
approximate height/footprint labels. Two height and two footprint approaches
were benchmarked. Three real models passed Blender scale/export/re-import and
3ds Max import at exact target meter heights. Independent survey-grade height
accuracy remains unavailable.

## Gate Results

| Checklist | Result | Evidence |
| --- | --- | --- |
| Real Tehran imagery access | Pass | provider matrix, report, five local aerial samples |
| ChatGPT → Hunyuan → FBX | Pass with human fallback | RUN-S0-002 and RUN-S0-003 manifests |
| Detection/height baseline | Pass with confidence limitation | five-sample benchmark and report |
| Three Hunyuan FBX compatibility checks | Pass | Blender JSON + 3ds Max TSV |
| Architecture decisions recorded | Pass | this review and reports |
| Unknown critical risk hidden | Pass | remaining risks listed below |

## Test Results

- Unit: 24/24 pass.
- Provider matrix schema/complete-mode validation: pass.
- Blender integration: three imports, normalizations, exports, and re-imports
  pass within configured tolerance.
- 3ds Max integration: three FBXs import with exact 48 m, 60 m, and 6 m Z
  extents.
- Live browser: authenticated ChatGPT reuse confirmed; Hunyuan generations and
  downloads completed with recorded recovery paths.
- Manual: five Google aerial samples visually reviewed; Hunyuan detection and
  human download fallback exercised.

## Technical Findings

### Providers

Google is the practical first provider; Neshan is a best-effort fallback.
Coverage visibility does not prove building attribution. Camera heading, FOV,
and capture metadata must be optional fields with confidence.

### Browser automation

Use the already-authenticated persistent workstation browser. Keep provider
selectors behind adapters. Retry twice, capture structured evidence, then flag
for human action. Do not depend on requesting a fresh Hunyuan verification code.

### Five-view generation

Require realistic colored façade textures and a uniform dark neutral-gray
background. Top view may need independent near-top regeneration. Preserve the
versioned direction mapping and validate every independent image before upload.

### Height and footprint

Use visible floor count first. Use shadow geometry only with reliable timestamp,
solar elevation, terrain, scale, and shadow endpoint. Preserve method,
confidence, evidence source, and one-floor uncertainty. Prefer cleaned
edge-derived footprint geometry to a coarse threshold box.

### FBX

Keep raw GLB, normalize through Blender in meters and Z-up, export FBX, then
re-import for verification. Strip Hunyuan texture references and assign a dummy
material; extensionless packed texture names cause 3ds Max warnings.

## Architecture Decisions

1. Windows workstation orchestration with persistent authenticated sessions.
2. External-provider adapters/page objects isolated from workflow logic.
3. Run ID and Building ID required on every artifact and evidence record.
4. Local artifacts excluded from Git; only sanitized manifests/reports are
   versioned.
5. Human approvals retained at imagery attribution, five-view acceptance, and
   final model review.
6. Two automatic attempts followed by a flagged human fallback.
7. Blender is the deterministic meter-scale FBX normalization boundary.
8. Provider metadata and height estimates always include confidence and source.

## Open Risks

| Risk | Severity | Mitigation |
| --- | --- | --- |
| Provider terms may restrict automated acquisition/retention | Critical | owner/legal review before production collector |
| Hunyuan download UI is unreliable | High | bounded retries + reload detection + human fallback |
| Provider selector/session changes | High | adapters, diagnostics, persistent profile, runbook |
| Building attribution ambiguous | High | geometry scoring + confidence + human approval |
| Height labels lack independent ground truth | High | Sprint 1 measured validation dataset |
| Neshan building-level 360 contract unproven | Medium | best-effort fallback spike in vertical slice |
| Hunyuan textures not portable to Max | Medium | strip textures; assign dummy material |
| Very dense meshes slow downstream tools | Low for MVP | cleanup remains an accepted human post-process |

## Scope Changes Recommended

- Add a Sprint 1 task for independent height ground-truth validation.
- Add a bounded Hunyuan result/download adapter task with explicit human
  fallback.
- Add deterministic dummy-material cleanup to FBX normalization.
- Keep Neshan as fallback until building-level selection is proven.
- Do not add distant dummy buildings, automatic neighborhood image pools,
  Unreal placement, or the main project building to MVP scope.

## Final Recommendation

**Conditional Go.** Sprint 1 may begin only after the Product Owner accepts the
listed conditions. The core pipeline is feasible; the conditions protect the
MVP from provider legality, attribution, height-ground-truth, and browser-
download fragility.

## Next Action

Product Owner decision: accept or reject the Conditional Go conditions. Sprint
1 must not start automatically.
