"""
Pure metric-computation functions comparing ground-truth room intervals
against a single decision method's estimated room, per (mac, method).
Mirrors decision_methods.py's architecture: stdlib-only, no Mongo/pandas
required internally, unit-testable with hand-built lists.

The one deliberate exception to the rest of this codebase's "plain string
comparison, never parse datetimes" convention: latency-in-seconds and
elapsed-hours genuinely require datetime arithmetic, not just ordering, so
datetime.strptime is used narrowly here for those two computations only.
"""

import statistics
from datetime import datetime

TIME_FORMAT = "%Y-%m-%d %H:%M:%S"


def _parse(time_str):
    return datetime.strptime(time_str, TIME_FORMAT)


def extract_true_transitions(intervals):
    """intervals: one experiment_id's list of {"room","start","end"} from
    analyze_room_decisions.build_ground_truth_intervals (already
    chronologically ordered). Returns real room-to-room boundaries only:
    [{"time", "new_room", "window_end"}].

    A boundary where the room doesn't actually change (a duplicate or
    defensive same-room re-tap) is skipped - and, importantly, such a
    re-tap must never truncate the PRECEDING transition's detection
    window either: window_end is found by walking forward past any number
    of same-room intervals to the next genuinely different room's start
    (or None if no such interval exists - the window stays open-ended).
    """
    transitions = []
    for i in range(1, len(intervals)):
        prev_room = intervals[i - 1]["room"]
        this_room = intervals[i]["room"]
        if this_room == prev_room:
            continue  # not a real transition (duplicate/defensive tap)

        window_end = None
        for j in range(i + 1, len(intervals)):
            if intervals[j]["room"] != this_room:
                window_end = intervals[j]["start"]
                break

        transitions.append({
            "time": intervals[i]["start"],
            "new_room": this_room,
            "window_end": window_end,
        })
    return transitions


def match_transitions_to_detections(transitions, rows):
    """rows: chronological list of {"time", "estimated_room"} for ONE
    (mac, experiment_id, method) - caller guarantees sorted order and that
    all rows belong to the same experiment as `transitions`.

    For each transition, finds the first row at/after its time (and before
    window_end, if set) whose estimated_room matches the transition's
    new_room. Returns one dict per transition, same order:
        {"detected": bool, "latency_sec": float|None}
    Latency can never be negative by construction (only rows with
    row["time"] >= transition["time"] are ever considered a match).
    """
    results = []
    for t in transitions:
        detected = False
        latency = None
        for row in rows:
            if row["time"] < t["time"]:
                continue
            if t["window_end"] is not None and row["time"] >= t["window_end"]:
                break  # past this transition's window - never detected
            if row["estimated_room"] == t["new_room"]:
                detected = True
                latency = (_parse(row["time"]) - _parse(t["time"])).total_seconds()
                break
        results.append({"detected": detected, "latency_sec": latency})
    return results


def summarize_latencies(latency_values):
    """{"median","p95","iqr","min","max"} - all None if the list is empty.
    statistics.quantiles handles 1-2 sample lists gracefully (verified: no
    StatisticsError, degenerates sensibly), so no hand-rolled percentile
    logic or special-casing is needed beyond the empty-list guard."""
    if not latency_values:
        return {"median": None, "p95": None, "iqr": None, "min": None, "max": None}

    p95 = statistics.quantiles(latency_values, n=100, method="inclusive")[94]
    q1, _, q3 = statistics.quantiles(latency_values, n=4, method="inclusive")
    return {
        "median": statistics.median(latency_values),
        "p95": p95,
        "iqr": q3 - q1,
        "min": min(latency_values),
        "max": max(latency_values),
    }


def count_false_movements(rows, first_decision_index):
    """rows: full chronological list for ONE (mac, method), each with
    {"changed", "ground_truth_room", "estimated_room"}.

    A changed=True row (excluding rows[first_decision_index] - the same
    "establishing the first decision isn't a transition" exclusion already
    used by analyze_room_decisions.py's num_transitions, passed in by
    index so the two rules can never drift apart) counts as a false
    movement if ground truth covers that row AND disagrees with it.
    Rows without ground truth coverage can't be judged, so they're
    skipped rather than counted as false.
    """
    count = 0
    for i, row in enumerate(rows):
        if i == first_decision_index:
            continue
        if not row.get("changed"):
            continue
        gt_room = row.get("ground_truth_room")
        if gt_room is None:
            continue
        if row.get("estimated_room") != gt_room:
            count += 1
    return count


def build_confusion_counts(rows, unknown_label="desconhecida"):
    """rows: [{"ground_truth_room" (caller guarantees not None), "estimated_room"}]
    for ONE (mac, method). Maps a None estimated_room to unknown_label
    BEFORE counting - never rely on pandas' default NaN-dropping groupby,
    which would silently drop persistence's warm-up rows instead of
    surfacing them as the "desconhecida" column the guiao's own example
    confusion matrix expects.

    Returns a sorted list: [{"real_room", "estimated_room", "count"}].
    """
    counts = {}
    for row in rows:
        real_room = row["ground_truth_room"]
        estimated_room = row.get("estimated_room")
        if estimated_room is None:
            estimated_room = unknown_label
        key = (real_room, estimated_room)
        counts[key] = counts.get(key, 0) + 1

    return sorted(
        ({"real_room": r, "estimated_room": e, "count": c} for (r, e), c in counts.items()),
        key=lambda d: (d["real_room"], d["estimated_room"]),
    )


def compute_ground_truth_metrics(rows, gt_intervals_by_experiment, first_decision_index):
    """rows: full chronological list for ONE (mac, method), each with
    {"time", "experiment_id", "ground_truth_room", "estimated_room", "changed"}.

    Returns the 12 summary columns. pct_time_unknown_or_transition is
    always computed (it only depends on the method's own decided_room
    being None, not on ground truth). If NO row has ground truth coverage,
    every other field is None ("unmeasurable", distinct from a genuine
    zero - e.g. false_movements_per_hour=0.0 would misleadingly read as
    "measured zero false movements").

    "All experiments" mode (--experiment-id omitted) can interleave one
    mac's rows across several unrelated trials - transitions/latency/
    elapsed-hours are computed PER experiment_id group, then summed
    (counts, hours) or concatenated (latencies) across groups, so a false
    movement rate is never diluted by another trial's unrelated duration,
    and a transition search never bleeds into a different trial's rows.
    This degenerates to the ordinary single-experiment computation
    whenever only one experiment_id is present, the common case.
    """
    total = len(rows)
    num_unknown = sum(1 for r in rows if r.get("estimated_room") is None)
    pct_time_unknown_or_transition = (num_unknown / total * 100.0) if total else None

    gt_rows = [r for r in rows if r.get("ground_truth_room") is not None]
    if not gt_rows:
        return {
            "accuracy": None,
            "num_true_movements": None,
            "num_missed_movements": None,
            "missed_movement_rate": None,
            "num_false_movements": None,
            "false_movements_per_hour": None,
            "latency_median_sec": None,
            "latency_p95_sec": None,
            "latency_iqr_sec": None,
            "latency_min_sec": None,
            "latency_max_sec": None,
            "pct_time_unknown_or_transition": pct_time_unknown_or_transition,
        }

    accuracy = sum(1 for r in gt_rows if r["estimated_room"] == r["ground_truth_room"]) / len(gt_rows)
    num_false_movements = count_false_movements(rows, first_decision_index)

    by_experiment = {}
    for r in rows:
        by_experiment.setdefault(r.get("experiment_id"), []).append(r)

    num_true_movements = 0
    num_missed = 0
    all_latencies = []
    total_hours = 0.0

    for experiment_id, exp_rows in by_experiment.items():
        intervals = gt_intervals_by_experiment.get(experiment_id, [])
        if len(intervals) >= 2:
            transitions = extract_true_transitions(intervals)
            detections = match_transitions_to_detections(transitions, exp_rows)
            num_true_movements += len(transitions)
            for d in detections:
                if d["detected"]:
                    all_latencies.append(d["latency_sec"])
                else:
                    num_missed += 1
        if exp_rows:
            elapsed_hours = (_parse(exp_rows[-1]["time"]) - _parse(exp_rows[0]["time"])).total_seconds() / 3600.0
            total_hours += elapsed_hours

    missed_movement_rate = (num_missed / num_true_movements) if num_true_movements else None
    false_movements_per_hour = (num_false_movements / total_hours) if total_hours > 0 else None
    latency_summary = summarize_latencies(all_latencies)

    return {
        "accuracy": accuracy,
        "num_true_movements": num_true_movements,
        "num_missed_movements": num_missed,
        "missed_movement_rate": missed_movement_rate,
        "num_false_movements": num_false_movements,
        "false_movements_per_hour": false_movements_per_hour,
        "latency_median_sec": latency_summary["median"],
        "latency_p95_sec": latency_summary["p95"],
        "latency_iqr_sec": latency_summary["iqr"],
        "latency_min_sec": latency_summary["min"],
        "latency_max_sec": latency_summary["max"],
        "pct_time_unknown_or_transition": pct_time_unknown_or_transition,
    }
