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
from datetime import datetime, timedelta

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


def match_transitions_to_detections(transitions, rows, first_decision_index=None):
    """rows: chronological list of {"time", "estimated_room", "changed"} for
    ONE (mac, experiment_id, method) - caller guarantees sorted order and
    that all rows belong to the same experiment as `transitions`. "changed"
    must mean what decision_methods.py already means by it: "differs from
    this method's own previous decision" - required to tell a genuine
    reaction to the real transition apart from a room label that was
    already sitting there from before it (see premature_before_transition
    below - this is what a real, observed bug looked like: a method that
    switched rooms 4s too early got credited with a perfect latency=0
    confirmation once ground truth caught up, simply because nothing
    "changed" at that row - see CLAUDE.md-adjacent plan notes). Only 2
    callers exist (analyze_room_decisions.build_summary_rows via
    compute_ground_truth_metrics, statistical_analysis.compute_per_transition_results),
    both provide "changed" - this key is required, not optional.

    first_decision_index, when given, is this row list's OWN index (not a
    global one) of the method's very first-ever decision - it never counts
    as a genuine entry even if it happens to match, same "establishing the
    first decision isn't a reaction to anything" rule num_transitions/
    count_false_movements already apply.

    For each transition, returns:
        {"detected": bool, "latency_sec": float|None,
         "premature_before_transition": bool, "post_transition_confirmed": bool,
         "premature_lead_sec": float|None, "transition_status": str}

    premature_before_transition: estimated_room was ALREADY new_room on the
    last row strictly before t["time"] - exact string comparison, no
    tolerance of any kind.
    post_transition_confirmed: some row in [t["time"], window_end) is a
    GENUINE entry into new_room (estimated_room==new_room AND changed==True
    there, and not first_decision_index) - a row that only continues an
    already-established state (changed==False) never counts on its own,
    even though its estimated_room already matches. This is independent of
    premature_before_transition: a method can leave the target room after
    the real transition and genuinely re-enter it later, which must still
    count here.
    premature_lead_sec: only set when premature_before_transition - exact
    backward search (no tolerance) to the nearest changed==True row that
    started the still-ongoing streak sitting in new_room at t["time"].
    detected == post_transition_confirmed; latency_sec is only ever
    measured from t["time"] to a genuine entry, never from an earlier
    premature one. transition_status is a convenience label derived from
    the two booleans, never computed independently of them:
        (False, True)  -> "confirmed_after_transition"
        (False, False) -> "missed_transition"
        (True,  True)  -> "premature_then_confirmed"
        (True,  False) -> "premature_no_confirmation"
    """
    results = []
    for t in transitions:
        pre_transition_room = None
        pre_transition_index = None
        for i, row in enumerate(rows):
            if row["time"] >= t["time"]:
                break
            pre_transition_room = row["estimated_room"]
            pre_transition_index = i
        premature_before_transition = pre_transition_room == t["new_room"]

        premature_lead_sec = None
        if premature_before_transition:
            entry_index = pre_transition_index
            for i in range(pre_transition_index, -1, -1):
                if rows[i]["estimated_room"] != t["new_room"]:
                    break
                entry_index = i
                if rows[i].get("changed"):
                    break
            premature_lead_sec = (_parse(t["time"]) - _parse(rows[entry_index]["time"])).total_seconds()

        post_transition_confirmed = False
        latency = None
        for i, row in enumerate(rows):
            if row["time"] < t["time"]:
                continue
            if t["window_end"] is not None and row["time"] >= t["window_end"]:
                break  # past this transition's window - never confirmed
            if row["estimated_room"] == t["new_room"] and row.get("changed") and i != first_decision_index:
                post_transition_confirmed = True
                latency = (_parse(row["time"]) - _parse(t["time"])).total_seconds()
                break

        if premature_before_transition:
            status = "premature_then_confirmed" if post_transition_confirmed else "premature_no_confirmation"
        else:
            status = "confirmed_after_transition" if post_transition_confirmed else "missed_transition"

        results.append({
            "detected": post_transition_confirmed,
            "latency_sec": latency,
            "premature_before_transition": premature_before_transition,
            "post_transition_confirmed": post_transition_confirmed,
            "premature_lead_sec": premature_lead_sec,
            "transition_status": status,
        })
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

    Returns the summary columns (accuracy/movements/latency/premature-
    transition counts) plus "transition_details" (a list, see below -
    callers building a decision_summary row must pop it first, it isn't one
    of the scalar columns that CSV holds).
    pct_time_unknown_or_transition is always computed (it only depends on
    the method's own decided_room being None, not on ground truth). If NO
    row has ground truth coverage, every other field is None
    ("unmeasurable", distinct from a genuine zero - e.g.
    false_movements_per_hour=0.0 would misleadingly read as "measured zero
    false movements") and transition_details is an empty list (consistent
    shape in both branches, never a missing key).

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
            "num_confirmed_after_transition": None,
            "num_premature_before_transition": None,
            "num_premature_without_confirmation": None,
            "num_false_movements": None,
            "false_movements_per_hour": None,
            "latency_median_sec": None,
            "latency_p95_sec": None,
            "latency_iqr_sec": None,
            "latency_min_sec": None,
            "latency_max_sec": None,
            "pct_time_unknown_or_transition": pct_time_unknown_or_transition,
            "transition_details": [],
        }

    accuracy = sum(1 for r in gt_rows if r["estimated_room"] == r["ground_truth_room"]) / len(gt_rows)
    num_false_movements = count_false_movements(rows, first_decision_index)

    # Indexed so a GLOBAL first_decision_index can be translated into each
    # experiment group's OWN local index below - by_experiment splits rows
    # into per-group lists, so position i within exp_rows is generally NOT
    # the same as position i within the full rows list (only coincides when
    # there's a single experiment_id, the common case, but "all experiments"
    # mode genuinely interleaves several - see this function's own docstring).
    by_experiment = {}
    for i, r in enumerate(rows):
        by_experiment.setdefault(r.get("experiment_id"), []).append((i, r))

    num_true_movements = 0
    num_missed = 0
    num_confirmed_after_transition = 0
    num_premature_before_transition = 0
    num_premature_without_confirmation = 0
    all_latencies = []
    total_hours = 0.0
    transition_details = []

    for experiment_id, indexed_exp_rows in by_experiment.items():
        exp_rows = [r for _, r in indexed_exp_rows]
        local_first_decision_index = None
        if first_decision_index is not None:
            for local_i, (global_i, _) in enumerate(indexed_exp_rows):
                if global_i == first_decision_index:
                    local_first_decision_index = local_i
                    break
        intervals = gt_intervals_by_experiment.get(experiment_id, [])
        if len(intervals) >= 2:
            transitions = extract_true_transitions(intervals)
            detections = match_transitions_to_detections(transitions, exp_rows, first_decision_index=local_first_decision_index)
            num_true_movements += len(transitions)
            for transition_index, (t, d) in enumerate(zip(transitions, detections)):
                # Branch explicitly on the two dimensions, never on "detected"
                # alone - premature_no_confirmation also has detected=False
                # now, and must never be folded into num_missed by accident.
                if d["post_transition_confirmed"]:
                    num_confirmed_after_transition += 1
                    all_latencies.append(d["latency_sec"])
                    confirmation_time = (_parse(t["time"]) + timedelta(seconds=d["latency_sec"])).strftime(TIME_FORMAT)
                elif d["premature_before_transition"]:
                    num_premature_without_confirmation += 1
                    confirmation_time = None
                else:
                    num_missed += 1
                    confirmation_time = None
                if d["premature_before_transition"]:
                    num_premature_before_transition += 1
                transition_details.append({
                    "experiment_id": experiment_id,
                    "transition_index": transition_index,
                    "new_room": t["new_room"],
                    "transition_time": t["time"],
                    "detected": d["detected"],
                    "latency_sec": d["latency_sec"],
                    "confirmation_time": confirmation_time,
                    "premature_before_transition": d["premature_before_transition"],
                    "post_transition_confirmed": d["post_transition_confirmed"],
                    "premature_lead_sec": d["premature_lead_sec"],
                    "transition_status": d["transition_status"],
                })
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
        "num_confirmed_after_transition": num_confirmed_after_transition,
        "num_premature_before_transition": num_premature_before_transition,
        "num_premature_without_confirmation": num_premature_without_confirmation,
        "num_false_movements": num_false_movements,
        "false_movements_per_hour": false_movements_per_hour,
        "latency_median_sec": latency_summary["median"],
        "latency_p95_sec": latency_summary["p95"],
        "latency_iqr_sec": latency_summary["iqr"],
        "latency_min_sec": latency_summary["min"],
        "latency_max_sec": latency_summary["max"],
        "pct_time_unknown_or_transition": pct_time_unknown_or_transition,
        # Per-transition detail (real Mongo-sourced transition instant +
        # each method's confirmation instant, not reconstructed from a CSV
        # column change) - consumed by analyze_room_decisions.build_summary_rows
        # to write transition_latencies_<label>.csv, then by
        # generate_report_figures.py's latency-boxplot and rssi-timeline
        # figures. Callers that only want the decision_summary row MUST pop
        # this key first (see build_summary_rows) - it isn't one of the 12
        # scalar columns that CSV has always had.
        "transition_details": transition_details,
    }
