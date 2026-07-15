# Browser automation proof — Sprint 0

Linear: APE-38 / APE-62  
Review date: 2026-07-15

## Result

**Conditional Go.** The real ChatGPT → five independent views → Hunyuan → GLB
→ scaled FBX path is feasible. UI automation remains fragile and the Hunyuan
download step needs a human fallback until a stable automatic mechanism is
proven.

## Session reuse

- An authenticated ChatGPT session was reopened without login on 2026-07-15.
- Hunyuan was operated through an existing authenticated persistent Chrome
  session after the isolated-profile email verification flow was throttled.
- No cookie, token, password, browser profile, or credential was committed or
  copied into evidence.

The isolated Hunyuan profile attempt produced the distinct provider state
`verification_throttled` (`Send verification code is restricted`). Reusing the
already-authenticated Chrome profile is therefore the recommended MVP path.

## Real workflow evidence

RUN-S0-002 proves one complete path:

1. one generated five-view sheet was split into front, back, left, right, top;
2. all five independent files were mapped to the correct Hunyuan fields;
3. Hunyuan 3DGeneration-V3.1 completed with 1,493,722 faces;
4. download recovered after reloading a stale completed-result page;
5. the 78,002,484-byte GLB was hashed and linked to the Run ID;
6. Blender produced and re-imported a 60 m FBX;
7. 3ds Max independently imported the same FBX at 60 m.

RUN-S0-003 additionally proves two-attempt image recovery, top-view
regeneration, completed Hunyuan generation, manual download fallback, and a
second scaled FBX.

## Failure-state contract

The disposable proof now classifies these states independently:

- `logout`
- `captcha`
- `verification_throttled`
- `timeout`
- `selector_changed`
- `upload_failure`
- `download_failure`
- `no_output`
- `incomplete_output`

The classification is deterministic and unit tested. Provider UI selectors are
contained in the disposable adapter rather than mixed into geometry or artifact
logic.

## Diagnostics and security

- sanitized JSON run evidence is stored under `artifacts/browser-traces/`;
- the upload proof captures a diagnostic screenshot when invoked with an
  evidence path;
- an active-session screenshot was retained locally and ignored by Git;
- artifacts record Run ID, direction mapping, output metrics, hashes, and
  recovery state;
- no secrets are present in committed reports or fixtures.

## Known fragility

- Hunyuan UI selectors and upload-slot count may change;
- detection rejects low-contrast or ambiguous views;
- top view needed independent regeneration in RUN-S0-003;
- Hunyuan result download failed automatically in two observed flows and needed
  reload or a human click;
- CAPTCHA, verification throttling, or session expiration can pause the run;
- ChatGPT and Hunyuan UI automation need periodic adapter maintenance.

## Recommendation

Proceed to Sprint 1 only with:

1. a persistent authenticated browser profile on the dedicated workstation;
2. adapter/page-object isolation for both providers;
3. two automatic attempts, then a Telegram/human-action flag;
4. mandatory screenshots and sanitized structured evidence per failed run;
5. an explicit human fallback for Hunyuan download;
6. the versioned textured-building/dark-gray-background generation contract.
