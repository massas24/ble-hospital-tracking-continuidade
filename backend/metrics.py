"""
Cálculo das métricas por (mac, método), comparando os intervalos de ground
truth com a sala estimada por cada método de decisão. Sem dependências
externas (só biblioteca padrão), como decision_methods.py.

Exceção à convenção de comparar tempos como strings: a latência em segundos
e as horas decorridas precisam de aritmética de datas, por isso só aqui se
usa datetime.strptime.
"""

import statistics
from datetime import datetime, timedelta

TIME_FORMAT = "%Y-%m-%d %H:%M:%S"


def _parse(time_str):
    return datetime.strptime(time_str, TIME_FORMAT)


def extract_true_transitions(intervals):
    """Extrai as transições reais de sala de um experiment_id.

    intervals: lista ordenada de {"room", "start", "end"}.
    Devolve [{"time", "new_room", "window_end"}].

    Uma marcação repetida na mesma sala não é transição e não encurta a
    janela da transição anterior: window_end é o início do próximo intervalo
    com sala diferente, ou None se não existir (janela aberta).
    """
    transitions = []
    for i in range(1, len(intervals)):
        prev_room = intervals[i - 1]["room"]
        this_room = intervals[i]["room"]
        if this_room == prev_room:
            continue  # marcação repetida na mesma sala

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
    """Classifica cada transição real face às decisões de um método.

    rows: lista cronológica de {"time", "estimated_room", "changed"} para um
    (mac, experiment_id, método). "changed" é obrigatório: distingue uma
    entrada genuína na sala de um rótulo que já lá estava antes da transição.
    first_decision_index: índice local da primeira decisão do método, que
    nunca conta como reação a uma transição.

    Duas dimensões independentes:
    - premature_before_transition: a última linha estritamente anterior a
      t["time"] já tinha new_room;
    - post_transition_confirmed: existe em [t["time"], window_end) uma linha
      com estimated_room == new_room e changed == True.

    detected é igual a post_transition_confirmed; a latência mede-se só até
    uma entrada genuína. transition_status deriva das duas dimensões:
        (False, True)  -> "confirmed_after_transition"
        (False, False) -> "missed_transition"
        (True,  True)  -> "premature_then_confirmed"
        (True,  False) -> "premature_no_confirmation"
    premature_lead_sec: antecedência da entrada prematura, procurada para trás
    até à linha changed == True que iniciou a sequência em new_room.
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
                break  # fora da janela desta transição
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
    """Mediana, p95, IQR, mínimo e máximo; tudo None se a lista estiver vazia."""
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
    """Conta as mudanças de decisão (changed == True) em que a sala estimada
    difere do ground truth. Exclui a primeira decisão e as linhas sem ground
    truth, que não podem ser avaliadas.
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
    """Contagens da matriz de confusão para um (mac, método).

    Uma sala estimada None conta como unknown_label ("desconhecida"), para
    que as linhas de aquecimento da persistência apareçam na matriz em vez
    de serem descartadas. Devolve [{"real_room", "estimated_room", "count"}].
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
    """Métricas de um (mac, método) face ao ground truth.

    rows: lista cronológica com {"time", "experiment_id", "ground_truth_room",
    "estimated_room", "changed"}.

    pct_time_unknown_or_transition calcula-se sempre. Sem nenhuma linha com
    ground truth, as restantes métricas ficam None (não mensurável, diferente
    de zero) e transition_details fica vazio.

    Com vários experiment_id, transições, latências e horas calculam-se por
    ensaio e só depois se agregam, para que a duração de um ensaio não dilua
    a taxa de falsos movimentos de outro. "transition_details" alimenta
    transition_latencies_<label>.csv e tem de ser retirado antes de escrever
    a linha de decision_summary.
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

    # Guarda o índice global para traduzir first_decision_index para o
    # índice local de cada ensaio.
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
                # Decide pelas duas dimensões: premature_no_confirmation também
                # tem detected=False e não pode contar como movimento perdido.
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
        # Detalhe por transição (ver docstring).
        "transition_details": transition_details,
    }
