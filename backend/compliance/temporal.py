"""
Temporal Compliance Engine
--------------------------
Aggregates per-frame compliance records (with persistent track IDs) into a
per-person time-based report. 

This module is only used by the video endpoint. Image analysis uses the
simpler `rules.py` directly.
"""

from typing import Dict, List

# Tracks visible for less than this duration are almost certainly ghost tracks
# born from ID fragmentation (tracker briefly loses a person and re-acquires them
# with a new ID). Real workers and even briefly passing persons are visible for
# at least this long. Adjust if your videos have very fast walk-throughs.
MIN_TRACK_SECONDS = 2.0


def build_temporal_report(
    per_frame_results: List[List[Dict]],
    fps: float,
    min_track_seconds: float = MIN_TRACK_SECONDS,
) -> List[Dict]:
    """
    Aggregate compliance data across all frames for each tracked person.

    Args:
        per_frame_results: A list of frames. Each frame is a list of
                           per-person compliance dicts that include:
                           - "track_id"     (int)
                           - "compliance_status" ("Compliant" | "Non-compliant")
                           - "missing_ppe"  (list[str])
                           - "detected_ppe" (list[str])
                           - "risk_level"   (str)
        fps: Video frame rate, used to convert frame counts to seconds.

    Returns:
        A list of per-person summary dicts sorted by track_id.
    """
    # track_id -> {compliant_frames, violation_frames, missing_ppe_counts}
    state: Dict[int, Dict] = {}

    for frame in per_frame_results:
        for person in frame:
            tid = person["track_id"]
            if tid not in state:
                state[tid] = {
                    "compliant_frames": 0,
                    "violation_frames": 0,
                    "missing_ppe_tally": {},  # ppe_item -> count of frames missing
                    "detected_ppe_tally": {},
                }
            s = state[tid]
            is_compliant = person["compliance_status"] == "Compliant"

            if is_compliant:
                s["compliant_frames"] += 1
            else:
                s["violation_frames"] += 1

            for item in person.get("missing_ppe", []):
                s["missing_ppe_tally"][item] = s["missing_ppe_tally"].get(item, 0) + 1

            for item in person.get("detected_ppe", []):
                s["detected_ppe_tally"][item] = s["detected_ppe_tally"].get(item, 0) + 1

    results = []
    min_frames = int(min_track_seconds * fps)

    for track_id, s in sorted(state.items()):
        total_frames = s["compliant_frames"] + s["violation_frames"]

        # Filter out ghost tracks from ID fragmentation — they are too short-lived
        # to be real persons and only clutter the report.
        if total_frames < min_frames:
            continue

        total_seconds = round(total_frames / fps, 1) if fps > 0 else 0.0
        compliant_seconds = round(s["compliant_frames"] / fps, 1) if fps > 0 else 0.0
        violation_seconds = round(s["violation_frames"] / fps, 1) if fps > 0 else 0.0
        compliance_rate = round(s["compliant_frames"] / total_frames * 100, 1) if total_frames > 0 else 0.0

        # Primary violation = the PPE item missing in the most frames
        primary_violation = None
        if s["missing_ppe_tally"]:
            primary_violation = max(s["missing_ppe_tally"], key=s["missing_ppe_tally"].get)

        results.append({
            "track_id": track_id,
            "total_seconds_visible": total_seconds,
            "compliant_seconds": compliant_seconds,
            "violation_seconds": violation_seconds,
            "compliance_rate": compliance_rate,
            "primary_violation": primary_violation,
            "missing_ppe_tally": s["missing_ppe_tally"],
            "detected_ppe_tally": s["detected_ppe_tally"],
        })

    return results
