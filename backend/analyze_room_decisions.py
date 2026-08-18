"""
Comparação offline de quatro configurações de decisão de ambiente progressivamente mais rigorosas
reproduzidas sobre as deteções BLE em bruto já armazenadas por backend/app.py na
coleção raw_detections do MongoDB:

1. linha de base - a leitura mais recente ganha, sem filtragem
2. mediana - RSSI mediano numa janela deslizante
3. histerese mediana - + margem necessária para mudar de ambiente
4. persistência de histerese mediana - + N leituras consecutivas para confirmar

Cada uma é uma versão progressivamente mais rigorosa da anterior (ver
decision_methods.py), e não uma alternativa independente - portanto, em vez de uma
matriz de concordância de todos os pares, cada estágio é comparado com o estágio final
(mais filtrado) através de agree_rate_vs_final.

Nenhum valor de referência é aqui utilizado - isto compara as quatro configurações
entre si (taxa de concordância, número de transições), e não com um
ambiente conhecido e correto. Esta comparação pode ser adicionada posteriormente, após a definição do valor de referência. verdade
Os dados existem.

Requer pandas e matplotlib para além dos requisitos básicos do backend:

pip instalar -r requisitos.txt -r requisitos-análise.txt

Uso:

python analyze_room_decisions.py --mac aa:bb:cc:dd:ee:01 --experiment-id test1

python analyze_room_decisions.py # todas as experiências, todos os macs

python analyze_room_decisions.py --no-plots # apenas CSVs, ignorar matplotlib
"""

import argparse
import json
import os
from datetime import datetime

import pandas as pd
import matplotlib.pyplot as plt
from pymongo import MongoClient

import decision_methods as dm
import metrics

METHOD_COLORS = {
    "baseline": "#8a4fd6",
    "median": "#eb6834",
    "median_hysteresis": "#2a78d6",
    "median_hysteresis_persistence": "#1baf7a",
}
METHODS = [
    ("baseline", "baseline_room", "baseline_changed"),
    ("median", "median_room", "median_changed"),
    ("median_hysteresis", "median_hysteresis_room", "median_hysteresis_changed"),
    ("median_hysteresis_persistence", "median_hysteresis_persistence_room", "median_hysteresis_persistence_changed"),
]
FINAL_METHOD = "median_hysteresis_persistence"

# Shown once in run_metadata whenever at least one (mac, experiment_id)
# group used clock_source="node" - see _group_uses_node_time's docstring
# for the full reasoning. Kept as a complete, citable sentence rather than
# a bare boolean, since this is a real methodological caveat for whatever
# report cites these numbers, not just an internal implementation note.
NODE_TIME_CLOCK_WARNING = (
    "Pelo menos um grupo (mac, experiment_id) nesta corrida usou node_time "
    "(relógio do próprio nó, sincronizado por NTP) em vez da hora de "
    "receção do servidor. Isto muda uma propriedade importante: quando "
    "deteção E ground truth vêm do MESMO relógio (servidor), um desvio "
    "desse relógio cancela-se na subtração e a latência sai correta mesmo "
    "que o relógio esteja errado em termos absolutos. Ao misturar node_time "
    "(nó) com o ground truth (sempre servidor), esse cancelamento deixa de "
    "acontecer - um desvio do relógio do SERVIDOR entra diretamente, sem se "
    "cancelar, em todas as latências destes grupos. As latências destes "
    "grupos só são fiáveis se o relógio do servidor também estiver "
    "corretamente sincronizado - não verificado por este código. Ver README."
)


def normalize_mac(mac):
    return mac.replace("-", ":").lower().strip().replace('"', "")


def load_detections_by_mac(collection, experiment_id, macs):
    query = {}
    if experiment_id is not None:
        query["experiment_id"] = experiment_id

    if macs:
        target_macs = macs
    else:
        target_macs = collection.distinct("mac", query)

    data_by_mac = {}
    for mac in target_macs:
        mac_query = dict(query)
        mac_query["mac"] = mac
        # Sort by server time then _id: batch_id is a random uuid4 (not a
        # chronological key), while Mongo's ObjectId is monotonically
        # increasing at insertion time, giving a true fine-grained tiebreaker
        # for detections that share the same (1-second-resolution) "time".
        docs = list(
            collection.find(
                mac_query,
                {"mac": 1, "esp_id": 1, "room": 1, "rssi": 1, "time": 1,
                 "node_time": 1, "node_seq": 1, "boot_id": 1,
                 "batch_id": 1, "experiment_id": 1},
            ).sort([("time", 1), ("_id", 1)])
        )
        data_by_mac[mac] = docs
    return data_by_mac


def load_ground_truth_by_mac(collection, experiment_id, macs):
    """Mesmo formato de consulta que o load_detections_by_mac, mas contra a
    coleção ground_truth - eventos "o beacon X entrou na sala Y à hora T" 
    selecionados manualmente, uma linha por seleção de campo."""
    query = {}
    if experiment_id is not None:
        query["experiment_id"] = experiment_id

    data_by_mac = {}
    for mac in macs:
        mac_query = dict(query)
        mac_query["mac"] = mac
        events = list(
            collection.find(
                mac_query, {"experiment_id": 1, "mac": 1, "room": 1, "time": 1, "scenario": 1}
            ).sort([("time", 1), ("_id", 1)])
        )
        data_by_mac[mac] = events
    return data_by_mac


def build_ground_truth_intervals(events):
    """Emparelha eventos consecutivos de referência em intervalos: intervalo_i =
    [evento_i.tempo, evento_{i+1}.tempo], com o intervalo do último evento deixado
    em aberto (fim=Nenhum). Agrupa por experiment_id FIRST - essencial, uma vez que
    dois ensaios diferentes reutilizando o mesmo MAC nunca devem ter os seus eventos
    emparelhados entre experiências. Retorna {experiment_id: [intervalo, ...]}."""
    by_experiment = {}
    for ev in events:
        by_experiment.setdefault(ev.get("experiment_id"), []).append(ev)

    intervals_by_experiment = {}
    for experiment_id, evs in by_experiment.items():
        intervals = []
        for i, ev in enumerate(evs):
            end = evs[i + 1]["time"] if i + 1 < len(evs) else None
            intervals.append({"room": ev["room"], "scenario": ev.get("scenario"), "start": ev["time"], "end": end})
        intervals_by_experiment[experiment_id] = intervals
    return intervals_by_experiment


def lookup_ground_truth_interval(intervals, time_str):
    """Comparação de strings simples - segura porque "%Y-%m-%d %H:%M:%S" é um
    formato de largura fixa, preenchido com zeros, que classifica/compara corretamente como strings simples,
    de forma consistente com a forma como este ficheiro já evita a análise de data e hora
    noutros lugares. Devolve o INTERVALO completo ({"room","scenario","start","end"})
    que cobre time_str, ou None se estiver fora de todos os intervalos (por ex.
    antes da primeira marcação, ou sem ground truth nenhum) - devolver o
    intervalo inteiro, em vez de só a sala, serve room E scenario a partir
    de UMA única passagem O(n), em vez de dois varrimentos separados."""
    if not time_str:
        return None
    for interval in intervals:
        if interval["start"] <= time_str and (interval["end"] is None or time_str < interval["end"]):
            return interval
    return None


def _group_uses_node_time(docs):
    """True só se TODAS as deteções deste grupo (mac, experiment_id)
    tiverem node_time E vierem todas do MESMO esp_id - duas condições, não
    uma. Decisão por CONJUNTO, nunca por linha: se node_time faltar nalguma
    linha, o grupo inteiro recua para a hora de receção.

    Porquê também exigir um único esp_id (não só node_time em todas as
    linhas): a ordem de base do detail_df continua sempre por hora de
    receção (nunca por node_time), e é essa MESMA ordem que alimenta tanto
    decision_methods.py (changed/decisões) como, a seguir, o metrics.py
    (transições/latências) - as duas têm de usar a mesma ordem, ou
    "changed" deixa de corresponder à linha anterior real. Isso só é
    seguro quando a ordem de receção e a ordem do próprio nó COINCIDEM -
    garantido para um único esp_id (um dispositivo só gera e envia as
    suas leituras em sequência), não garantido quando vários nós reportam
    o mesmo beacon com atrasos de rede diferentes. Alargar a vários nós
    exigiria também mudar a ordem que alimenta decision_methods.py - fora
    de âmbito aqui, fica só a acumular node_time/node_seq/boot_id para
    esse trabalho futuro.

    Nota sobre validade adicional: comparar o relógio do nó com o do
    ground_truth (sempre o relógio do servidor) só é correto se o próprio
    relógio do SERVIDOR também estiver certo - não verificado nem
    garantido por este código (ver limitação no README, e
    NODE_TIME_CLOCK_WARNING em run_metadata)."""
    if not docs:
        return False
    if not all(d.get("node_time") is not None for d in docs):
        return False
    return len({d.get("esp_id") for d in docs}) == 1


def build_detail_dataframe(mac, docs, hysteresis_margin, median_window, persistence_streak, gt_intervals_by_experiment):
    baseline = dm.decide_baseline(docs)
    median = dm.decide_median(docs, window=median_window)
    med_hyst = dm.decide_median_hysteresis(docs, window=median_window, margin=hysteresis_margin)
    med_hyst_pers = dm.decide_median_hysteresis_persistence(
        docs, window=median_window, margin=hysteresis_margin, streak=persistence_streak
    )

    def agree(a, b):
        return a is not None and b is not None and a == b

    # Escolha do relógio por CONJUNTO (mac, experiment_id), pré-calculada
    # antes do ciclo principal - ver _group_uses_node_time.
    docs_by_experiment = {}
    for doc in docs:
        docs_by_experiment.setdefault(doc.get("experiment_id"), []).append(doc)
    uses_node_time_by_experiment = {
        exp_id: _group_uses_node_time(exp_docs) for exp_id, exp_docs in docs_by_experiment.items()
    }

    rows = []
    for doc, b, m, mh, mhp in zip(docs, baseline, median, med_hyst, med_hyst_pers):
        b_room, m_room, mh_room, mhp_room = (
            b["decided_room"], m["decided_room"], mh["decided_room"], mhp["decided_room"],
        )
        experiment_id = doc.get("experiment_id")
        uses_node_time = uses_node_time_by_experiment.get(experiment_id, False)
        effective_time = doc.get("node_time") if uses_node_time else doc.get("time")
        # Looked up per-row using THIS row's own experiment_id, not the CLI
        # filter - in "all experiments" mode a single mac's docs can span
        # more than one trial.
        intervals = gt_intervals_by_experiment.get(experiment_id, [])
        gt_interval = lookup_ground_truth_interval(intervals, effective_time)
        ground_truth_room = gt_interval["room"] if gt_interval else None
        ground_truth_scenario = gt_interval["scenario"] if gt_interval else None
        rows.append({
            "time": doc.get("time"),
            "node_time": doc.get("node_time"),
            "node_seq": doc.get("node_seq"),
            "boot_id": doc.get("boot_id"),
            "effective_time": effective_time,
            "clock_source": "node" if uses_node_time else "server",
            "mac": mac,
            "esp_id": doc.get("esp_id", ""),
            "batch_id": doc.get("batch_id", ""),
            "experiment_id": experiment_id,
            "raw_room": doc.get("room"),
            "raw_rssi": doc.get("rssi"),
            "ground_truth_room": ground_truth_room,
            "ground_truth_scenario": ground_truth_scenario,
            "baseline_room": b_room,
            "baseline_changed": b["changed"],
            "median_room": m_room,
            "median_changed": m["changed"],
            "median_hysteresis_room": mh_room,
            "median_hysteresis_changed": mh["changed"],
            "median_hysteresis_rejected": mh["rejected"],
            "median_hysteresis_persistence_room": mhp_room,
            "median_hysteresis_persistence_changed": mhp["changed"],
            "baseline_agrees_with_final": agree(b_room, mhp_room),
            "median_agrees_with_final": agree(m_room, mhp_room),
            "median_hysteresis_agrees_with_final": agree(mh_room, mhp_room),
        })

    return pd.DataFrame(rows).reset_index(drop=True)


def _records_with_none(df):
    """df.to_dict("records") followed by a real NaN->None pass. Doing this
    BEFORE to_dict (e.g. df.where(df.notna(), None)) does not work for a
    float64-dtype column: pandas silently coerces the replacement None
    right back into NaN to preserve the column's numeric dtype, so a
    method's room column that happens to be entirely None over some slice
    (e.g. a persistence-only warm-up subset) would still surface as float
    NaN, not Python None, downstream - breaking "is None" checks in
    metrics.py and unorderable sort comparisons in build_confusion_counts.
    Converting after to_dict (plain Python dicts, no dtype to preserve) is
    the reliable way to do this instead."""
    records = df.to_dict("records")
    for record in records:
        for key, value in record.items():
            if isinstance(value, float) and pd.isna(value):
                record[key] = None
    return records


def build_summary_rows(mac, detail_df, gt_intervals_by_experiment):
    """Returns (summary_rows, transition_latency_rows). transition_latency_rows
    is real-Mongo-sourced per-transition detail (transition instant + each
    method's confirmation instant, never reconstructed from a CSV column
    change - no BASELINE_LATENCY_CAVEAT-style artifact), popped out of
    metrics.compute_ground_truth_metrics's return dict before it's spread
    into a summary row - decision_summary_<label>.csv's columns are
    unaffected by this."""
    summary_rows = []
    transition_latency_rows = []

    final_room_col = next(rc for name, rc, _ in METHODS if name == FINAL_METHOD)
    final_rooms = detail_df[final_room_col]

    for method, room_col, changed_col in METHODS:
        rooms = detail_df[room_col]
        changed = detail_df[changed_col]
        decided_mask = rooms.notna()

        num_decided = int(decided_mask.sum())
        first_decision_index = int(decided_mask.idxmax()) if num_decided > 0 else None

        # "changed" marks any row whose decision differs from the previous
        # row's, including the very first decision being "established" out
        # of None. num_transitions excludes that first establishment, since
        # it isn't a transition between two known rooms.
        num_changed_true = int(changed.sum())
        num_transitions = max(0, num_changed_true - (1 if num_decided > 0 else 0))

        # Agreement is measured against the final (most-filtered) stage in
        # the chain, not an all-pairs matrix - the four configurations are
        # progressive refinements of each other, not independent alternatives.
        both_decided = decided_mask & final_rooms.notna()
        if method == FINAL_METHOD:
            agree_rate_vs_final = 1.0 if both_decided.sum() > 0 else None
        elif both_decided.sum() > 0:
            agree_rate_vs_final = float((rooms[both_decided] == final_rooms[both_decided]).mean())
        else:
            agree_rate_vs_final = None

        # Ground-truth-based metrics (accuracy, false/missed movements,
        # confirmation latency, % time unknown/transition) - see metrics.py.
        # Reuses first_decision_index computed above so the "establishing
        # the first decision isn't a movement" rule can never drift between
        # num_transitions and the false-movement count.
        # Uses effective_time (node clock when the whole group qualifies,
        # else receipt time - see _group_uses_node_time), renamed back to
        # "time" for metrics.py. No reordering needed: _group_uses_node_time
        # already guarantees receipt order and node order coincide whenever
        # clock_source="node", so this stays in detail_df's own row order,
        # the same order decision_methods.py already processed.
        method_rows = detail_df[["effective_time", "experiment_id", "ground_truth_room", room_col, changed_col]]
        method_rows = method_rows.rename(columns={"effective_time": "time", room_col: "estimated_room", changed_col: "changed"})
        gt_metrics = metrics.compute_ground_truth_metrics(
            _records_with_none(method_rows), gt_intervals_by_experiment, first_decision_index
        )
        # Must be popped BEFORE gt_metrics is spread into the summary row
        # below - otherwise decision_summary_<label>.csv would gain a
        # column holding a serialized list instead of a scalar.
        transition_details = gt_metrics.pop("transition_details", [])
        for detail in transition_details:
            transition_latency_rows.append({"mac": mac, "method": method, **detail})

        summary_rows.append({
            "mac": mac,
            "method": method,
            "num_detections": len(detail_df),
            "num_decided": num_decided,
            "num_transitions": num_transitions,
            "first_decision_index": first_decision_index,
            "agree_rate_vs_final": agree_rate_vs_final,
            **gt_metrics,
        })

    return summary_rows, transition_latency_rows


def build_confusion_rows(mac, detail_df):
    """One row per (mac, method, real_room, estimated_room) with a count,
    built only from rows with ground-truth coverage. Long/tidy format -
    easy to pivot into a real matrix per method afterwards in pandas/Excel."""
    confusion_rows = []
    gt_covered = detail_df[detail_df["ground_truth_room"].notna()]
    for method, room_col, _ in METHODS:
        rows = gt_covered[["ground_truth_room", room_col]].rename(columns={room_col: "estimated_room"})
        for count_row in metrics.build_confusion_counts(_records_with_none(rows)):
            confusion_rows.append({"mac": mac, "method": method, **count_row})
    return confusion_rows


def load_node_seq_by_esp(collection, experiment_id):
    """{(esp_id, boot_id): [node_seq, ...]} - uma entrada por LOTE (esp_id,
    batch_id) distinto, não por linha de raw_detections (várias linhas
    partilham o mesmo node_seq quando o mesmo lote viu vários beacons).
    node_seq é propriedade do NÓ, não do beacon - por isso esta função
    trabalha diretamente sobre a coleção, independente de data_by_mac.
    Linhas com boot_id em falta (dados antigos, anteriores a esta
    funcionalidade) ficam de fora - sem boot_id não há forma segura de
    saber a que sessão pertencem."""
    query = {"node_seq": {"$ne": None}, "boot_id": {"$ne": None}}
    if experiment_id is not None:
        query["experiment_id"] = experiment_id
    docs = collection.find(query, {"esp_id": 1, "node_seq": 1, "batch_id": 1, "boot_id": 1})
    seen_batches = set()
    seqs_by_esp_boot = {}
    for doc in docs:
        key = (doc.get("esp_id"), doc.get("batch_id"))
        if key in seen_batches:
            continue
        seen_batches.add(key)
        seqs_by_esp_boot.setdefault((doc.get("esp_id"), doc.get("boot_id")), []).append(doc.get("node_seq"))
    return seqs_by_esp_boot


def compute_node_seq_gaps(seqs_by_esp_boot):
    """Ordena por node_seq DENTRO DE CADA (esp_id, boot_id) e conta saltos/
    duplicados - nunca entre sessões diferentes do mesmo nó (node_seq
    reinicia a cada arranque do firmware, por isso duas sessões podem
    partilhar números por coincidência). Devolve
    {esp_id: [{"boot_id", "num_batches_seen", "num_duplicates", "num_gaps",
    "num_missing_estimated", "seq_min", "seq_max"}, ...]} - uma entrada por
    sessão de arranque, agrupadas por esp_id só para leitura mais fácil."""
    result = {}
    for (esp_id, boot_id), seqs in seqs_by_esp_boot.items():
        ordered = sorted(seqs)
        num_duplicates = num_gaps = num_missing_estimated = 0
        for i in range(1, len(ordered)):
            diff = ordered[i] - ordered[i - 1]
            if diff == 0:
                num_duplicates += 1
            elif diff > 1:
                num_gaps += 1
                num_missing_estimated += diff - 1
        result.setdefault(esp_id, []).append({
            "boot_id": boot_id, "num_batches_seen": len(ordered), "num_duplicates": num_duplicates,
            "num_gaps": num_gaps, "num_missing_estimated": num_missing_estimated,
            "seq_min": ordered[0] if ordered else None, "seq_max": ordered[-1] if ordered else None,
        })
    return result


def load_acquisition_config_by_esp(collection, experiment_id):
    """{(experiment_id, esp_id): {"scan_duration_sec": {valores...}, "upload_interval_ms": {valores...}}}
    - conjunto de valores efetivos DISTINTOS observados em raw_detections
    (guião secção 7), por esp_id, dentro de cada experiment_id. Linhas sem
    nenhum dos dois campos (dados anteriores a esta funcionalidade, ou
    formato antigo) ficam simplesmente ausentes dos conjuntos - não tratadas
    como um terceiro valor "desconhecido"."""
    query = {"$or": [{"scan_duration_sec": {"$ne": None}}, {"upload_interval_ms": {"$ne": None}}]}
    if experiment_id is not None:
        query["experiment_id"] = experiment_id
    docs = collection.find(
        query, {"esp_id": 1, "experiment_id": 1, "scan_duration_sec": 1, "upload_interval_ms": 1}
    )
    result = {}
    for doc in docs:
        key = (doc.get("experiment_id"), doc.get("esp_id"))
        entry = result.setdefault(key, {"scan_duration_sec": set(), "upload_interval_ms": set()})
        if doc.get("scan_duration_sec") is not None:
            entry["scan_duration_sec"].add(doc["scan_duration_sec"])
        if doc.get("upload_interval_ms") is not None:
            entry["upload_interval_ms"].add(doc["upload_interval_ms"])
    return result


def compute_acquisition_config_divergence(config_by_esp, acquisition_by_experiment):
    """Duas verificações independentes, por (experiment_id, campo) em
    scan_duration_sec/upload_interval_ms:

    (a) Consistência interna por esp_id: mais do que um valor efetivo
        distinto para o MESMO esp_id dentro do MESMO experiment_id nunca
        pode ser intencional (é o mesmo nó físico, no mesmo ensaio) -
        sinalizado sempre que acontece.
    (b) Frota vs. registado: só é comparável quando TODOS os esp_id que
        contribuíram um valor limpo (exatamente 1 valor observado) nesse
        experiment_id concordam entre si (frota homogénea). Comparar um
        único valor registado em `experiments` contra uma frota
        deliberadamente heterogénea (configuração por esp_id a ser usada
        para dar valores diferentes a nós diferentes) acusaria falsamente o
        nó cujo valor é, por desenho, diferente dos outros - por isso, nesse
        caso, esta função não compara com o registado, devolve só a
        distribuição por esp_id como informação.

    Devolve {experiment_id: {"warnings": [frase citável, ...], "fleet":
    {campo: {"homogeneous", "effective_value", "registered_value",
    "diverges_from_registered", "by_esp_id"}}}} - um registo por
    experiment_id com alguns dados de configuração em raw_detections;
    inteiramente {} quando esta corrida não tem nenhum (ex: dados anteriores
    à funcionalidade)."""
    by_experiment = {}
    for (experiment_id, esp_id), field_sets in config_by_esp.items():
        by_experiment.setdefault(experiment_id, {})[esp_id] = field_sets

    result = {}
    for experiment_id, per_esp in by_experiment.items():
        warnings = []
        fleet = {}
        registered = acquisition_by_experiment.get(experiment_id) or {}

        for field in ("scan_duration_sec", "upload_interval_ms"):
            clean_values_by_esp = {}
            for esp_id, field_sets in per_esp.items():
                values = sorted(field_sets.get(field, set()))
                if len(values) > 1:
                    warnings.append(
                        f"{esp_id} usou {len(values)} valores distintos de {field} dentro do "
                        f"ensaio '{experiment_id}': {values} - o mesmo nó nunca deveria divergir "
                        f"de si próprio dentro de um único ensaio."
                    )
                elif len(values) == 1:
                    clean_values_by_esp[esp_id] = values[0]

            distinct_clean = sorted(set(clean_values_by_esp.values()))
            homogeneous = len(distinct_clean) <= 1
            effective_value = distinct_clean[0] if homogeneous and distinct_clean else None
            registered_value = registered.get(field)
            diverges_from_registered = (
                homogeneous and effective_value is not None and registered_value is not None
                and effective_value != registered_value
            )
            if diverges_from_registered:
                warnings.append(
                    f"Ensaio '{experiment_id}': {field} registado em experiments "
                    f"({registered_value}) diverge do valor efetivo observado em todos os nós "
                    f"({effective_value})."
                )
            fleet[field] = {
                "homogeneous": homogeneous,
                "effective_value": effective_value,
                "registered_value": registered_value,
                "diverges_from_registered": diverges_from_registered,
                "by_esp_id": clean_values_by_esp,
            }

        result[experiment_id] = {"warnings": warnings, "fleet": fleet}

    return result


def plot_mac(mac, detail_df, output_dir, label):
    x = list(range(len(detail_df)))

    room_cols = ["raw_room"] + [rc for _, rc, _ in METHODS]
    all_room_values = pd.concat([detail_df[c] for c in room_cols])
    rooms_all = sorted(r for r in all_room_values.dropna().unique())
    room_to_code = {room: i for i, room in enumerate(rooms_all)}

    fig, axes = plt.subplots(1 + len(METHODS), 1, sharex=True, figsize=(12, 11))

    ax = axes[0]
    y_raw = [room_to_code.get(r, float("nan")) for r in detail_df["raw_room"]]
    ax.scatter(x, y_raw, s=10, color="#6b7280")
    ax.set_yticks(list(room_to_code.values()))
    ax.set_yticklabels(list(room_to_code.keys()))
    ax.set_ylabel("Raw")
    ax.set_title(f"{mac} - {label}")

    for ax, (name, room_col, changed_col) in zip(axes[1:], METHODS):
        y = [room_to_code.get(r, float("nan")) if pd.notna(r) else float("nan")
             for r in detail_df[room_col]]
        color = METHOD_COLORS[name]
        ax.step(x, y, where="post", color=color, linewidth=2)

        change_x = [xi for xi, c in zip(x, detail_df[changed_col]) if c]
        change_y = [y[xi] for xi in change_x]
        ax.scatter(change_x, change_y, s=40, color=color, zorder=3)

        ax.set_yticks(list(room_to_code.values()))
        ax.set_yticklabels(list(room_to_code.keys()))
        ax.set_ylabel(name)

        if name == FINAL_METHOD:
            decided = detail_df[room_col].notna()
            if decided.any():
                first_idx = int(decided.idxmax())
                if first_idx > 0:
                    ax.axvspan(-0.5, first_idx - 0.5, color="lightgray", alpha=0.4)

    axes[-1].set_xlabel("Detection index (chronological order)")
    fig.tight_layout()

    filename = f"{mac.replace(':', '')}_{label}_room_timeline.png"
    path = os.path.join(output_dir, filename)
    fig.savefig(path, dpi=120)
    plt.close(fig)
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--experiment-id", default=None, help="Filtrar por experiment_id (default: todos)")
    parser.add_argument("--mac", nargs="+", default=None, help="Um ou mais MACs (default: todos os presentes nos dados)")
    parser.add_argument("--hysteresis-margin", type=float, default=dm.HYSTERESIS_MARGIN)
    parser.add_argument("--median-window", type=int, default=5)
    parser.add_argument("--persistence-streak", type=int, default=3)
    parser.add_argument("--min-rssi", type=float, default=None,
                         help="Ignora leituras com RSSI abaixo deste limiar (default: sem filtro)")
    parser.add_argument("--output-dir", default="analysis_output")
    parser.add_argument("--no-plots", action="store_true", help="Gera só os CSVs, sem graficos")
    parser.add_argument("--mongo-uri", default="mongodb://localhost:27017")
    parser.add_argument("--db-name", default="temp1_db",
                         help="Nome da base de dados MongoDB (default: temp1_db) - útil para apontar a análise "
                              "a uma base de dados de teste/staging sem editar o script")
    args = parser.parse_args()

    macs = [normalize_mac(m) for m in args.mac] if args.mac else None
    label = args.experiment_id if args.experiment_id else "all"

    os.makedirs(args.output_dir, exist_ok=True)
    plots_dir = os.path.join(os.path.dirname(__file__) or ".", "plots")
    if not args.no_plots:
        os.makedirs(plots_dir, exist_ok=True)

    client = MongoClient(args.mongo_uri)
    db = client[args.db_name]
    raw_detections = db["raw_detections"]
    ground_truth = db["ground_truth"]
    experiments = db["experiments"]

    print(f"A carregar raw_detections (experiment_id={args.experiment_id!r}, mac={macs})...")
    data_by_mac = load_detections_by_mac(raw_detections, args.experiment_id, macs)

    if not data_by_mac:
        print("Nenhum MAC encontrado para os filtros indicados.")
        return

    if args.min_rssi is not None:
        # Drops rows outright (not just their rssi) - filters ALL FOUR
        # methods' working set, not only the median-based ones. This changes
        # the effective row count of the detail CSV; it's recorded below in
        # run_metadata, not silent.
        data_by_mac = {mac: dm.filter_min_rssi(docs, args.min_rssi) for mac, docs in data_by_mac.items()}

    print(f"A carregar ground_truth (experiment_id={args.experiment_id!r})...")
    ground_truth_by_mac = load_ground_truth_by_mac(ground_truth, args.experiment_id, list(data_by_mac.keys()))

    all_detail_frames = []
    all_summary_rows = []
    all_transition_latency_rows = []
    all_confusion_rows = []
    ground_truth_summary = {}
    node_time_summary = {}

    for mac, docs in data_by_mac.items():
        if not docs:
            print(f"  {mac}: 0 deteções, a saltar")
            continue
        print(f"  {mac}: {len(docs)} deteções")

        gt_events = ground_truth_by_mac.get(mac, [])
        gt_intervals_by_experiment = build_ground_truth_intervals(gt_events)

        detail_df = build_detail_dataframe(
            mac, docs, args.hysteresis_margin, args.median_window, args.persistence_streak,
            gt_intervals_by_experiment,
        )
        all_detail_frames.append(detail_df)
        summary_rows, transition_latency_rows = build_summary_rows(mac, detail_df, gt_intervals_by_experiment)
        all_summary_rows.extend(summary_rows)
        all_transition_latency_rows.extend(transition_latency_rows)
        all_confusion_rows.extend(build_confusion_rows(mac, detail_df))

        ground_truth_summary[mac] = {
            "events_loaded": len(gt_events),
            "rows_with_ground_truth": int(detail_df["ground_truth_room"].notna().sum()),
            "rows_total": len(detail_df),
        }
        node_time_summary[mac] = {
            "rows_with_node_seq": int(detail_df["node_seq"].notna().sum()),
            "rows_with_node_time": int(detail_df["node_time"].notna().sum()),
            "rows_total": len(detail_df),
            "experiments_using_node_time": sorted(
                exp_id for exp_id in detail_df.loc[detail_df["clock_source"] == "node", "experiment_id"].dropna().unique()
            ),
        }

        if not args.no_plots:
            path = plot_mac(mac, detail_df, plots_dir, label)
            print(f"    gráfico: {path}")

    if not all_detail_frames:
        print("Nenhuma deteção para processar.")
        return

    combined_detail = pd.concat(all_detail_frames, ignore_index=True)

    detail_csv = os.path.join(args.output_dir, f"raw_with_decisions_{label}.csv")
    summary_csv = os.path.join(args.output_dir, f"decision_summary_{label}.csv")
    confusion_csv = os.path.join(args.output_dir, f"confusion_matrix_{label}.csv")
    transition_latencies_csv = os.path.join(args.output_dir, f"transition_latencies_{label}.csv")
    metadata_json = os.path.join(args.output_dir, f"run_metadata_{label}.json")

    combined_detail.to_csv(detail_csv, index=False)
    pd.DataFrame(all_summary_rows).to_csv(summary_csv, index=False)
    # Explicit columns=... even when all_confusion_rows is empty (no ground
    # truth at all in this run) - otherwise pd.DataFrame([]) has NO columns,
    # writing a truly headerless CSV instead of a header-only one, which
    # would break anything downstream expecting these column names to exist.
    pd.DataFrame(
        all_confusion_rows, columns=["mac", "method", "real_room", "estimated_room", "count"]
    ).to_csv(confusion_csv, index=False)
    # Real Mongo-sourced per-transition latencies (transition instant + each
    # method's confirmation instant), consumed by generate_report_figures.py's
    # latency-boxplot and rssi-timeline figures - never reconstructed from a
    # CSV column change, so free of the baseline-artifact caveat that
    # statistical_analysis.py's --pertransition mode has to carry.
    pd.DataFrame(
        all_transition_latency_rows,
        columns=["mac", "method", "experiment_id", "transition_index", "new_room",
                 "transition_time", "detected", "latency_sec", "confirmation_time"],
    ).to_csv(transition_latencies_csv, index=False)

    # Acquisition parameters (scan duration/interval, firmware RSSI cutoff)
    # were registered separately per experiment_id via POST /api/experiment,
    # at collection time - keyed here by every experiment_id actually present
    # in the processed data (not just args.experiment_id, since "all
    # experiments" mode can mix several trials).
    distinct_experiment_ids = sorted(
        e for e in combined_detail["experiment_id"].dropna().unique()
    )
    acquisition_by_experiment = {
        exp_id: experiments.find_one({"experiment_id": exp_id}, {"_id": 0})
        for exp_id in distinct_experiment_ids
    }

    # Offline missing/duplicate-batch detection (guião secção 3) - reads
    # node_seq directly from raw_detections, independent of data_by_mac
    # (node_seq is a property of the node, not the beacon). Complements the
    # live, console-only check in app.py with citable numbers here.
    node_seq_gap_summary = compute_node_seq_gaps(load_node_seq_by_esp(raw_detections, args.experiment_id))

    # Guião secção 7: acquisition config (scan_duration_sec/upload_interval_ms)
    # divergence, both within a node across the same trial and between the
    # fleet's effective config and what was registered in `experiments` - see
    # compute_acquisition_config_divergence's docstring for why these are two
    # separate checks, not one.
    acquisition_config_divergence = compute_acquisition_config_divergence(
        load_acquisition_config_by_esp(raw_detections, args.experiment_id), acquisition_by_experiment,
    )

    # See NODE_TIME_CLOCK_WARNING's own comment - this stays None (no
    # warning at all) unless at least one processed group actually used
    # clock_source="node".
    node_time_clock_warning = (
        NODE_TIME_CLOCK_WARNING if (combined_detail["clock_source"] == "node").any() else None
    )

    run_metadata = {
        "run_timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "experiment_id_filter": args.experiment_id,
        "mac_filter": macs,
        "resolved_macs": sorted(data_by_mac.keys()),
        "analysis_parameters": {
            "hysteresis_margin": args.hysteresis_margin,
            "median_window": args.median_window,
            "persistence_streak": args.persistence_streak,
            "min_rssi": args.min_rssi,
        },
        "output_files": {
            "detail_csv": detail_csv,
            "summary_csv": summary_csv,
            "confusion_csv": confusion_csv,
            "plots_dir": None if args.no_plots else plots_dir,
        },
        "acquisition_parameters_by_experiment": acquisition_by_experiment,
        "ground_truth_summary": ground_truth_summary,
        "node_time_summary": node_time_summary,
        "node_seq_gap_summary": node_seq_gap_summary,
        "node_time_clock_warning": node_time_clock_warning,
        "acquisition_config_divergence": acquisition_config_divergence,
    }
    with open(metadata_json, "w", encoding="utf-8") as f:
        json.dump(run_metadata, f, indent=2, ensure_ascii=False, default=str)

    print(f"\nCSV de detalhe: {detail_csv}")
    print(f"CSV de resumo: {summary_csv}")
    print(f"Matriz de confusão: {confusion_csv}")
    print(f"Latências por transição: {transition_latencies_csv}")
    print(f"Metadados do ensaio/análise: {metadata_json}")


if __name__ == "__main__":
    main()
