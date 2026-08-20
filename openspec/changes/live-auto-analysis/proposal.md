## Why

The Live Camera tab currently requires a manual "Capture & Analyze" click per frame, and results are drawn on a separate frozen canvas below the live feed. This feels like a photo tool, not live monitoring — the demo value of a real-time safety inspection is lost.

## What Changes

- Replace the manual "Capture & Analyze" button with an **automatic analysis loop** (~1s throttle) that starts when the camera starts and stops when the camera stops.
- Draw detection boxes and labels as an **overlay directly on the live video feed** instead of a separate frozen result canvas, so annotations appear on the moving camera view.
- Keep the metrics cards (Risk Score / Persons / Violations / Hazards) and the Worker Compliance list, updating automatically on every completed analysis.
- Pause the analysis loop when the user switches to another tab; the camera keeps running and the loop resumes when returning.
- **BREAKING**: Remove the manual "Capture & Analyze" button and the old `liveCanvas` result-panel canvas from the Live Camera tab.
- The backend is **unchanged**: still the single-frame, stateless synchronous `/api/analyze?light=true` path — no websockets, no streaming, no background jobs.

## Capabilities

### New Capabilities
<!-- Capabilities being introduced. Replace <name> with kebab-case identifier (e.g., user-auth, data-export, api-rate-limiting). Each creates specs/<name>/spec.md -->
- `live-auto-analysis`: Continuous, throttled auto-analysis of the webcam feed in the Live Camera tab, with annotations overlaid on the live video and live-updating metrics.

### Modified Capabilities
<!-- Existing capabilities whose REQUIREMENTS are changing (not just implementation).
     Only list here if spec-level behavior changes. Each needs a delta spec file.
     Use existing spec names from openspec/specs/. Leave empty if no requirement changes. -->
- `live-camera-input`: The manual single-frame capture requirement changes to an automatic continuous analysis loop over the webcam feed. `light=true` and "no backend background work" requirements are unchanged.

## Impact

- `frontend/index.html` — Live Camera tab: remove Capture button, wrap `<video>` + overlay `<canvas>` in a viewport container, restructure result display.
- `frontend/app.js` — remove `captureLiveFrame()`/`liveCapture` state; add analysis loop with busy-guard, overlay drawing, and tab-switch pause/resume.
- `frontend/style.css` — `.live-viewport` positioning and overlay canvas styling.
- Backend, models, tests, and API contract: **no changes**.