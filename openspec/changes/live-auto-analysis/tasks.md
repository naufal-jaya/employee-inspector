## 1. HTML Structure (index.html)

- [x] 1.1 Remove the "Capture & Analyze" button (`captureLiveBtn`) from the Live Camera controls; keep Start/Stop buttons
- [x] 1.2 Wrap the `<video id="liveVideo">` and a new transparent `<canvas id="liveOverlay">` in a `position:relative` viewport container (e.g. `.live-viewport`); place the canvas absolutely over the video
- [x] 1.3 Remove the old result-panel `<canvas id="liveCanvas">`; keep metrics cards and Worker Compliance list visible while streaming

## 2. Overlay CSS (style.css)

- [x] 2.1 Add `.live-viewport` positioning and give the overlay canvas `position:absolute; inset:0; width:100%; height:100%; pointer-events:none`

## 3. Auto-Analysis Loop (app.js)

- [x] 3.1 Remove `captureLiveFrame()` and the `liveCapture` state; keep `liveStream` and add `liveAnalyzeTimer` + `liveBusy` + `liveOverlayScale` state
- [x] 3.2 In `startLiveCamera()`: after video plays, size the overlay canvas from `video.videoWidth/videoHeight`, then start `setInterval(liveAnalyzeLoop, 1000)`
- [x] 3.3 Implement `liveAnalyzeLoop()`: skip if `liveBusy`; downscale current frame to ≤640px; POST `/api/analyze?light=true`; on success draw overlay + update metrics/list; clear `liveBusy` in `finally`
- [x] 3.4 Implement overlay drawing using the existing `drawLiveAnnotations(ctx, data, scale)`/`liveCategoryColor`, with `scale = overlayWidth / analyzedFrameWidth`; clear the overlay before redrawing
- [x] 3.5 Update `renderLiveResults` to fill metrics cards + Worker Compliance list from the latest response (reused for live)
- [x] 3.6 In `stopLiveCamera()`: `clearInterval`, stop tracks, clear the overlay, reset buttons/status

## 4. Tab Lifecycle (app.js)

- [x] 4.1 In the tab-switch handler: when leaving the Live panel clear the analysis timer (camera keeps running); when entering the Live panel with an active camera, restart the timer

## 5. Verification

- [x] 5.1 `node --check frontend/app.js` passes
- [x] 5.2 Manual check with running stack (`docker compose up`): start camera → overlay boxes appear within ~1–2s and refresh as the scene changes; metrics/list update automatically; Stop clears overlay; switching tabs pauses the loop and returning resumes it