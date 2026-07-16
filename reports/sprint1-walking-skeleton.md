# Sprint 1 Walking Skeleton Evidence

## Delivered path

Project and building creation → five approved directional images → Hunyuan submission state →
non-blocking `awaiting_manual_download` queue → downloaded GLB registration → Blender
normalization → metre-scaled FBX.

## Product decisions implemented

- Waiting for a human Hunyuan download does not block other jobs.
- Each job has a persistent Building ID and Run ID.
- The five generated views are copied with hashes and an input manifest.
- Realistic facade textures are not removed from the five-view inputs.
- No independent height dataset or numeric building-match confidence is required.

## Verification

- Unit/integration suite covers transition rules, artifact manifests, restart recovery and two-job
  non-blocking behavior.
- Live run `RUN-72DA479E8D` used an actual Sprint 0 Hunyuan GLB and Blender 5.0.
- Blender exported and re-imported the FBX and verified a 24 m target height.
- Final local artifact:
  `.local/sprint1-live-demo/projects/PRJ-C509C5F8/buildings/BLD-3CA22640/models/final/RUN-72DA479E8D.fbx`

## Remaining live acceptance

The final workstation demonstration must repeat the UI path with a newly submitted Hunyuan job.
The user action is limited to downloading the completed model; generation of other jobs may continue
while any job awaits that action.

## Fresh workstation run

- Run ID: `RUN-8B1C4812DC`
- The packaged desktop application created the project and copied five approved inputs.
- Hunyuan accepted Front and Back on attempt 1 and Right on attempt 2.
- Hunyuan rejected Top and Left on both allowed attempts, including the prepared dark-gray
  high-contrast retry images.
- The Product Owner accepted proceeding with the three detected views for this MVP run.
- A real Hunyuan job was submitted with Front, Right and Back; geometry and texture generation
  completed and the GLB download control became available.
- Top/Left failure diagnosis is probabilistic because Hunyuan exposes only `Detection failed`:
  Top is a flat orthographic roof view with no visible vertical face, while Left is not a coherent
  true side elevation of the same building. File format and background are unlikely primary causes,
  because the dark-gray retry retained the same failures while Right passed.
- A future controlled A/B check should compare (a) an oblique aerial Top showing roof plus two
  facades and (b) a true 30-45 degree Left view, changing only one variable per attempt.
- The UI now separates `Open Hunyuan` from `Confirm Hunyuan Submission`, preventing a premature
  `Awaiting Manual Download` transition.
- Product correction: direct Hunyuan FBX is now the preferred download. GLB/GLTF remain supported
  fallbacks; Blender imports either path, normalizes metre scale, exports FBX and verifies re-import.
- The manually downloaded artifact was registered to `RUN-8B1C4812DC` and normalized by Blender 5.0.
  The 24 m target re-imported at 24.0000019 m (0.0000019 m absolute error), with one mesh,
  919,078 vertices and 1,418,930 polygons. Verification passed.
- Final workstation artifact:
  `C:/ProgramData/NearProjectEnvironment/projects/PRJ-AF5534DC/buildings/BLD-214CDF32/models/final/RUN-8B1C4812DC.fbx`

## In-application Hunyuan adapter

- The desktop application now owns a persistent-profile Playwright adapter and exposes
  `Upload Views + Start Hunyuan`.
- The adapter maps five approved directional files to the known Hunyuan slots, records detection
  failures, starts generation when at least three views are accepted, and saves sanitized JSON and
  screenshot evidence by Run ID.
- The packaged Windows runtime was rebuilt successfully and passed its worker smoke test.
- Live adapter run `RUN-ADAPTER-LIVE-001` reached Hunyuan but was redirected to Login because the
  dedicated application profile has no authenticated session. Login is the remaining external gate;
  credentials and cookies are not copied from the user's regular Chrome profile.
- After one-time Login, `RUN-ADAPTER-LIVE-002` connected over the dedicated Chrome CDP boundary,
  uploaded all five views, observed two detection failures, accepted three views and automatically
  started generation. Hunyuan completed geometry and texture generation; the output selector was
  changed to FBX and Download became available.
- The direct Hunyuan FBX was downloaded, imported by Blender 5.0, normalized to 24 m, exported and
  re-imported at 24.0000019 m. Verification passed with one mesh, 739,361 vertices and 1,479,326
  polygons.
- Final direct-FBX artifact:
  `C:/ProgramData/NearProjectEnvironment/projects/PRJ-AF5534DC/buildings/BLD-214CDF32/models/final/RUN-ADAPTER-LIVE-002.fbx`
