"""
Comparação estatística entre os 4 métodos de decisão (baseline, median,
median_hysteresis, median_hysteresis_persistence), por cima das métricas já
calculadas por analyze_room_decisions.py (secção "10. Análise estatística
recomendada" do guião): mediana+IQR para latência, média/desvio-padrão/IC95%
para exatidão, comparação emparelhada (Wilcoxon para 2 métodos, Friedman para
os 4), dimensão de efeito, e correção de Bonferroni para as comparações
múltiplas.

Restrição rígida: este ficheiro nunca importa pymongo nem acede à MongoDB -
lê só os CSVs já exportados por analyze_room_decisions.py
(decision_summary_<label>.csv / raw_with_decisions_<label>.csv). Por isso
duplica localmente (não importa de analyze_room_decisions.py, que traz
pymongo) o pequeno helper normalize_mac/_records_with_none.

Dois modos, com unidades de comparação diferentes:

- "per-repetition" (principal/correto): cada decision_summary_<label>.csv
  fornecido representa UMA repetição/ensaio do mesmo protocolo. Os testes
  pareados só correm de facto com >=2 repetições - com 1 só, ficam
  explicitamente marcados como "skipped" (não correm às cegas com N=1).

- "per-transition" (exploratório/piloto): trabalha a partir de UM
  raw_with_decisions_<label>.csv, reconstruindo os limites das transições
  reais de sala a partir da própria coluna ground_truth_room já
  materializada nesse CSV (sem aceder ao Mongo). Dá n pequeno (nº de
  transições reais dentro de 1 ensaio único) - todo o output fica marcado
  como piloto, nunca substituindo repetições reais. A latência do método
  "baseline" sai sempre 0.0s neste modo, por construção (ver
  BASELINE_LATENCY_CAVEAT) - não é um resultado genuíno.

Requer scipy além dos requisitos de analyze_room_decisions.py:

    pip install -r requirements.txt -r requirements-analysis.txt

Uso:

    python statistical_analysis.py per-repetition \\
        --summary-csv analysis_output/decision_summary_rep1.csv analysis_output/decision_summary_rep2.csv

    python statistical_analysis.py per-transition \\
        --detail-csv analysis_output/raw_with_decisions_<label>.csv
"""

import argparse
import itertools
import json
import math
import os
import statistics
from datetime import datetime

import pandas as pd
from scipy.stats import wilcoxon, friedmanchisquare, norm
from scipy.stats import t as t_dist

import metrics

METHODS = ["baseline", "median", "median_hysteresis", "median_hysteresis_persistence"]
FINAL_METHOD = "median_hysteresis_persistence"
WILCOXON_PAIRS = list(itertools.combinations(METHODS, 2))  # 6 pares, ordem fixa

METRICS_TESTED = ["accuracy", "false_movements_per_hour", "latency_median_sec"]
PER_TRANSITION_METRICS_TESTED = ["latency_sec"]  # accuracy/false_movements_per_hour não têm unidade por-transição; detected fica só descritivo (ver detection_rate_summary)

# Superset de METRICS_TESTED, só para estatística descritiva (média/IC),
# usado pelas figuras/tabela do capítulo de resultados (backend/
# generate_report_figures.py) que precisam de mais colunas do que as 3
# testadas para significância - ex. a tabela global (figura 1 do guião)
# tem 6 colunas, não 3. NUNCA usado pelos testes pareados/Bonferroni
# abaixo - build_repetition_wilcoxon_rows/build_repetition_friedman_rows
# continuam a iterar só METRICS_TESTED, para a família de hipóteses
# (REPETITION_BONFERRONI_M_*) nunca mudar silenciosamente por causa disto.
DESCRIPTIVE_METRICS = METRICS_TESTED + ["latency_p95_sec", "missed_movement_rate", "pct_time_unknown_or_transition"]

DEFAULT_ALPHA = 0.05

# m fixo por família de hipóteses (nº de pares x nº de métricas testadas em
# conjunto) - não recalculado a partir de quantos testes acabaram por correr,
# para não encolher a correção só porque alguns pares tiveram pouca
# sobreposição de dados (ver apply_bonferroni).
REPETITION_BONFERRONI_M_WILCOXON = len(WILCOXON_PAIRS) * len(METRICS_TESTED)              # 18
REPETITION_BONFERRONI_M_FRIEDMAN = len(METRICS_TESTED)                                     # 3
TRANSITION_BONFERRONI_M_WILCOXON = len(WILCOXON_PAIRS) * len(PER_TRANSITION_METRICS_TESTED)  # 6
TRANSITION_BONFERRONI_M_FRIEDMAN = len(PER_TRANSITION_METRICS_TESTED)                      # 1

REQUIRED_SUMMARY_COLUMNS = ["mac", "method"] + DESCRIPTIVE_METRICS
REQUIRED_DETAIL_COLUMNS = ["mac", "experiment_id", "time", "ground_truth_room"] + [f"{m}_room" for m in METHODS]

RAW_VALUES_COLUMNS = ["mac", "method", "metric", "repetition_label", "value"]
DESCRIPTIVE_COLUMNS = [
    "mac", "method", "metric", "n", "mean", "std", "sem", "ci_lower", "ci_upper",
    "median", "p95", "iqr", "min", "max", "repetitions_used",
]
WILCOXON_COLUMNS = [
    "mac", "metric", "method_a", "method_b", "adjacent_in_chain", "vs_final", "alpha",
    "n_pairs", "n_pairs_nonzero", "statistic", "pvalue", "pvalue_bonferroni",
    "significant", "significant_bonferroni", "effect_size_r", "median_diff", "skipped_reason",
]
FRIEDMAN_COLUMNS = [
    "mac", "metric", "alpha", "n_blocks", "k_methods", "statistic", "pvalue",
    "pvalue_bonferroni", "significant", "significant_bonferroni", "kendalls_w", "skipped_reason",
]
TRANSITION_DETAIL_COLUMNS = [
    "mac", "experiment_id", "transition_index", "new_room", "method",
    "detected", "latency_sec", "latency_is_anchor_artifact",
]
DETECTION_RATE_COLUMNS = ["mac", "experiment_id", "method", "n_transitions", "n_detected", "detection_rate"]
TRANSITION_WILCOXON_COLUMNS = [
    "mac", "experiment_id", "metric", "method_a", "method_b", "adjacent_in_chain", "vs_final",
    "alpha", "n_pairs", "n_pairs_nonzero", "statistic", "pvalue", "pvalue_bonferroni",
    "significant", "significant_bonferroni", "effect_size_r", "median_diff", "skipped_reason", "caveat",
]
TRANSITION_FRIEDMAN_COLUMNS = [
    "mac", "experiment_id", "metric", "alpha", "n_blocks", "k_methods", "statistic", "pvalue",
    "pvalue_bonferroni", "significant", "significant_bonferroni", "kendalls_w", "skipped_reason", "caveat",
]

BASELINE_LATENCY_CAVEAT = (
    "baseline_room == raw_room em cada linha, e a ancora de transicao reconstruida "
    "neste modo (a partir da propria coluna ground_truth_room do CSV, sem Mongo) e "
    "exatamente a linha onde essa coluna muda - por isso a latencia do baseline sai "
    "sempre 0.0s aqui, por construcao, nao porque seja genuinamente mais rapido. "
    "Nao interpretar como um resultado real; o modo per-repetition usa os instantes "
    "reais do toque no Mongo e nao tem este vies."
)


def normalize_mac(mac):
    return mac.replace("-", ":").lower().strip().replace('"', "")


def _records_with_none(df):
    """Duplicado de analyze_room_decisions._records_with_none - não importado
    de lá de propósito (esse módulo traz pymongo). to_dict("records") PRIMEIRO,
    só depois trocar NaN float por None - ao contrário falha silenciosamente em
    colunas float64 inteiramente vazias (pandas volta a converter None em NaN
    para preservar o dtype numérico)."""
    records = df.to_dict("records")
    for record in records:
        for key, value in record.items():
            if isinstance(value, float) and pd.isna(value):
                record[key] = None
    return records


def _adjacent_in_chain(method_a, method_b):
    return METHODS.index(method_b) - METHODS.index(method_a) == 1


def _vs_final(method_a, method_b):
    return method_b == FINAL_METHOD


# ---------------------------------------------------------------------------
# Núcleo estatístico puro (sem pandas/IO)
# ---------------------------------------------------------------------------

def descriptive_stats(values, confidence=0.95):
    """values: lista já limpa (sem None) de floats. Mediana/p95/IQR/min/max
    vêm de metrics.summarize_latencies - genérico apesar do nome, e seguro
    mesmo em n=1 (verificado empiricamente no venv real deste projeto,
    Python 3.14.3: statistics.quantiles([v], n=4) não rebenta). mean/std/sem/
    IC ficam à parte porque a stdlib não os dá e o IC precisa de
    t-Student (não normal - mais correto para os n pequenos típicos de nº
    de repetições). std/sem/IC ficam None abaixo de n=2 (statistics.stdev
    rebenta com 1 ponto - indefinido, nunca reportado como zero)."""
    quantile_summary = metrics.summarize_latencies(values)
    n = len(values)
    if n == 0:
        return {"n": 0, "mean": None, "std": None, "sem": None,
                "ci_lower": None, "ci_upper": None, **quantile_summary}

    mean = statistics.mean(values)
    if n >= 2:
        std = statistics.stdev(values)
        sem = std / math.sqrt(n)
        if std == 0:
            ci_lower = ci_upper = mean
        else:
            ci_lower, ci_upper = (float(b) for b in t_dist.interval(confidence, df=n - 1, loc=mean, scale=sem))
    else:
        std = sem = ci_lower = ci_upper = None

    return {"n": n, "mean": mean, "std": std, "sem": sem,
            "ci_lower": ci_lower, "ci_upper": ci_upper, **quantile_summary}


def apply_bonferroni(rows, m, alpha=DEFAULT_ALPHA):
    """rows: dicts com uma chave "pvalue" (float ou None - None = teste
    skipped, fica sem correção também, não ganha um "significant" de borla
    só por não ter corrido). m: tamanho FIXO da família de hipóteses
    (nº de pares x nº de métricas testadas em conjunto) - não o nº de
    testes que happen to ter corrido; uma família pré-definida não encolhe
    só porque alguns pares tiveram pouca sobreposição de dados."""
    out = []
    for row in rows:
        row = dict(row)
        p = row.get("pvalue")
        if p is None:
            row["pvalue_bonferroni"] = None
            row["significant_bonferroni"] = None
        else:
            pb = min(1.0, p * m)
            row["pvalue_bonferroni"] = pb
            row["significant_bonferroni"] = bool(pb < alpha)
        out.append(row)
    return out


def _skipped_wilcoxon_result(n_pairs, reason, median_diff=None):
    return {
        "n_pairs": n_pairs, "n_pairs_nonzero": 0,
        "statistic": None, "pvalue": None, "significant": None,
        "effect_size_r": None, "median_diff": median_diff,
        "skipped_reason": reason,
    }


def pairwise_wilcoxon(x, y, alpha=DEFAULT_ALPHA):
    """x, y: listas paralelas já emparelhadas/limpas pelo chamador (sem
    None, mesmo comprimento). Dimensão de efeito r = Z/sqrt(N) (Rosenthal
    1991): method="auto" (p-value exato, mais correto que a aproximação
    normal para os n pequenos deste projeto) não expõe .zstatistic, por
    isso Z é recuperado do p-value devolvido via norm.ppf - sinal tirado da
    mediana das diferenças emparelhadas (x-y). N = nº de diferenças não
    nulas (convenção do teste de sinais/postos; zero_method="wilcox"
    descarta ties em zero antes do ranking)."""
    n = len(x)
    if n < 2:
        return _skipped_wilcoxon_result(n, "fewer_than_2_paired_observations")

    diffs = [xi - yi for xi, yi in zip(x, y)]
    n_nonzero = sum(1 for d in diffs if d != 0)
    median_diff = statistics.median(diffs)
    if n_nonzero == 0:
        return _skipped_wilcoxon_result(n, "all_differences_zero", median_diff=median_diff)

    try:
        result = wilcoxon(x, y, zero_method="wilcox", alternative="two-sided", method="auto")
    except ValueError as exc:
        return _skipped_wilcoxon_result(n, f"scipy_error: {exc}", median_diff=median_diff)

    p = float(result.pvalue)
    if math.isnan(p):
        return _skipped_wilcoxon_result(n, "scipy_returned_nan", median_diff=median_diff)

    p_clamped = min(max(p, 1e-300), 1.0)
    z_abs = float(norm.ppf(1 - p_clamped / 2))
    sign = 1.0 if median_diff > 0 else (-1.0 if median_diff < 0 else 0.0)
    r = (z_abs / math.sqrt(n_nonzero)) * sign

    return {
        "n_pairs": n, "n_pairs_nonzero": n_nonzero,
        "statistic": float(result.statistic), "pvalue": p,
        "significant": bool(p < alpha),
        "effect_size_r": r, "median_diff": median_diff,
        "skipped_reason": None,
    }


def _skipped_friedman_result(n_blocks, k, reason):
    return {
        "n_blocks": n_blocks, "k_methods": k,
        "statistic": None, "pvalue": None, "significant": None,
        "kendalls_w": None, "skipped_reason": reason,
    }


def friedman_test(samples_by_method, alpha=DEFAULT_ALPHA):
    """samples_by_method: {método: [valores...]}, todas as listas com o
    mesmo comprimento e na mesma ordem de bloco (repetição ou transição,
    conforme o modo - já resolvido pelo chamador). Kendall's W =
    statistic / (n_blocks*(k-1)) - identidade padrão entre a estatística
    do Friedman e W (verificado numericamente contra um cálculo manual de
    somas de postos durante o planeamento). Guardas explícitas: k<3 (scipy
    rebenta) e n_blocks<2 (scipy NÃO rebenta mas o resultado não depende
    dos dados - verificado, teria de ficar "skipped" na mesma)."""
    methods = list(samples_by_method)
    k = len(methods)
    lists = [samples_by_method[m] for m in methods]
    n_blocks = len(lists[0]) if lists else 0

    if k < 3:
        return _skipped_friedman_result(n_blocks, k, "fewer_than_3_methods")
    if n_blocks < 2:
        return _skipped_friedman_result(n_blocks, k, "fewer_than_2_blocks")

    try:
        result = friedmanchisquare(*lists)
    except ValueError as exc:
        return _skipped_friedman_result(n_blocks, k, f"scipy_error: {exc}")

    statistic, pvalue = float(result.statistic), float(result.pvalue)
    if math.isnan(statistic) or math.isnan(pvalue):
        return _skipped_friedman_result(n_blocks, k, "undefined_zero_variance_across_all_blocks")

    # W é teoricamente limitado a [0,1] - o ruído de ponto flutuante do
    # próprio cálculo interno do qui-quadrado do scipy pode empurrá-lo
    # marginalmente acima de 1.0 (visto em teste: 1.0000000000000004 com
    # concordância quase perfeita entre blocos) - sem significado real,
    # só travado aqui para nunca aparecer um valor fora do intervalo.
    kendalls_w = max(0.0, min(1.0, statistic / (n_blocks * (k - 1))))

    return {
        "n_blocks": n_blocks, "k_methods": k,
        "statistic": statistic, "pvalue": pvalue,
        "significant": bool(pvalue < alpha),
        "kendalls_w": kendalls_w,
        "skipped_reason": None,
    }


# ---------------------------------------------------------------------------
# Modo 1 - por repetição
# ---------------------------------------------------------------------------

def load_repetition_summaries(paths):
    if len(paths) != len(set(paths)):
        raise ValueError(f"Caminhos repetidos em --summary-csv: {paths}")

    records_by_label = {}
    for path in paths:
        df = pd.read_csv(path)
        missing = [c for c in REQUIRED_SUMMARY_COLUMNS if c not in df.columns]
        if missing:
            raise ValueError(
                f"{path}: faltam colunas {missing}. Este ficheiro tem o schema de "
                "decision_summary_<label>.csv COM as métricas de ground truth "
                "(accuracy, false_movements_per_hour, ...)? Ficheiros antigos, "
                "gerados antes dessas colunas existirem, não servem aqui."
            )
        label = os.path.splitext(os.path.basename(path))[0]
        records_by_label[label] = _records_with_none(df)
    return records_by_label


def check_consistent_analysis_parameters(csv_paths, prefix="decision_summary_", ignore_keys=None):
    """Compares analysis_parameters (median_window/hysteresis_margin/
    persistence_streak/min_rssi) across the run_metadata_<label>.json
    sibling of each input path - motivated by a real finding, not
    hypothetical: this project's own ensaio1/ensaio2 were analyzed with
    median_window=5 vs 15 and were nearly pooled as "repetitions" without
    anyone noticing. Returns a list of human-readable warnings (empty =
    consistent) - never raises, callers decide whether to hard-fail or
    print-and-continue. `prefix` matches whichever of analyze_room_
    decisions.py's per-label outputs is being checked (default
    "decision_summary_"; pass "raw_with_decisions_" for detail CSVs, e.g.
    generate_report_figures.py's scenario-table). ignore_keys excludes a
    key from comparison, for sweep_parameter.py to allow the ONE parameter
    it's deliberately varying to differ across the sweep's own per-point
    repetitions. Sibling files that can't be located are silently skipped
    (best-effort check, not a hard requirement on file layout)."""
    ignore_keys = set(ignore_keys or [])
    params_by_path = {}
    for path in csv_paths:
        stem = os.path.splitext(os.path.basename(path))[0]
        if not stem.startswith(prefix):
            continue
        run_label = stem[len(prefix):]
        metadata_path = os.path.join(os.path.dirname(path), f"run_metadata_{run_label}.json")
        if not os.path.exists(metadata_path):
            continue
        with open(metadata_path, encoding="utf-8") as f:
            metadata = json.load(f)
        params_by_path[path] = {
            k: v for k, v in metadata.get("analysis_parameters", {}).items() if k not in ignore_keys
        }

    warnings = []
    reference_path, reference_params = None, None
    for path, params in params_by_path.items():
        if reference_params is None:
            reference_path, reference_params = path, params
            continue
        if params != reference_params:
            warnings.append(
                f"Parâmetros de análise inconsistentes: {os.path.basename(reference_path)} "
                f"tem {reference_params}, {os.path.basename(path)} tem {params} - "
                "estas repetições não são comparáveis."
            )
    return warnings


def check_room_consistency(confusion_csv_paths):
    """Compares the set of real_room values across confusion_matrix_<label>.csv
    files about to be pooled (figure 6's --pool path in
    generate_report_figures.py) - motivated by a real finding, not a
    hypothetical: this project's own ensaio1/ensaio2 only share "Sala dos
    brinquedos", so summing their confusion matrices as-is would produce a
    0-count row for any room never tested in one of the two repetitions,
    visually indistinguishable from "tested extensively, zero confusion".
    Returns a list of human-readable warnings (empty = consistent)."""
    rooms_by_path = {}
    for path in confusion_csv_paths:
        df = pd.read_csv(path)
        rooms_by_path[path] = set(df["real_room"].dropna().unique())

    all_rooms = set()
    common_rooms = None
    for rooms in rooms_by_path.values():
        all_rooms |= rooms
        common_rooms = rooms if common_rooms is None else (common_rooms & rooms)
    common_rooms = common_rooms or set()

    only_in_some = all_rooms - common_rooms
    if not only_in_some:
        return []
    details = []
    for room in sorted(only_in_some):
        present_in = [os.path.basename(p) for p, rooms in rooms_by_path.items() if room in rooms]
        details.append(f"{room!r} só em {present_in}")
    return [
        "Salas reais não são as mesmas em todas as repetições - somar as "
        "matrizes de confusão vai gerar linhas com 0 deteções para salas "
        "nunca testadas nessa repetição, indistinguível de 'testada, sem "
        "confusão': " + "; ".join(details)
    ]


def check_scenario_consistency(detail_csv_paths):
    """Compares the set of ground_truth_scenario values across
    raw_with_decisions_<label>.csv files being aggregated for the
    per-scenario accuracy table (figure 9, guião secção 9) - same pattern
    as check_room_consistency, same philosophy (warns, never blocks): a
    scenario absent from one repetition would otherwise silently give that
    scenario's aggregated cell fewer observations than the others, with no
    signal that it happened. This is an inconsistency warning about the
    REPETITION SET, not an error about any single repetition - a trial
    missing one scenario is still valid for its other scenarios.

    Older/synthetic CSVs (e.g. from simulate_metrics_trial.py, predating
    scenario tagging) may be missing the ground_truth_scenario column
    entirely, not just empty - treated as contributing no scenarios rather
    than raising KeyError. Returns a list of human-readable warnings
    (empty = consistent)."""
    scenarios_by_path = {}
    for path in detail_csv_paths:
        df = pd.read_csv(path)
        if "ground_truth_scenario" not in df.columns:
            scenarios_by_path[path] = set()
            continue
        gt = df[df["ground_truth_room"].notna()]
        scenarios_by_path[path] = set(gt["ground_truth_scenario"].dropna().unique())

    all_scenarios = set()
    common_scenarios = None
    for scenarios in scenarios_by_path.values():
        all_scenarios |= scenarios
        common_scenarios = scenarios if common_scenarios is None else (common_scenarios & scenarios)
    common_scenarios = common_scenarios or set()

    only_in_some = all_scenarios - common_scenarios
    if not only_in_some:
        return []
    details = []
    for scenario in sorted(only_in_some):
        present_in = [os.path.basename(p) for p, scenarios in scenarios_by_path.items() if scenario in scenarios]
        details.append(f"{scenario!r} só em {present_in}")
    return [
        "Cenários não são os mesmos em todas as repetições - uma célula "
        "cujo cenário falte nalguma repetição fica com menos observações "
        "do que as outras, sem sinal nenhum de que isso aconteceu: "
        + "; ".join(details)
    ]


def check_scenario_concentration(gt_df, concentration_threshold=0.5):
    """Different question from check_scenario_consistency: a scenario can
    be present in every repetition and STILL be, in practice, the result
    of one repetition wearing several repetitions' clothing - e.g. n=45
    where 31 come from a single experiment_id. Groups by experiment_id
    (already a column in raw_with_decisions_<label>.csv - no separate
    repetition-label bookkeeping needed) within each scenario, and flags
    any scenario where the single most-represented repetition exceeds
    `concentration_threshold` of that scenario's total.

    gt_df: already filtered by the caller to ground_truth_room notna,
    ground_truth_scenario notna, and (if relevant) a single mac -
    raw_with_decisions_<label>.csv can hold multiple macs, and this
    function has no way to know which one the caller cares about, so it
    trusts gt_df rather than re-deriving its own filter from file paths
    (which risks silently diverging from whatever filter the caller
    already applied for the accuracy numbers themselves).

    Returns {scenario: {"total", "by_experiment": {experiment_id: count},
    "max_share", "dominant_experiment", "concentrated"}} for EVERY
    scenario present, not just the concentrated ones, so callers can
    report the full distribution regardless of the flag."""
    result = {}
    for scenario, sub in gt_df.groupby("ground_truth_scenario"):
        total = len(sub)
        by_experiment = sub.groupby("experiment_id").size().sort_values(ascending=False)
        dominant_experiment = by_experiment.index[0] if len(by_experiment) else None
        max_share = (by_experiment.iloc[0] / total) if total else 0.0
        # Cast away numpy scalar types (int64/float64/bool_) before
        # returning - pandas groupby/.size() leaks them otherwise, and
        # numpy.bool_ fails an `is True`/`is False` identity check even
        # though it's truthy-equal, the kind of friction this project's
        # own _records_with_none (analyze_room_decisions.py) exists to
        # avoid for the same class of problem.
        result[scenario] = {
            "total": int(total),
            "by_experiment": {k: int(v) for k, v in by_experiment.to_dict().items()},
            "max_share": float(max_share),
            "dominant_experiment": dominant_experiment,
            "concentrated": bool(max_share > concentration_threshold),
        }
    return result


def build_repetition_table(records_by_label, mac, metric):
    """{método: {repetition_label: valor|None}} - pivot único de que tudo
    o resto parte. "mac não estava nesta repetição" e "mac sem ground
    truth nesta repetição" ficam ambos None da mesma forma."""
    table = {method: {} for method in METHODS}
    for label, records in records_by_label.items():
        by_method = {r["method"]: r for r in records if r["mac"] == mac}
        for method in METHODS:
            row = by_method.get(method)
            table[method][label] = row.get(metric) if row is not None else None
    return table


def paired_complete_cases(table, method_a, method_b):
    """Só repetições onde AMBOS os métodos têm valor não-None - o
    "mesmos ensaios" do guião não permite zero-preencher nem descartar de
    um lado só."""
    labels_used, xs, ys = [], [], []
    for label in sorted(table[method_a]):
        a = table[method_a][label]
        b = table[method_b].get(label)
        if a is None or b is None:
            continue
        labels_used.append(label)
        xs.append(a)
        ys.append(b)
    return labels_used, xs, ys


def paired_complete_cases_all_methods(table, methods):
    labels_used = [
        label for label in sorted(table[methods[0]])
        if all(table[m].get(label) is not None for m in methods)
    ]
    samples_by_method = {m: [table[m][label] for label in labels_used] for m in methods}
    return labels_used, samples_by_method


def build_repetition_raw_value_rows(records_by_label, macs):
    rows = []
    for mac in macs:
        for method in METHODS:
            for metric in DESCRIPTIVE_METRICS:
                table = build_repetition_table(records_by_label, mac, metric)
                for label in sorted(table[method]):
                    rows.append({
                        "mac": mac, "method": method, "metric": metric,
                        "repetition_label": label, "value": table[method][label],
                    })
    return rows


def build_repetition_descriptive_rows(records_by_label, macs):
    rows = []
    for mac in macs:
        for method in METHODS:
            for metric in DESCRIPTIVE_METRICS:
                table = build_repetition_table(records_by_label, mac, metric)
                labels_used = sorted(l for l, v in table[method].items() if v is not None)
                values = [table[method][l] for l in labels_used]
                stats = descriptive_stats(values)
                rows.append({
                    "mac": mac, "method": method, "metric": metric,
                    "n": stats["n"], "mean": stats["mean"], "std": stats["std"],
                    "sem": stats["sem"], "ci_lower": stats["ci_lower"], "ci_upper": stats["ci_upper"],
                    "median": stats["median"], "p95": stats["p95"], "iqr": stats["iqr"],
                    "min": stats["min"], "max": stats["max"],
                    "repetitions_used": ";".join(labels_used),
                })
    return rows


def build_repetition_wilcoxon_rows(records_by_label, macs, alpha):
    rows = []
    for mac in macs:
        for metric in METRICS_TESTED:
            table = build_repetition_table(records_by_label, mac, metric)
            for method_a, method_b in WILCOXON_PAIRS:
                _, xs, ys = paired_complete_cases(table, method_a, method_b)
                result = pairwise_wilcoxon(xs, ys, alpha=alpha)
                rows.append({
                    "mac": mac, "metric": metric,
                    "method_a": method_a, "method_b": method_b,
                    "adjacent_in_chain": _adjacent_in_chain(method_a, method_b),
                    "vs_final": _vs_final(method_a, method_b),
                    "alpha": alpha,
                    **result,
                })
    return apply_bonferroni(rows, REPETITION_BONFERRONI_M_WILCOXON, alpha=alpha)


def build_repetition_friedman_rows(records_by_label, macs, alpha):
    rows = []
    for mac in macs:
        for metric in METRICS_TESTED:
            table = build_repetition_table(records_by_label, mac, metric)
            _, samples_by_method = paired_complete_cases_all_methods(table, METHODS)
            result = friedman_test(samples_by_method, alpha=alpha)
            rows.append({"mac": mac, "metric": metric, "alpha": alpha, **result})
    return apply_bonferroni(rows, REPETITION_BONFERRONI_M_FRIEDMAN, alpha=alpha)


# ---------------------------------------------------------------------------
# Modo 2 - por transição (exploratório)
# ---------------------------------------------------------------------------

def build_true_intervals_from_detail_csv(rows):
    """rows: lista cronológica de {"time","ground_truth_room"} para UM
    (mac, experiment_id). Substitui analyze_room_decisions.
    build_ground_truth_intervals (que lê a coleção ground_truth do Mongo -
    proibida aqui): deteta mudanças na própria coluna ground_truth_room já
    materializada no CSV. Ver BASELINE_LATENCY_CAVEAT para a consequência
    desta reconstrução na latência do baseline. Linhas com
    ground_truth_room=None são ignoradas na deteção de mudança - marcam
    "fora de qualquer intervalo", nunca uma sala própria."""
    intervals = []
    for row in rows:
        room = row.get("ground_truth_room")
        if room is None:
            continue
        if not intervals or intervals[-1]["room"] != room:
            intervals.append({"room": room, "start": row["time"], "end": None})
    for i in range(len(intervals) - 1):
        intervals[i]["end"] = intervals[i + 1]["start"]
    return intervals


def group_rows_by_mac_experiment(records):
    """Agrupa por (mac, experiment_id), não só por experiment_id - um CSV
    pode conter vários macs, e metrics.match_transitions_to_detections é
    por um único (mac, experiment_id, método) de cada vez."""
    groups = {}
    for row in records:
        groups.setdefault((row.get("mac"), row.get("experiment_id")), []).append(row)
    for key in groups:
        groups[key].sort(key=lambda r: r["time"])  # comparação de strings - segura, "%Y-%m-%d %H:%M:%S" é largura fixa
    return groups


def compute_per_transition_results(records, macs=None):
    """records: _records_with_none()'d de UM raw_with_decisions CSV.
    Devolve uma linha por (mac, experiment_id, transition_index, método):
    detected, latency_sec. Reutiliza metrics.extract_true_transitions /
    match_transitions_to_detections sem alteração - só a FONTE dos
    intervalos de ground truth difere de analyze_room_decisions.py."""
    results = []
    for (mac, experiment_id), rows in group_rows_by_mac_experiment(records).items():
        if macs is not None and mac not in macs:
            continue
        intervals = build_true_intervals_from_detail_csv(rows)
        if len(intervals) < 2:
            continue
        transitions = metrics.extract_true_transitions(intervals)
        for method in METHODS:
            method_rows = [{"time": r["time"], "estimated_room": r.get(f"{method}_room")} for r in rows]
            matches = metrics.match_transitions_to_detections(transitions, method_rows)
            for idx, (transition, match) in enumerate(zip(transitions, matches)):
                results.append({
                    "mac": mac, "experiment_id": experiment_id,
                    "transition_index": idx, "new_room": transition["new_room"],
                    "method": method, "detected": match["detected"], "latency_sec": match["latency_sec"],
                    "latency_is_anchor_artifact": method == "baseline",
                })
    return results


def detection_rate_summary(per_transition_rows):
    """Puramente descritivo - sem teste de significância formal (exigiria
    McNemar para dados binários emparelhados, que o guião não pede)."""
    groups = {}
    for r in per_transition_rows:
        key = (r["mac"], r["experiment_id"], r["method"])
        groups.setdefault(key, []).append(r["detected"])

    rows = []
    for (mac, experiment_id, method), detections in sorted(groups.items()):
        n = len(detections)
        n_detected = sum(1 for d in detections if d)
        rows.append({
            "mac": mac, "experiment_id": experiment_id, "method": method,
            "n_transitions": n, "n_detected": n_detected,
            "detection_rate": (n_detected / n) if n > 0 else None,
        })
    return rows


def _per_transition_table(per_transition_rows, mac, experiment_id, method):
    """{transition_index: latency_sec}, só para transições DETETADAS por
    este método - não detetado nunca vira zero, fica de fora do
    emparelhamento (paired-complete-case)."""
    return {
        r["transition_index"]: r["latency_sec"]
        for r in per_transition_rows
        if r["mac"] == mac and r["experiment_id"] == experiment_id
        and r["method"] == method and r["detected"]
    }


def _paired_complete_transition_latencies(per_transition_rows, mac, experiment_id, method_a, method_b):
    table_a = _per_transition_table(per_transition_rows, mac, experiment_id, method_a)
    table_b = _per_transition_table(per_transition_rows, mac, experiment_id, method_b)
    shared = sorted(set(table_a) & set(table_b))
    xs = [table_a[i] for i in shared]
    ys = [table_b[i] for i in shared]
    return shared, xs, ys


def build_transition_wilcoxon_rows(per_transition_rows, alpha):
    keys = sorted({(r["mac"], r["experiment_id"]) for r in per_transition_rows})
    rows = []
    for mac, experiment_id in keys:
        for metric in PER_TRANSITION_METRICS_TESTED:
            for method_a, method_b in WILCOXON_PAIRS:
                _, xs, ys = _paired_complete_transition_latencies(
                    per_transition_rows, mac, experiment_id, method_a, method_b
                )
                result = pairwise_wilcoxon(xs, ys, alpha=alpha)
                caveat = (
                    BASELINE_LATENCY_CAVEAT
                    if metric == "latency_sec" and "baseline" in (method_a, method_b)
                    else None
                )
                rows.append({
                    "mac": mac, "experiment_id": experiment_id, "metric": metric,
                    "method_a": method_a, "method_b": method_b,
                    "adjacent_in_chain": _adjacent_in_chain(method_a, method_b),
                    "vs_final": _vs_final(method_a, method_b),
                    "alpha": alpha, **result, "caveat": caveat,
                })
    return apply_bonferroni(rows, TRANSITION_BONFERRONI_M_WILCOXON, alpha=alpha)


def build_transition_friedman_rows(per_transition_rows, alpha):
    keys = sorted({(r["mac"], r["experiment_id"]) for r in per_transition_rows})
    rows = []
    for mac, experiment_id in keys:
        for metric in PER_TRANSITION_METRICS_TESTED:
            tables_by_method = {
                method: _per_transition_table(per_transition_rows, mac, experiment_id, method)
                for method in METHODS
            }
            shared = sorted(set.intersection(*(set(tbl) for tbl in tables_by_method.values())))
            samples_by_method = {
                method: [tables_by_method[method][i] for i in shared] for method in METHODS
            }
            result = friedman_test(samples_by_method, alpha=alpha)
            caveat = BASELINE_LATENCY_CAVEAT if metric == "latency_sec" else None
            rows.append({
                "mac": mac, "experiment_id": experiment_id, "metric": metric,
                "alpha": alpha, **result, "caveat": caveat,
            })
    return apply_bonferroni(rows, TRANSITION_BONFERRONI_M_FRIEDMAN, alpha=alpha)


def _label_from_detail_csv(path):
    name = os.path.splitext(os.path.basename(path))[0]
    prefix = "raw_with_decisions_"
    return name[len(prefix):] if name.startswith(prefix) else name


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def cmd_per_repetition(args):
    alpha = args.alpha

    print("Ficheiros de repetição fornecidos:")
    for path in args.summary_csv:
        print(f"  {path}")

    records_by_label = load_repetition_summaries(args.summary_csv)

    print("\nResumo por repetição carregada (confirma antes de continuar):")
    all_macs_seen = set()
    for label, records in records_by_label.items():
        macs_in_file = sorted({r["mac"] for r in records})
        all_macs_seen.update(macs_in_file)
        print(f"  {label}: {len(records)} linhas, macs={macs_in_file}")

    macs = [normalize_mac(m) for m in args.mac] if args.mac else sorted(all_macs_seen)
    n_repetitions = len(records_by_label)
    pairwise_tests_possible = n_repetitions >= 2
    print(f"\n{n_repetitions} repetição(ões) fornecida(s) - testes pareados "
          f"{'vão correr' if pairwise_tests_possible else 'NÃO vão correr (N=1, insuficiente - ver skipped_reason)'}.")

    raw_value_rows = build_repetition_raw_value_rows(records_by_label, macs)
    descriptive_rows = build_repetition_descriptive_rows(records_by_label, macs)
    wilcoxon_rows = build_repetition_wilcoxon_rows(records_by_label, macs, alpha)
    friedman_rows = build_repetition_friedman_rows(records_by_label, macs, alpha)

    os.makedirs(args.output_dir, exist_ok=True)
    label = args.label

    raw_csv = os.path.join(args.output_dir, f"perrepetition_raw_values_{label}.csv")
    desc_csv = os.path.join(args.output_dir, f"perrepetition_descriptive_{label}.csv")
    wilcoxon_csv = os.path.join(args.output_dir, f"perrepetition_wilcoxon_{label}.csv")
    friedman_csv = os.path.join(args.output_dir, f"perrepetition_friedman_{label}.csv")
    metadata_json = os.path.join(args.output_dir, f"perrepetition_metadata_{label}.json")

    pd.DataFrame(raw_value_rows, columns=RAW_VALUES_COLUMNS).to_csv(raw_csv, index=False)
    pd.DataFrame(descriptive_rows, columns=DESCRIPTIVE_COLUMNS).to_csv(desc_csv, index=False)
    pd.DataFrame(wilcoxon_rows, columns=WILCOXON_COLUMNS).to_csv(wilcoxon_csv, index=False)
    pd.DataFrame(friedman_rows, columns=FRIEDMAN_COLUMNS).to_csv(friedman_csv, index=False)

    metadata = {
        "run_timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "mode": "per-repetition",
        "input_files": list(args.summary_csv),
        "repetition_labels": sorted(records_by_label.keys()),
        "macs_analyzed": macs,
        "alpha": alpha,
        "pairwise_tests_possible": pairwise_tests_possible,
        "bonferroni_m_wilcoxon": REPETITION_BONFERRONI_M_WILCOXON,
        "bonferroni_m_friedman": REPETITION_BONFERRONI_M_FRIEDMAN,
        "output_files": {
            "raw_values_csv": raw_csv, "descriptive_csv": desc_csv,
            "wilcoxon_csv": wilcoxon_csv, "friedman_csv": friedman_csv,
        },
    }
    with open(metadata_json, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False, default=str)

    print(f"\nValores brutos: {raw_csv}")
    print(f"Estatística descritiva: {desc_csv}")
    print(f"Wilcoxon: {wilcoxon_csv}")
    print(f"Friedman: {friedman_csv}")
    print(f"Metadados: {metadata_json}")


def cmd_per_transition(args):
    alpha = args.alpha

    print(f"Ficheiro de detalhe: {args.detail_csv}")
    print("AVISO: modo exploratório/piloto - n pequeno (nº de transições reais "
          "dentro de 1 único ensaio), não substitui repetições reais nem é a "
          "unidade de comparação recomendada pelo guião. Ver a coluna 'caveat' "
          "nos CSVs de Wilcoxon/Friedman para o viés da latência do baseline.")

    df = pd.read_csv(args.detail_csv)
    missing = [c for c in REQUIRED_DETAIL_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"{args.detail_csv}: faltam colunas {missing} - é mesmo um raw_with_decisions_<label>.csv?")

    records = _records_with_none(df)
    macs = [normalize_mac(m) for m in args.mac] if args.mac else None

    per_transition_rows = compute_per_transition_results(records, macs=macs)
    if not per_transition_rows:
        print("Nenhuma transição real reconstruída (macs sem ground truth, ou <2 "
              "intervalos por mac/experiment_id) - nada a fazer.")
        return

    detection_rows = detection_rate_summary(per_transition_rows)
    wilcoxon_rows = build_transition_wilcoxon_rows(per_transition_rows, alpha)
    friedman_rows = build_transition_friedman_rows(per_transition_rows, alpha)

    os.makedirs(args.output_dir, exist_ok=True)
    label = args.label or _label_from_detail_csv(args.detail_csv)

    detail_out_csv = os.path.join(args.output_dir, f"pertransition_exploratory_detail_{label}.csv")
    detection_csv = os.path.join(args.output_dir, f"pertransition_exploratory_detection_rate_{label}.csv")
    wilcoxon_csv = os.path.join(args.output_dir, f"pertransition_exploratory_wilcoxon_{label}.csv")
    friedman_csv = os.path.join(args.output_dir, f"pertransition_exploratory_friedman_{label}.csv")
    metadata_json = os.path.join(args.output_dir, f"pertransition_exploratory_metadata_{label}.json")

    pd.DataFrame(per_transition_rows, columns=TRANSITION_DETAIL_COLUMNS).to_csv(detail_out_csv, index=False)
    pd.DataFrame(detection_rows, columns=DETECTION_RATE_COLUMNS).to_csv(detection_csv, index=False)
    pd.DataFrame(wilcoxon_rows, columns=TRANSITION_WILCOXON_COLUMNS).to_csv(wilcoxon_csv, index=False)
    pd.DataFrame(friedman_rows, columns=TRANSITION_FRIEDMAN_COLUMNS).to_csv(friedman_csv, index=False)

    transitions_found = {}
    for mac, experiment_id in sorted({(r["mac"], r["experiment_id"]) for r in per_transition_rows}):
        n_transitions = len({
            r["transition_index"] for r in per_transition_rows
            if r["mac"] == mac and r["experiment_id"] == experiment_id
        })
        transitions_found[f"{mac}|{experiment_id}"] = n_transitions

    metadata = {
        "run_timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "mode": "per-transition",
        "warning": (
            "Modo exploratório/piloto: n pequeno (transições reais dentro de 1 "
            "único ensaio), unidade de comparação diferente da recomendada pelo "
            "guião (por repetição). A latência do método baseline é sempre "
            "0.0s neste modo, por construção - ver 'caveat' nos CSVs de teste."
        ),
        "input_file": args.detail_csv,
        "macs_analyzed": sorted({r["mac"] for r in per_transition_rows}),
        "transitions_found_by_mac_experiment": transitions_found,
        "alpha": alpha,
        "bonferroni_m_wilcoxon": TRANSITION_BONFERRONI_M_WILCOXON,
        "bonferroni_m_friedman": TRANSITION_BONFERRONI_M_FRIEDMAN,
        "output_files": {
            "detail_csv": detail_out_csv, "detection_rate_csv": detection_csv,
            "wilcoxon_csv": wilcoxon_csv, "friedman_csv": friedman_csv,
        },
    }
    with open(metadata_json, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False, default=str)

    print(f"\nDetalhe por transição: {detail_out_csv}")
    print(f"Taxa de deteção: {detection_csv}")
    print(f"Wilcoxon: {wilcoxon_csv}")
    print(f"Friedman: {friedman_csv}")
    print(f"Metadados: {metadata_json}")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    subparsers = parser.add_subparsers(dest="command", required=True)

    rep = subparsers.add_parser("per-repetition", help="Comparação pareada entre repetições (modo principal)")
    rep.add_argument("--summary-csv", nargs="+", required=True,
                      help="Um decision_summary_<label>.csv por repetição do mesmo protocolo")
    rep.add_argument("--mac", nargs="+", default=None)
    rep.add_argument("--label", default="combined")
    rep.add_argument("--alpha", type=float, default=DEFAULT_ALPHA)
    rep.add_argument("--output-dir", default="analysis_output")
    rep.set_defaults(func=cmd_per_repetition)

    trans = subparsers.add_parser("per-transition", help="Comparação exploratória por transição dentro de 1 ensaio")
    trans.add_argument("--detail-csv", required=True, help="Um raw_with_decisions_<label>.csv")
    trans.add_argument("--mac", nargs="+", default=None)
    trans.add_argument("--label", default=None, help="Default: derivado do nome do --detail-csv")
    trans.add_argument("--alpha", type=float, default=DEFAULT_ALPHA)
    trans.add_argument("--output-dir", default="analysis_output")
    trans.set_defaults(func=cmd_per_transition)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
