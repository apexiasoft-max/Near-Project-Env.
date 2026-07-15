# Sprint 0 feasibility artifacts

This directory contains reproducible, non-production evidence for Linear issues
APE-37/61, APE-38/62, and APE-39/63. It must not contain browser profiles,
cookies, tokens, unsanitized traces, or provider imagery whose retention terms
have not been reviewed.

## Provider matrix

Validate the matrix with:

```powershell
python spikes/sprint0/scripts/validate_provider_matrix.py `
  spikes/sprint0/provider-matrix/provider-observations.json `
  --require-complete
```

Run deterministic tests with:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s spikes/sprint0/tests -v
```

Live observations are intentionally separate from deterministic validation.
Each observation records the provider, coordinate, access state, visible
metadata, attribution confidence, failure mode, and evidence reference.

## Mandatory five-view generation contract

Every new ChatGPT five-view generation must use:

- realistic, colored facade textures/materials inferred from approved references;
- no white/gray clay, monochrome, or untextured building output;
- a uniform dark neutral-gray studio background (target RGB `72,76,82`);
- a complete, centered building occupying 65–85% of every panel.

The versioned prompt and approval checklist are stored in
`fixtures/five-view-generation-contract.json`. A run must not proceed to
Hunyuan approval if any mandatory check fails.

## Dedicated Hunyuan browser profile

Login is performed in a normal Chrome process with a local persistent profile.
After manual login, Playwright connects to that already-running browser over a
localhost-only CDP port. The upload still calls `set_input_files()` directly,
so it never opens the native Windows file picker.

One-time login window:

```powershell
.\.venv\Scripts\python.exe .\spikes\sprint0\scripts\hunyuan_browser_spike.py login `
  --profile .\.local\browser-profile\hunyuan `
  --debugging-port 9222
```

Do not request another verification code while Hunyuan displays
`Send verification code is restricted`. Leave Chrome open after a successful
manual login so the upload command can attach to the same session.

Autonomous upload after that login:

```powershell
.\.venv\Scripts\python.exe .\spikes\sprint0\scripts\hunyuan_browser_spike.py upload `
  --profile .\.local\browser-profile\hunyuan `
  --debugging-port 9222 `
  --views .\spikes\sprint0\artifacts\generated-five-view\RUN-S0-002\views `
  --evidence .\spikes\sprint0\artifacts\browser-traces\RUN-S0-002-upload.json
```
