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
- The run is flagged for human review before generation. It must not be represented as submitted.
- The UI now separates `Open Hunyuan` from `Confirm Hunyuan Submission`, preventing a premature
  `Awaiting Manual Download` transition.
