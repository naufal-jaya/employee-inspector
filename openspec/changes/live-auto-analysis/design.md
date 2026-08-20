## Context

The Live Camera tab (`frontend/index.html`, `frontend/app.js`) currently: starts a `getUserMedia` stream into a `<video>` element, then waits for a manual "Capture & Analyze" click to draw a single frame to an offscreen canvas, POST it to `/api/analyze?light=true`, and render results onto a separate frozen `liveCanvas` in a result panel.

The backend is stateless: each frame is an independent synchronous request (`light=true` omits the base64 image so the client renders boxes from JSON). Competition constraint: no websockets/streaming/background jobs — this stays true under the new design.

## Goals / Non-Goals

**Goals:**
- Continuous auto-analysis of the webcam feed (~1s throttle) with no user interaction.
- Annotations overlaid directly on the live video feed.
- Metrics and Worker Compliance list update automatically on each completed analysis.
- Clean lifecycle: start/stop camera, and pause-loop-on-tab-switch with camera kept alive.
- Purely frontend change; backend API contract untouched.

**Non-Goals:**
- True real-time streaming or websocket backend (forbidden by competition MVP rules).
- Frame-rate control beyond a fixed ~1s throttle.
- Persistence or logging of live results.
- Reducing inference latency of the backend.

## Decisions

### D1 — Overlay canvas on top of the `<video>` element
Wrap `<video>` and a transparent `<canvas id="liveOverlay">` in a `position:relative` `.live-viewport`; the canvas is `position:absolute; inset:0; width:100%; height:100%; pointer-events:none`. The video plays natively (cheap CPU), and only the overlay is redrawn when a result arrives.
- **Alternative considered**: A "canvas-as-view" that redraws the video into a canvas every animation frame — simpler compositing but redraws the full frame at 60fps; rejected for extra CPU cost with no user-visible benefit.

### D2 — Throttled analysis loop with busy-guard
A `setInterval(liveAnalyzeLoop, 1000)` started after the camera starts. `liveAnalyzeLoop`:
1. Skips if `liveBusy` is true (previous request still in flight) — prevents queue buildup and matches backend speed automatically.
2. Draws the current video frame to an offscreen canvas downscaled to ≤640px wide (reusing the existing downscale math).
3. `canvas.toBlob('image/jpeg', 0.85)` → `POST /api/analyze?light=true`.
4. On success: draw boxes/labels onto the overlay (`liveOverlayScale = overlayWidth / analyzedFrameWidth`), update metrics + Worker list, then clear `liveBusy` (in `finally`).
- **Alternative considered**: requestAnimationFrame-driven loop — no advantage since analysis cadence is bounded by network+inference (~1–2s), not display refresh.

### D3 — Effective refresh follows backend speed
Because of the busy-guard, the effective analysis rate is `min(1s, inference+latency)`. This is the intended behavior; a slower GPU degrades gracefully to fewer updates rather than queuing stale frames.

### D4 — Reuse existing drawing helpers
The existing `drawLiveAnnotations(ctx, data, scale)` and `liveCategoryColor(category)` are reused for the overlay, with `scale = overlayWidth / analyzedFrameWidth`. Removes the old `liveCanvas` result panel and `liveCapture`/`captureLiveFrame()`.

### D5 — Tab-switch lifecycle
In the existing tab-switch handler (`frontend/app.js` DOMContentLoaded): when leaving the live panel → `clearInterval(liveAnalyzeTimer)` (camera keeps streaming); when entering the live panel while the camera is active → restart the interval. `stopLiveCamera()` clears the timer, stops tracks, and wipes the overlay.

### D6 — No backend changes
`/api/analyze?light=true` already returns all needed data (`all_objects`, `results`, `summary`). Reusing it keeps the "single-frame stateless request" constraint intact.

## Risks / Trade-offs

- [Annotation lag vs. moving video] → Inherent to non-streaming inference (up to ~1–2s). Mitigated by busy-guard so results are always fresh, never stale-queued; acceptable for a demo.
- [Browser throttling when tab hidden] → The camera keeps running but the analysis loop is intentionally paused on tab switch, avoiding background inference spam.
- [Effective rate drops on slow GPU] → Graceful degradation by design (busy-guard); no UX failure, only fewer updates.
- [Overlay size mismatch on resize/window scaling] → Overlay is sized from `video.videoWidth/Height` once, with CSS `width:100%/height:100%` keeping both layers in lockstep.

## Open Questions

None — the three UX decisions (1s throttle, overlay + persistent panel, pause-on-tab-switch) are confirmed with the user.