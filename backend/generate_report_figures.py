"""
Report-ready figures/tables for the guião's "Apresentação e análise dos
resultados" section (docs/Comparação experimental de estratégias simples
de localização BLE.docx.md, linhas 234-514).

Reads ONLY the CSVs analyze_room_decisions.py and statistical_analysis.py
already produce - never touches Mongo, same precedent statistical_analysis.py
already established. Imports METHODS/FINAL_METHOD/WILCOXON_PAIRS/
descriptive_stats/check_consistent_analysis_parameters/check_room_consistency
directly from statistical_analysis.py (pure Python, no pymongo - importing
it doesn't reintroduce the problem statistical_analysis.py itself avoids by
NOT importing analyze_room_decisions.py). Only METHOD_COLORS is duplicated
here (it lives in analyze_room_decisions.py, which does bring pymongo),
alongside a new METHOD_LABELS_PT for report-facing legends.

Rótulos/legendas em português; PNG a 300 DPI (bbox_inches="tight"); cores
por método consistentes com plot_mac's METHOD_COLORS. Regra de aviso a três
níveis por célula (método × métrica) em vez de desenhar dados enganadores -
ver _draw_tiered_bar.

Uso: python generate_report_figures.py <subcomando> --help
"""
import argparse
import os

import matplotlib
matplotlib.use("Agg")  # headless - robust regardless of what backend analyze_room_decisions.py gets away with interactively
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import metrics
from statistical_analysis import (
    METHODS, FINAL_METHOD, descriptive_stats,
    check_consistent_analysis_parameters, check_room_consistency,
    check_scenario_consistency, check_scenario_concentration,
)

plt.rcParams.update({
    "font.size": 12, "axes.titlesize": 14, "axes.labelsize": 12,
    "legend.fontsize": 11, "xtick.labelsize": 10, "ytick.labelsize": 10,
})

# Duplicated from analyze_room_decisions.py (which imports pymongo) rather
# than imported - same precedent statistical_analysis.py already uses for
# its own METHODS list.
METHOD_COLORS = {
    "baseline": "#8a4fd6",
    "median": "#eb6834",
    "median_hysteresis": "#2a78d6",
    "median_hysteresis_persistence": "#1baf7a",
}
METHOD_LABELS_PT = {
    "baseline": "Maior RSSI\ninstantâneo",
    "median": "Mediana\ndo RSSI",
    "median_hysteresis": "Mediana +\nhisterese",
    "median_hysteresis_persistence": "Método\ncombinado",
}
UNKNOWN_ROOM_LABEL = "desconhecida"
# Deliberadamente diferente de UNKNOWN_ROOM_LABEL: "desconhecida" já
# significa beacon inativo (location_status, app.py); um método sem decisão
# com o beacon ativo (ex. aquecimento da persistência) é outra situação.
NO_DECISION_LABEL = "sem decisão"
DPI = 300


def _savefig(fig, path):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    fig.savefig(path, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"Figura escrita: {path}")


def _warn(msg):
    print(f"AVISO: {msg}")


def _print_warnings(warnings, context):
    for w in warnings:
        _warn(f"[{context}] {w}")


# ---------------------------------------------------------------------------
# Regra de aviso a 3 níveis (método × métrica) - nunca uma barra/ponto
# enganador com dados a menos.
# ---------------------------------------------------------------------------

def _draw_tiered_bar(ax, x, row, color, width=0.7):
    """row: dict com n/mean/ci_lower/ci_upper (podem ser None/NaN), ou
    None. n>=2 -> barra+IC95%; n==1 -> barra sem IC, anotação "(n=1)";
    n==0/ausente -> sem barra, marcador "sem dados" (nunca uma barra de
    altura zero - zero é um valor real e plausível). Devolve True se
    desenhou alguma barra (usado pelo chamador para decidir se a figura
    inteira deve ser saltada)."""
    n = row.get("n") if row else None
    mean = row.get("mean") if row else None
    if row is None or not n or mean is None or (isinstance(mean, float) and np.isnan(mean)):
        ax.text(x, 0, "sem dados", ha="center", va="bottom", rotation=90, fontsize=9, color="#888888")
        return False
    if n == 1:
        ax.bar(x, mean, width=width, color=color)
        ax.text(x, mean, " (n=1)", ha="center", va="bottom", fontsize=9)
        return True
    ci_lower, ci_upper = row.get("ci_lower"), row.get("ci_upper")
    yerr = None
    if ci_lower is not None and ci_upper is not None and not (isinstance(ci_lower, float) and np.isnan(ci_lower)):
        yerr = np.array([[mean - ci_lower], [ci_upper - mean]])
    ax.bar(x, mean, width=width, color=color, yerr=yerr, capsize=5)
    return True


# ---------------------------------------------------------------------------
# Leitura/seleção comuns
# ---------------------------------------------------------------------------

def _load_descriptive(path, mac):
    df = pd.read_csv(path)
    macs = sorted(df["mac"].unique())
    if mac is None:
        if len(macs) != 1:
            raise SystemExit(f"--mac obrigatório: {path} tem várias macs {macs}")
        mac = macs[0]
    elif mac not in macs:
        raise SystemExit(f"--mac {mac!r} não encontrado em {path} (macs presentes: {macs})")
    return df[df["mac"] == mac], mac


def _method_row(df, method, metric):
    sub = df[(df["method"] == method) & (df["metric"] == metric)]
    if sub.empty:
        return None
    return sub.iloc[0].to_dict()


def _method_axis(ax):
    ax.set_xticks(range(len(METHODS)))
    ax.set_xticklabels([METHOD_LABELS_PT[m] for m in METHODS])


# ---------------------------------------------------------------------------
# Figura 1 - tabela global de comparação
# ---------------------------------------------------------------------------

GLOBAL_TABLE_METRICS = [
    ("accuracy", "Exatidão", lambda v: f"{v * 100:.1f}%"),
    ("false_movements_per_hour", "Falsos movimentos/hora", lambda v: f"{v:.1f}"),
    ("missed_movement_rate", "Movimentos não detetados", lambda v: f"{v * 100:.1f}%"),
    ("latency_median_sec", "Latência mediana", lambda v: f"{v:.1f} s"),
    ("latency_p95_sec", "Latência p95", lambda v: f"{v:.1f} s"),
    ("pct_time_unknown_or_transition", "Tempo em estado incerto", lambda v: f"{v:.1f}%"),
]


def cmd_global_table(args):
    df, mac = _load_descriptive(args.descriptive_csv, args.mac)
    header = ["Método"] + [label for _, label, _ in GLOBAL_TABLE_METRICS]
    rows = []
    any_data = False
    for method in METHODS:
        row = [METHOD_LABELS_PT[method].replace("\n", " ")]
        for metric, _, fmt in GLOBAL_TABLE_METRICS:
            r = _method_row(df, method, metric)
            value = r["mean"] if r else None
            if value is None or (isinstance(value, float) and np.isnan(value)):
                row.append("sem dados")
            else:
                row.append(fmt(value))
                any_data = True
        rows.append(row)
    if not any_data:
        _warn("global-table: nenhum método tem dados válidos - a saltar a figura.")
        return

    fig, ax = plt.subplots(figsize=(11, 1 + 0.6 * len(rows)))
    ax.axis("off")
    table = ax.table(cellText=rows, colLabels=header, loc="center", cellLoc="center")
    table.auto_set_font_size(False)
    table.set_fontsize(11)
    table.auto_set_column_width(col=list(range(len(header))))
    table.scale(1, 1.8)
    ax.set_title(f"Tabela global de comparação dos métodos - {mac}", pad=20)
    _savefig(fig, os.path.join(args.output_dir, f"tabela_global_{args.label}.png"))

    md_path = os.path.join(args.output_dir, f"tabela_global_{args.label}.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("| " + " | ".join(header) + " |\n")
        f.write("|" + "|".join(["---"] * len(header)) + "|\n")
        for row in rows:
            f.write("| " + " | ".join(row) + " |\n")
    print(f"Tabela (markdown) escrita: {md_path}")


# ---------------------------------------------------------------------------
# Figuras 2/3 - barras (exatidão / falsos movimentos por hora)
# ---------------------------------------------------------------------------

def _bar_figure(descriptive_csv, mac_arg, metric, ylabel, title, filename, output_dir, label):
    df, mac = _load_descriptive(descriptive_csv, mac_arg)
    fig, ax = plt.subplots(figsize=(8, 6))
    any_bar = False
    for i, method in enumerate(METHODS):
        row = _method_row(df, method, metric)
        drawn = _draw_tiered_bar(ax, i, row, METHOD_COLORS[method])
        any_bar = any_bar or drawn
    if not any_bar:
        plt.close(fig)
        _warn(f"{filename}: nenhum método tem dados válidos para {metric} - a saltar a figura.")
        return
    _method_axis(ax)
    ax.set_ylabel(ylabel)
    ax.set_title(f"{title} - {mac}")
    ax.axhline(0, color="#333333", linewidth=0.8)
    _savefig(fig, os.path.join(output_dir, f"{filename}_{label}.png"))


def cmd_accuracy_bar(args):
    _bar_figure(
        args.descriptive_csv, args.mac, "accuracy",
        "Exatidão", "Exatidão da localização por método",
        "barras_exatidao", args.output_dir, args.label,
    )


def cmd_false_movements_bar(args):
    _bar_figure(
        args.descriptive_csv, args.mac, "false_movements_per_hour",
        "Falsos movimentos por hora", "Falsos movimentos por hora, por método",
        "barras_falsos_movimentos", args.output_dir, args.label,
    )


# ---------------------------------------------------------------------------
# Figura 5 - dispersão fiabilidade vs. latência
# ---------------------------------------------------------------------------

def cmd_reliability_scatter(args):
    df, mac = _load_descriptive(args.descriptive_csv, args.mac)
    fig, ax = plt.subplots(figsize=(8, 6))
    any_point = False
    for method in METHODS:
        lat_row = _method_row(df, method, "latency_median_sec")
        fm_row = _method_row(df, method, "false_movements_per_hour")
        lat, fm = (lat_row or {}).get("mean"), (fm_row or {}).get("mean")
        if lat is None or fm is None or (isinstance(lat, float) and np.isnan(lat)):
            _warn(f"reliability-scatter: sem dados para {method} - ponto omitido.")
            continue
        ax.scatter(lat, fm, color=METHOD_COLORS[method], s=120, zorder=3, label=METHOD_LABELS_PT[method].replace("\n", " "))
        any_point = True
    if not any_point:
        plt.close(fig)
        _warn("reliability-scatter: nenhum método tem dados válidos - a saltar a figura.")
        return
    ax.set_xlabel("Latência mediana (s)")
    ax.set_ylabel("Falsos movimentos por hora")
    ax.set_title(f"Compromisso entre fiabilidade e latência - {mac}\n(canto inferior esquerdo é o ideal)")
    ax.legend()
    _savefig(fig, os.path.join(args.output_dir, f"dispersao_fiabilidade_latencia_{args.label}.png"))


# ---------------------------------------------------------------------------
# Figura 4 - boxplot da latência de confirmação (todas as transições)
# ---------------------------------------------------------------------------

def cmd_latency_boxplot(args):
    frames = [pd.read_csv(p) for p in args.latency_csv]
    combined = pd.concat(frames, ignore_index=True)
    mac = args.mac
    if mac is None:
        macs = sorted(combined["mac"].unique())
        if len(macs) != 1:
            raise SystemExit(f"--mac obrigatório: entradas têm várias macs {macs}")
        mac = macs[0]
    combined = combined[(combined["mac"] == mac) & (combined["detected"] == True)]  # noqa: E712

    data, positions, colors, table_rows = [], [], [], []
    for i, method in enumerate(METHODS):
        values = combined.loc[combined["method"] == method, "latency_sec"].dropna().tolist()
        if not values:
            _warn(f"latency-boxplot: sem transições detetadas para {method} - posição vazia.")
            continue
        data.append(values)
        positions.append(i)
        colors.append(METHOD_COLORS[method])
        summary = metrics.summarize_latencies(values)
        table_rows.append([
            METHOD_LABELS_PT[method].replace("\n", " "), f"{summary['median']:.1f}",
            f"{np.percentile(values, 25):.1f}", f"{np.percentile(values, 75):.1f}",
            f"{summary['p95']:.1f}", f"{summary['max']:.1f}",
        ])

    if not data:
        _warn("latency-boxplot: nenhuma transição detetada em nenhum método - a saltar a figura.")
        return

    fig, ax = plt.subplots(figsize=(8, 6))
    bp = ax.boxplot(data, positions=positions, widths=0.6, patch_artist=True)
    for patch, color in zip(bp["boxes"], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.7)
    ax.set_xticks(range(len(METHODS)))
    ax.set_xticklabels([METHOD_LABELS_PT[m] for m in METHODS])
    for i, method in enumerate(METHODS):
        if i not in positions:
            ax.text(i, 0, "sem dados", ha="center", va="bottom", rotation=90, fontsize=9, color="#888888")
    ax.set_ylabel("Latência de confirmação (s)")
    ax.set_title(f"Latência de confirmação por método (todas as transições) - {mac}")
    _savefig(fig, os.path.join(args.output_dir, f"boxplot_latencia_{args.label}.png"))

    md_path = os.path.join(args.output_dir, f"boxplot_latencia_{args.label}.md")
    with open(md_path, "w", encoding="utf-8") as f:
        header = ["Método", "Mediana", "Q1", "Q3", "p95", "Máximo"]
        f.write("| " + " | ".join(header) + " |\n")
        f.write("|" + "|".join(["---"] * len(header)) + "|\n")
        for row in table_rows:
            f.write("| " + " | ".join(row) + " |\n")
    print(f"Tabela (markdown) escrita: {md_path}")


# ---------------------------------------------------------------------------
# Figura 6 - matriz de confusão (sala real x sala estimada)
# ---------------------------------------------------------------------------

def _draw_confusion_grid(df, mac, title_suffix, output_path):
    df = df[df["mac"] == mac] if mac else df
    all_real = sorted(df["real_room"].dropna().unique())
    all_estimated = sorted(set(df["estimated_room"].dropna().unique()) | {UNKNOWN_ROOM_LABEL})

    fig, axes = plt.subplots(2, 2, figsize=(14, 12))
    for ax, method in zip(axes.flat, METHODS):
        sub = df[df["method"] == method]
        pivot = sub.pivot_table(index="real_room", columns="estimated_room", values="count", aggfunc="sum")
        pivot = pivot.reindex(index=all_real, columns=all_estimated)
        row_totals = pivot.sum(axis=1)
        pct = pivot.div(row_totals, axis=0) * 100.0

        display = pct.to_numpy(dtype=float)
        masked = np.ma.masked_invalid(display)
        cmap = plt.cm.Blues.copy()
        cmap.set_bad(color="#dddddd")  # linha sem dados (total=0) - cinza sólido, distinto de "0%" (Colormap.set_bad não aceita hatch; a anotação "sem dados" por célula, abaixo, já garante a distinção)
        im = ax.imshow(masked, cmap=cmap, vmin=0, vmax=100, aspect="auto")
        ax.set_xticks(range(len(all_estimated)))
        ax.set_xticklabels(all_estimated, rotation=45, ha="right")
        ax.set_yticks(range(len(all_real)))
        ax.set_yticklabels(all_real)
        ax.set_xlabel("Sala estimada")
        ax.set_ylabel("Sala real")
        ax.set_title(METHOD_LABELS_PT[method].replace("\n", " "))
        for i in range(len(all_real)):
            for j in range(len(all_estimated)):
                val = display[i, j]
                if np.isnan(val):
                    ax.text(j, i, "sem dados", ha="center", va="center", fontsize=8, color="#666666")
                else:
                    ax.text(j, i, f"{val:.0f}%", ha="center", va="center",
                            fontsize=9, color="white" if val > 50 else "black")
    fig.suptitle(f"Matriz de confusão (sala real vs. estimada) - {title_suffix}", fontsize=16)
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    _savefig(fig, output_path)


def cmd_confusion_matrix(args):
    if args.pool:
        warnings = check_room_consistency(args.confusion_csv)
        _print_warnings(warnings, "confusion-matrix --pool")
        frames = [pd.read_csv(p) for p in args.confusion_csv]
        combined = pd.concat(frames, ignore_index=True)
        combined = combined.groupby(["mac", "method", "real_room", "estimated_room"], as_index=False)["count"].sum()
        mac = args.mac
        if mac is None:
            macs = sorted(combined["mac"].unique())
            if len(macs) != 1:
                raise SystemExit(f"--mac obrigatório: entradas têm várias macs {macs}")
            mac = macs[0]
        label = f"{args.label}_pool"
        _draw_confusion_grid(combined, mac, f"{mac}, agregado ({len(args.confusion_csv)} repetições)",
                              os.path.join(args.output_dir, f"matriz_confusao_{label}.png"))
    else:
        for path in args.confusion_csv:
            df = pd.read_csv(path)
            mac = args.mac
            if mac is None:
                macs = sorted(df["mac"].unique())
                if len(macs) != 1:
                    raise SystemExit(f"--mac obrigatório: {path} tem várias macs {macs}")
                mac = macs[0]
            run_label = os.path.splitext(os.path.basename(path))[0].replace("confusion_matrix_", "")
            _draw_confusion_grid(df, mac, f"{mac}, {run_label}",
                                  os.path.join(args.output_dir, f"matriz_confusao_{run_label}.png"))


# ---------------------------------------------------------------------------
# Figura 7 - RSSI ao longo do tempo durante uma transição
# ---------------------------------------------------------------------------

def cmd_rssi_timeline(args):
    latency_df = pd.read_csv(args.latency_csv)
    latency_df = latency_df[latency_df["mac"] == args.mac]
    if args.experiment_id:
        latency_df = latency_df[latency_df["experiment_id"] == args.experiment_id]

    if args.start and args.end:
        window_start, window_end = args.start, args.end
        transition_time, experiment_id, new_room = None, args.experiment_id, None
    else:
        candidates = latency_df[["experiment_id", "transition_index", "new_room", "transition_time"]].drop_duplicates()
        candidates = candidates.sort_values(["experiment_id", "transition_index"])
        if args.transition_index >= len(candidates):
            raise SystemExit(f"--transition-index {args.transition_index} fora de alcance (só {len(candidates)} transições disponíveis).")
        chosen = candidates.iloc[args.transition_index]
        experiment_id, new_room, transition_time = chosen["experiment_id"], chosen["new_room"], chosen["transition_time"]

        confirmations = latency_df[
            (latency_df["experiment_id"] == experiment_id) & (latency_df["transition_index"] == chosen["transition_index"])
        ]
        window_start = (pd.Timestamp(transition_time) - pd.Timedelta(seconds=args.window_sec)).strftime("%Y-%m-%d %H:%M:%S")
        latest_confirmation = confirmations["confirmation_time"].dropna()
        end_anchor = pd.Timestamp(latest_confirmation.max()) if not latest_confirmation.empty else pd.Timestamp(transition_time)
        window_end = (end_anchor + pd.Timedelta(seconds=args.window_sec)).strftime("%Y-%m-%d %H:%M:%S")

    detail_df = pd.read_csv(args.detail_csv)
    detail_df = detail_df[(detail_df["mac"] == args.mac)]
    if experiment_id is not None:
        detail_df = detail_df[detail_df["experiment_id"] == experiment_id]
    # Comparação de strings primeiro (janela, formato ordenável, convenção
    # do resto do projeto), SÓ DEPOIS convertida para datetime - o eixo X
    # do matplotlib trata strings como categorias na ordem em que aparecem
    # em cada série, não por ordem cronológica: sem esta conversão, as
    # várias séries (por nó, por método) ficam com escalas X inconsistentes
    # entre si e os rótulos saem embaralhados.
    detail_df = detail_df[(detail_df["effective_time"] >= window_start) & (detail_df["effective_time"] <= window_end)]
    if detail_df.empty:
        _warn("rssi-timeline: nenhuma deteção na janela escolhida - a saltar a figura.")
        return
    detail_df = detail_df.sort_values("effective_time")
    detail_df["effective_time"] = pd.to_datetime(detail_df["effective_time"])

    fig, axes = plt.subplots(2, 1, figsize=(12, 9), sharex=True, height_ratios=[2, 1.5])
    ax_rssi, ax_rooms = axes

    esp_ids = sorted(detail_df["esp_id"].dropna().unique())
    node_colors = plt.cm.tab10(np.linspace(0, 1, max(len(esp_ids), 1)))
    for esp_id, color in zip(esp_ids, node_colors):
        sub = detail_df[detail_df["esp_id"] == esp_id]
        ax_rssi.plot(sub["effective_time"], sub["raw_rssi"], marker="o", markersize=3, color=color, label=esp_id)
    ax_rssi.set_ylabel("RSSI (dBm)")
    ax_rssi.legend(title="Nó (esp_id)")
    ax_rssi.set_title(f"RSSI por nó durante uma transição - {args.mac}, {experiment_id or ''}")

    all_rooms = sorted(set(detail_df["ground_truth_room"].dropna().unique()) |
                        set().union(*(set(detail_df[f"{m}_room"].dropna().unique()) for m in METHODS)))
    room_y = {room: i for i, room in enumerate(all_rooms)}

    gt = detail_df[detail_df["ground_truth_room"].notna()]
    if not gt.empty:
        ax_rooms.step(gt["effective_time"], gt["ground_truth_room"].map(room_y), where="post",
                      color="black", linewidth=2.5, label="Real", zorder=5)

    for method in METHODS:
        col = f"{method}_room"
        sub = detail_df[detail_df[col].notna()]
        if sub.empty:
            continue
        ax_rooms.step(sub["effective_time"], sub[col].map(room_y), where="post",
                      color=METHOD_COLORS[method], linewidth=1.5, alpha=0.8,
                      label=METHOD_LABELS_PT[method].replace("\n", " "))

    # Instantes de confirmação reais (transition_latencies_<label>.csv, não
    # reconstruídos do CSV de detalhe) - por isso sem o artefacto do
    # baseline e sem precisar de ressalva.
    if transition_time is not None:
        ax_rooms.axvline(pd.Timestamp(transition_time), color="black", linestyle=":", linewidth=1.5, label="Instante da transição real")
        for _, row in confirmations.iterrows():
            if pd.notna(row["confirmation_time"]):
                ax_rooms.axvline(pd.Timestamp(row["confirmation_time"]), color=METHOD_COLORS[row["method"]],
                                  linestyle="--", linewidth=1.2, alpha=0.8)

    ax_rooms.set_yticks(list(room_y.values()))
    ax_rooms.set_yticklabels(list(room_y.keys()))
    ax_rooms.set_ylabel("Sala")
    ax_rooms.set_xlabel("Hora")
    ax_rooms.legend(fontsize=9, loc="upper left", bbox_to_anchor=(1.01, 1))
    for ax in axes:
        ax.tick_params(axis="x", rotation=45)

    _savefig(fig, os.path.join(args.output_dir, f"rssi_timeline_{args.label}.png"))


# ---------------------------------------------------------------------------
# Figura 8 - varredura de parâmetro
# ---------------------------------------------------------------------------

SWEEP_METRIC_LABELS = {
    "accuracy": "Exatidão",
    "false_movements_per_hour": "Falsos movimentos/hora",
    "latency_median_sec": "Latência mediana (s)",
}


def cmd_parameter_sweep(args):
    df = pd.read_csv(args.sweep_csv)
    parameter_names = sorted(df["parameter"].unique())
    if len(parameter_names) != 1:
        raise SystemExit(f"{args.sweep_csv} mistura mais do que um parâmetro varrido: {parameter_names}")
    parameter = parameter_names[0]

    metrics_present = [m for m in SWEEP_METRIC_LABELS if m in df["metric"].unique()]
    fig, axes = plt.subplots(1, len(metrics_present), figsize=(6 * len(metrics_present), 5), squeeze=False)
    axes = axes[0]

    for ax, metric in zip(axes, metrics_present):
        any_line = False
        for method in METHODS:
            sub = df[(df["method"] == method) & (df["metric"] == metric)].sort_values("parameter_value")
            sub = sub.dropna(subset=["mean"])
            if sub.empty:
                continue
            ax.plot(sub["parameter_value"], sub["mean"], marker="o", color=METHOD_COLORS[method],
                    label=METHOD_LABELS_PT[method].replace("\n", " "))
            has_ci = sub["ci_lower"].notna() & sub["ci_upper"].notna()
            if has_ci.any():
                ax.fill_between(sub["parameter_value"], sub["ci_lower"], sub["ci_upper"],
                                 color=METHOD_COLORS[method], alpha=0.15)
            any_line = True
        if not any_line:
            _warn(f"parameter-sweep: sem dados para a métrica {metric} - painel deixado vazio.")
        ax.set_xlabel(parameter)
        ax.set_ylabel(SWEEP_METRIC_LABELS[metric])
    axes[0].legend(fontsize=9)
    fig.suptitle(f"Influência de {parameter} nos métodos")
    _savefig(fig, os.path.join(args.output_dir, f"varredura_{parameter}_{args.label}.png"))


# ---------------------------------------------------------------------------
# Figura 9 - exatidão por cenário
# ---------------------------------------------------------------------------

LOW_N_COLOR = "#fff3cd"          # âmbar claro - poucas observações (convenção, não fronteira estatística)
CONCENTRATED_COLOR = "#f8d7da"   # vermelho/rosa claro - célula dominada por uma repetição (problema diferente do N)
BOTH_FLAGS_COLOR = "#e2d9f3"     # roxo claro - os dois problemas ao mesmo tempo, para não ficar ambíguo qual se aplica


def cmd_scenario_table(args):
    warnings = check_consistent_analysis_parameters(args.detail_csv, prefix="raw_with_decisions_")
    _print_warnings(warnings, "scenario-table")
    warnings = check_scenario_consistency(args.detail_csv)
    _print_warnings(warnings, "scenario-table")

    frames = [pd.read_csv(p) for p in args.detail_csv]
    combined = pd.concat(frames, ignore_index=True)
    if args.mac:
        combined = combined[combined["mac"] == args.mac]
    gt = combined[combined["ground_truth_room"].notna()]
    if "ground_truth_scenario" not in gt.columns or gt["ground_truth_scenario"].dropna().empty:
        _warn("scenario-table: nenhuma marcação de ground truth tem 'scenario' definido - a saltar a figura.")
        return

    gt = gt[gt["ground_truth_scenario"].notna()]
    scenarios = sorted(gt["ground_truth_scenario"].unique())

    # Concentração só faz sentido como aviso quando há mais do que uma
    # repetição a agregar - com 1 única repetição, max_share=1.0 por
    # definição (não há nada para comparar), e marcar isso seria ruído,
    # não sinal. check_scenario_concentration em si fica sempre correta/
    # pura (é um cálculo honesto mesmo a n=1); é aqui, na apresentação,
    # que se decide não usar esse resultado nesse caso.
    n_repetitions_overall = gt["experiment_id"].nunique()
    concentration_by_scenario = check_scenario_concentration(gt, args.concentration_threshold)
    if n_repetitions_overall > 1:
        for scenario, info in concentration_by_scenario.items():
            if info["concentrated"]:
                _warn(
                    f"[scenario-table] Cenário {scenario!r}: {info['by_experiment'][info['dominant_experiment']]}/"
                    f"{info['total']} ({info['max_share'] * 100:.1f}%) vêm de uma única repetição "
                    f"({info['dominant_experiment']}) - distribuição: {info['by_experiment']}"
                )

    header = ["Cenário"] + [METHOD_LABELS_PT[m].replace("\n", " ") for m in METHODS]
    rows = []
    flagged_rows = {}  # row_idx -> "low_n" | "concentrated" | "both"
    for row_idx, scenario in enumerate(scenarios):
        sub = gt[gt["ground_truth_scenario"] == scenario]
        total = len(sub)

        low_n = 0 < total < args.min_observations
        concentrated = n_repetitions_overall > 1 and concentration_by_scenario.get(scenario, {}).get("concentrated", False)
        markers = ("*" if low_n else "") + ("†" if concentrated else "")
        label = f"{scenario} (n={total})" + (f" {markers}" if markers else "")
        if low_n and concentrated:
            flagged_rows[row_idx] = "both"
        elif low_n:
            flagged_rows[row_idx] = "low_n"
        elif concentrated:
            flagged_rows[row_idx] = "concentrated"

        row = [label]
        for method in METHODS:
            # Replica exatamente a regra de exatidão de
            # metrics.compute_ground_truth_metrics: linha não decidida
            # (estimated_room None) com ground truth conhecido conta
            # como errada, nunca é excluída do denominador. Confirmado
            # empiricamente (não só por leitura de código) que esta é a
            # MESMA convenção usada em decision_summary_<label>.csv's
            # accuracy - ver Contexto do plano.
            correct = (sub[f"{method}_room"] == sub["ground_truth_room"]).sum()
            row.append(f"{correct / total * 100:.1f}%" if total else "sem dados")
        rows.append(row)

    fig, ax = plt.subplots(figsize=(10, 1.6 + 0.6 * len(rows)))
    ax.axis("off")
    table = ax.table(cellText=rows, colLabels=header, loc="center", cellLoc="center")
    table.auto_set_font_size(False)
    table.set_fontsize(11)
    table.auto_set_column_width(col=list(range(len(header))))
    table.scale(1, 1.8)

    flag_colors = {"low_n": LOW_N_COLOR, "concentrated": CONCENTRATED_COLOR, "both": BOTH_FLAGS_COLOR}
    for row_idx, flag in flagged_rows.items():
        for col in range(len(header)):
            table[(row_idx + 1, col)].set_facecolor(flag_colors[flag])  # +1: linha 0 da tabela é o cabeçalho

    ax.set_title("Exatidão por cenário e método")
    footnote_lines = []
    if any(f in ("low_n", "both") for f in flagged_rows.values()):
        footnote_lines.append(
            f"* menos de {args.min_observations} observações - convenção para sinalizar poucas "
            "observações, não um critério de validade estatística."
        )
    if any(f in ("concentrated", "both") for f in flagged_rows.values()):
        footnote_lines.append(
            f"† mais de {args.concentration_threshold * 100:.0f}% das observações vêm de uma única "
            "repetição - célula não genuinamente agregada; ver consola para a distribuição completa."
        )
    if footnote_lines:
        fig.text(0.5, 0.01, "\n".join(footnote_lines), ha="center", fontsize=9, color="#555555")

    _savefig(fig, os.path.join(args.output_dir, f"tabela_cenarios_{args.label}.png"))


# ---------------------------------------------------------------------------
# Figura extra - exatidão por posição (guião novo, protocolo de 75 ensaios)
# ---------------------------------------------------------------------------
# Quase uma cópia de cmd_scenario_table - reutiliza check_scenario_consistency/
# check_scenario_concentration com column/group_column="trial_position" em
# vez de reimplementar a mesma agregação/regra de aviso.

def cmd_position_table(args):
    warnings = check_consistent_analysis_parameters(args.detail_csv, prefix="raw_with_decisions_")
    _print_warnings(warnings, "position-table")
    warnings = check_scenario_consistency(args.detail_csv, column="trial_position", label="Posições")
    _print_warnings(warnings, "position-table")

    frames = [pd.read_csv(p) for p in args.detail_csv]
    combined = pd.concat(frames, ignore_index=True)
    if args.mac:
        combined = combined[combined["mac"] == args.mac]
    gt = combined[combined["ground_truth_room"].notna()]
    if "trial_position" not in gt.columns or gt["trial_position"].dropna().empty:
        _warn("position-table: nenhuma marcação de ground truth tem 'trial_position' reconhecido "
              "(experiment_id fora da convenção EST-<posição>-R<n>) - a saltar a figura.")
        return

    gt = gt[gt["trial_position"].notna()]
    positions = sorted(gt["trial_position"].unique())

    # Mesma justificação de cmd_scenario_table: com 1 única repetição
    # agregada, max_share=1.0 por definição - marcar isso seria ruído.
    n_repetitions_overall = gt["experiment_id"].nunique()
    concentration_by_position = check_scenario_concentration(
        gt, args.concentration_threshold, group_column="trial_position"
    )
    if n_repetitions_overall > 1:
        for position, info in concentration_by_position.items():
            if info["concentrated"]:
                _warn(
                    f"[position-table] Posição {position!r}: {info['by_experiment'][info['dominant_experiment']]}/"
                    f"{info['total']} ({info['max_share'] * 100:.1f}%) vêm de uma única repetição "
                    f"({info['dominant_experiment']}) - distribuição: {info['by_experiment']}"
                )

    header = ["Posição"] + [METHOD_LABELS_PT[m].replace("\n", " ") for m in METHODS]
    rows = []
    flagged_rows = {}
    for row_idx, position in enumerate(positions):
        sub = gt[gt["trial_position"] == position]
        total = len(sub)

        low_n = 0 < total < args.min_observations
        concentrated = n_repetitions_overall > 1 and concentration_by_position.get(position, {}).get("concentrated", False)
        markers = ("*" if low_n else "") + ("†" if concentrated else "")
        label = f"{position} (n={total})" + (f" {markers}" if markers else "")
        if low_n and concentrated:
            flagged_rows[row_idx] = "both"
        elif low_n:
            flagged_rows[row_idx] = "low_n"
        elif concentrated:
            flagged_rows[row_idx] = "concentrated"

        row = [label]
        for method in METHODS:
            # Mesma regra de exatidão de metrics.compute_ground_truth_metrics
            # (e de cmd_scenario_table): linha não decidida conta como
            # errada, nunca é excluída do denominador.
            correct = (sub[f"{method}_room"] == sub["ground_truth_room"]).sum()
            row.append(f"{correct / total * 100:.1f}%" if total else "sem dados")
        rows.append(row)

    fig, ax = plt.subplots(figsize=(10, 1.6 + 0.6 * len(rows)))
    ax.axis("off")
    table = ax.table(cellText=rows, colLabels=header, loc="center", cellLoc="center")
    table.auto_set_font_size(False)
    table.set_fontsize(11)
    table.auto_set_column_width(col=list(range(len(header))))
    table.scale(1, 1.8)

    flag_colors = {"low_n": LOW_N_COLOR, "concentrated": CONCENTRATED_COLOR, "both": BOTH_FLAGS_COLOR}
    for row_idx, flag in flagged_rows.items():
        for col in range(len(header)):
            table[(row_idx + 1, col)].set_facecolor(flag_colors[flag])

    ax.set_title("Exatidão por posição e método")
    footnote_lines = []
    if any(f in ("low_n", "both") for f in flagged_rows.values()):
        footnote_lines.append(
            f"* menos de {args.min_observations} observações - convenção para sinalizar poucas "
            "observações, não um critério de validade estatística."
        )
    if any(f in ("concentrated", "both") for f in flagged_rows.values()):
        footnote_lines.append(
            f"† mais de {args.concentration_threshold * 100:.0f}% das observações vêm de uma única "
            "repetição - célula não genuinamente agregada; ver consola para a distribuição completa."
        )
    if footnote_lines:
        fig.text(0.5, 0.01, "\n".join(footnote_lines), ha="center", fontsize=9, color="#555555")

    _savefig(fig, os.path.join(args.output_dir, f"tabela_posicoes_{args.label}.png"))


# ---------------------------------------------------------------------------
# Resumo estático/dinâmico (guião novo, protocolo de 75 ensaios)
# ---------------------------------------------------------------------------
# Não recalcula nada - só junta as métricas já em decision_summary com
# trial_type/trial_position/duração já derivadas em raw_with_decisions.
# CSV, não figura: até 75 ensaios x 4 métodos não cabe numa tabela desenhada
# como as das figuras 1/9.

def cmd_trial_type_summary(args):
    warnings = check_consistent_analysis_parameters(args.summary_csv, prefix="decision_summary_")
    _print_warnings(warnings, "trial-type-summary")

    trial_info = {}  # experiment_id -> {"trial_type", "trial_position", "duration_sec"}
    for path in args.detail_csv:
        df = pd.read_csv(path)
        if "trial_type" not in df.columns:
            continue
        for experiment_id, exp_df in df.groupby("experiment_id"):
            trial_type = exp_df["trial_type"].iloc[0]
            if pd.isna(trial_type):
                continue
            trial_position = exp_df["trial_position"].iloc[0]
            times = pd.to_datetime(exp_df["effective_time"]).sort_values()
            duration_sec = (times.iloc[-1] - times.iloc[0]).total_seconds()
            trial_info[experiment_id] = {
                "trial_type": trial_type,
                "trial_position": trial_position if pd.notna(trial_position) else None,
                "duration_sec": duration_sec,
            }

    if not trial_info:
        _warn("trial-type-summary: nenhum --detail-csv tem 'trial_type' reconhecido - a saltar.")
        return

    rows = []
    invariant_violations = []
    for path in args.summary_csv:
        experiment_id = os.path.splitext(os.path.basename(path))[0].replace("decision_summary_", "")
        info = trial_info.get(experiment_id)
        if info is None:
            continue  # sem --detail-csv correspondente fornecido, ou fora da convenção

        df = pd.read_csv(path)
        if args.mac:
            df = df[df["mac"] == args.mac]

        for r in df.itertuples():
            entry = {
                "experiment_id": experiment_id,
                "trial_type": info["trial_type"],
                "trial_position": info["trial_position"],
                "mac": r.mac,
                "method": r.method,
                "num_transitions": r.num_transitions,
            }
            if info["trial_type"] == "static":
                duration_min = (info["duration_sec"] / 60.0) if info["duration_sec"] else None
                entry["location_changes_per_min"] = (
                    r.num_transitions / duration_min if duration_min else None
                )
                num_false = r.num_false_movements
                # A false movement is always also a transition, never the
                # reverse - violating this means one of the two counts has
                # a bug, not that the trial is unusually unstable.
                if pd.notna(num_false) and pd.notna(r.num_transitions) and num_false > r.num_transitions:
                    invariant_violations.append(
                        f"{experiment_id} ({r.mac}, {r.method}): num_false_movements={num_false} > "
                        f"num_transitions={r.num_transitions} - impossível, sinal de bug."
                    )
                entry["num_false_movements"] = num_false
                entry["recoveries_to_correct"] = (
                    (r.num_transitions - num_false)
                    if pd.notna(num_false) and pd.notna(r.num_transitions) else None
                )
                entry["accuracy"] = r.accuracy
            else:  # dynamic
                entry["accuracy"] = r.accuracy
                entry["latency_median_sec"] = r.latency_median_sec
                entry["latency_p95_sec"] = r.latency_p95_sec
                entry["num_false_movements"] = r.num_false_movements
                entry["false_movements_per_hour"] = r.false_movements_per_hour
                entry["missed_movement_rate"] = r.missed_movement_rate
            rows.append(entry)

    if invariant_violations:
        for v in invariant_violations:
            _warn(f"[trial-type-summary] INVARIANTE VIOLADO: {v}")

    if not rows:
        _warn("trial-type-summary: nenhuma linha combinável (summary/detail sem experiment_id em comum) - a saltar.")
        return

    os.makedirs(args.output_dir, exist_ok=True)
    csv_path = os.path.join(args.output_dir, f"resumo_estatico_dinamico_{args.label}.csv")
    pd.DataFrame(rows).to_csv(csv_path, index=False)
    print(f"Resumo estático/dinâmico escrito: {csv_path}")
    if invariant_violations:
        print(f"({len(invariant_violations)} violação(ões) do invariante - ver avisos acima)")


# ---------------------------------------------------------------------------
# Distribuição da sala decidida nas posições de fronteira (P1/P2) - "preferência
# sistemática por um dos nós", sem depender de ground truth (não existe
# nessas posições, por desenho). Ao contrário de cmd_position_table (que
# filtra ground_truth_room.notna() e por isso exclui P1/P2 por completo),
# aqui não há nenhum filtro de ground truth - o denominador é toda e
# qualquer deteção nessas posições.
# ---------------------------------------------------------------------------

def cmd_doorway_distribution(args):
    warnings = check_consistent_analysis_parameters(args.detail_csv, prefix="raw_with_decisions_")
    _print_warnings(warnings, "doorway-distribution")
    # require_ground_truth=False - ver check_scenario_consistency, P1/P2
    # nunca têm ground_truth_room.
    warnings = check_scenario_consistency(
        args.detail_csv, column="trial_position", label="Posições (fronteira)", require_ground_truth=False
    )
    _print_warnings(warnings, "doorway-distribution")

    frames = [pd.read_csv(p) for p in args.detail_csv]
    combined = pd.concat(frames, ignore_index=True)

    macs_present = sorted(combined["mac"].dropna().unique())
    if args.mac:
        combined = combined[combined["mac"] == args.mac]
    elif len(macs_present) > 1:
        # Mais estrito que scenario-table/position-table (que pooliam vários
        # macs em silêncio): misturar beacons diferentes tornaria a pergunta
        # sobre assimetria de UM beacon enganadora.
        raise SystemExit(f"--mac obrigatório: os ficheiros dados têm vários macs {macs_present}")

    if "trial_position" not in combined.columns:
        _warn("doorway-distribution: coluna 'trial_position' ausente (dados anteriores à convenção EST-/DIN-) - a saltar.")
        return

    combined = combined[combined["trial_position"].isin(args.positions)]
    if combined.empty:
        _warn(f"doorway-distribution: nenhuma linha com trial_position em {args.positions} - a saltar.")
        return

    n_repetitions_overall = combined["experiment_id"].nunique()
    concentration_by_position = check_scenario_concentration(
        combined, args.concentration_threshold, group_column="trial_position"
    )
    if n_repetitions_overall > 1:
        for position, info in concentration_by_position.items():
            if info["concentrated"]:
                _warn(
                    f"[doorway-distribution] Posição {position!r}: {info['by_experiment'][info['dominant_experiment']]}/"
                    f"{info['total']} ({info['max_share'] * 100:.1f}%) vêm de uma única repetição "
                    f"({info['dominant_experiment']}) - distribuição: {info['by_experiment']}"
                )

    positions = sorted(set(args.positions) & set(combined["trial_position"].unique()))
    rows = []
    position_flags = {}  # position -> "low_n" | "concentrated" | "both" | None
    for position in positions:
        pos_df = combined[combined["trial_position"] == position]
        total_n = len(pos_df)
        low_n = 0 < total_n < args.min_observations
        concentrated = n_repetitions_overall > 1 and concentration_by_position.get(position, {}).get("concentrated", False)
        if low_n and concentrated:
            position_flags[position] = "both"
        elif low_n:
            position_flags[position] = "low_n"
        elif concentrated:
            position_flags[position] = "concentrated"
        info = concentration_by_position.get(position, {})

        for method in METHODS:
            # None/NaN (ex. aquecimento da persistência) é a sua própria
            # categoria, nunca excluída em silêncio do denominador.
            decided_rooms = pos_df[f"{method}_room"].fillna(NO_DECISION_LABEL)
            n_decided = int((decided_rooms != NO_DECISION_LABEL).sum())
            counts = decided_rooms.value_counts()
            for decided_room, n in counts.items():
                n = int(n)
                rows.append({
                    "trial_position": position,
                    "method": method,
                    "decided_room": decided_room,
                    "n": n,
                    "total_n": total_n,
                    "pct_of_total": (n / total_n * 100.0) if total_n else None,
                    "n_decided": n_decided,
                    "pct_of_decided": (n / n_decided * 100.0) if (n_decided and decided_room != NO_DECISION_LABEL) else None,
                    "low_n": low_n,
                    "concentrated": concentrated,
                    "dominant_experiment_id": info.get("dominant_experiment"),
                    "dominant_experiment_share": info.get("max_share"),
                })

    if not rows:
        _warn("doorway-distribution: nada para reportar.")
        return

    os.makedirs(args.output_dir, exist_ok=True)
    csv_path = os.path.join(args.output_dir, f"distribuicao_fronteira_{args.label}.csv")
    out_df = pd.DataFrame(rows, columns=[
        "trial_position", "method", "decided_room", "n", "total_n", "pct_of_total",
        "n_decided", "pct_of_decided", "low_n", "concentrated",
        "dominant_experiment_id", "dominant_experiment_share",
    ])
    out_df.to_csv(csv_path, index=False)
    print(f"Distribuição nas posições de fronteira escrita: {csv_path}")

    # Figura construída a partir das MESMAS linhas do CSV, nunca recalculada
    # em separado - célula = repartição por sala, pct_of_total primeiro
    # (mostrar só pct_of_decided esconderia "sem decisão" da vista).
    header = ["Posição"] + [METHOD_LABELS_PT[m].replace("\n", " ") for m in METHODS]
    fig_rows = []
    flagged_rows = {}
    for row_idx, position in enumerate(positions):
        flag = position_flags.get(position)
        if flag:
            flagged_rows[row_idx] = flag
        pos_total = out_df.loc[out_df["trial_position"] == position, "total_n"].iloc[0]
        label_marker = ("*" if flag in ("low_n", "both") else "") + ("†" if flag in ("concentrated", "both") else "")
        row_label = f"{position} (n={pos_total})" + (f" {label_marker}" if label_marker else "")
        row = [row_label]
        for method in METHODS:
            method_rows = out_df[(out_df["trial_position"] == position) & (out_df["method"] == method)]
            method_rows = method_rows.sort_values("pct_of_total", ascending=False)
            cell = "\n".join(f"{r.decided_room}: {r.pct_of_total:.0f}%" for r in method_rows.itertuples())
            row.append(cell if cell else "sem dados")
        fig_rows.append(row)

    fig, ax = plt.subplots(figsize=(11, 2.2 + 0.9 * len(fig_rows)))
    ax.axis("off")
    table = ax.table(cellText=fig_rows, colLabels=header, loc="center", cellLoc="center")
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.auto_set_column_width(col=list(range(len(header))))
    table.scale(1, 2.4)

    flag_colors = {"low_n": LOW_N_COLOR, "concentrated": CONCENTRATED_COLOR, "both": BOTH_FLAGS_COLOR}
    for row_idx, flag in flagged_rows.items():
        for col in range(len(header)):
            table[(row_idx + 1, col)].set_facecolor(flag_colors[flag])

    ax.set_title("Distribuição da sala decidida nas posições de fronteira (% do total de deteções)")
    footnote_lines = [
        "Sem ground truth nestas posições - percentagens sobre o total de deteções, não exatidão.",
        "\"Sem decisão\": o método ainda não confirmou sala nesta deteção (ex: aquecimento da persistência) - "
        "o beacon estava ativo e a ser detetado; não é o mesmo que o estado \"desconhecida\" do dashboard "
        "(esse é por inatividade do beacon).",
    ]
    if any(f in ("low_n", "both") for f in flagged_rows.values()):
        footnote_lines.append(
            f"* menos de {args.min_observations} observações - convenção para sinalizar poucas "
            "observações, não um critério de validade estatística."
        )
    if any(f in ("concentrated", "both") for f in flagged_rows.values()):
        footnote_lines.append(
            f"† mais de {args.concentration_threshold * 100:.0f}% das observações vêm de uma única "
            "repetição - célula não genuinamente agregada; ver consola para a distribuição completa."
        )
    fig.text(0.5, 0.01, "\n".join(footnote_lines), ha="center", fontsize=9, color="#555555")

    _savefig(fig, os.path.join(args.output_dir, f"tabela_fronteira_{args.label}.png"))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    def add_common(p):
        p.add_argument("--mac", default=None, help="MAC a usar (obrigatório se o CSV tiver mais do que uma)")
        p.add_argument("--output-dir", default="report_figures")
        p.add_argument("--label", default="fig")

    p1 = sub.add_parser("global-table", help="Figura 1: tabela global de comparação")
    p1.add_argument("--descriptive-csv", required=True)
    add_common(p1)
    p1.set_defaults(func=cmd_global_table)

    p2 = sub.add_parser("accuracy-bar", help="Figura 2: barras de exatidão com IC")
    p2.add_argument("--descriptive-csv", required=True)
    add_common(p2)
    p2.set_defaults(func=cmd_accuracy_bar)

    p3 = sub.add_parser("false-movements-bar", help="Figura 3: barras de falsos movimentos/hora com IC")
    p3.add_argument("--descriptive-csv", required=True)
    add_common(p3)
    p3.set_defaults(func=cmd_false_movements_bar)

    p4 = sub.add_parser("latency-boxplot", help="Figura 4: boxplot da latência de confirmação")
    p4.add_argument("--latency-csv", nargs="+", required=True, help="um ou mais transition_latencies_<label>.csv")
    add_common(p4)
    p4.set_defaults(func=cmd_latency_boxplot)

    p5 = sub.add_parser("reliability-scatter", help="Figura 5: dispersão fiabilidade vs. latência")
    p5.add_argument("--descriptive-csv", required=True)
    add_common(p5)
    p5.set_defaults(func=cmd_reliability_scatter)

    p6 = sub.add_parser("confusion-matrix", help="Figura 6: matriz de confusão sala real x estimada")
    p6.add_argument("--confusion-csv", nargs="+", required=True)
    p6.add_argument("--pool", action="store_true", help="soma as repetições (verifica consistência de salas primeiro)")
    add_common(p6)
    p6.set_defaults(func=cmd_confusion_matrix)

    p7 = sub.add_parser("rssi-timeline", help="Figura 7: RSSI ao longo do tempo durante uma transição")
    p7.add_argument("--detail-csv", required=True, help="raw_with_decisions_<label>.csv")
    p7.add_argument("--latency-csv", required=True, help="transition_latencies_<label>.csv da MESMA repetição")
    p7.add_argument("--mac", required=True)
    p7.add_argument("--experiment-id", default=None)
    p7.add_argument("--transition-index", type=int, default=0)
    p7.add_argument("--start", default=None)
    p7.add_argument("--end", default=None)
    p7.add_argument("--window-sec", type=float, default=20.0)
    p7.add_argument("--output-dir", default="report_figures")
    p7.add_argument("--label", default="fig")
    p7.set_defaults(func=cmd_rssi_timeline)

    p8 = sub.add_parser("parameter-sweep", help="Figura 8: varredura de um parâmetro de análise")
    p8.add_argument("--sweep-csv", required=True, help="parameter_sweep_<parameter>_<label>.csv de sweep_parameter.py")
    p8.add_argument("--output-dir", default="report_figures")
    p8.add_argument("--label", default="fig")
    p8.set_defaults(func=cmd_parameter_sweep)

    p9 = sub.add_parser("scenario-table", help="Figura 9: exatidão por cenário e método")
    p9.add_argument("--detail-csv", nargs="+", required=True, help="um ou mais raw_with_decisions_<label>.csv")
    p9.add_argument("--min-observations", type=int, default=30,
                     help="abaixo disto, a linha do cenário fica marcada com * (convenção, não fronteira estatística; default: 30)")
    p9.add_argument("--concentration-threshold", type=float, default=0.5,
                     help="fração acima da qual uma única repetição a dominar o cenário marca a linha com † (default: 0.5)")
    add_common(p9)
    p9.set_defaults(func=cmd_scenario_table)

    p10 = sub.add_parser("position-table", help="Exatidão por posição (guião novo, protocolo de 75 ensaios)")
    p10.add_argument("--detail-csv", nargs="+", required=True, help="um ou mais raw_with_decisions_<label>.csv")
    p10.add_argument("--min-observations", type=int, default=30,
                      help="abaixo disto, a linha da posição fica marcada com * (default: 30)")
    p10.add_argument("--concentration-threshold", type=float, default=0.5,
                      help="fração acima da qual uma única repetição a dominar a posição marca a linha com † (default: 0.5)")
    add_common(p10)
    p10.set_defaults(func=cmd_position_table)

    p11 = sub.add_parser("trial-type-summary", help="Resumo estático/dinâmico por ensaio (guião novo, protocolo de 75 ensaios)")
    p11.add_argument("--summary-csv", nargs="+", required=True, help="um decision_summary_<experiment_id>.csv por ensaio")
    p11.add_argument("--detail-csv", nargs="+", required=True, help="um ou mais raw_with_decisions_<label>.csv com trial_type/trial_position")
    add_common(p11)
    p11.set_defaults(func=cmd_trial_type_summary)

    p12 = sub.add_parser("doorway-distribution",
                          help="Distribuição da sala decidida por método nas posições de fronteira (P1/P2, sem ground truth)")
    p12.add_argument("--detail-csv", nargs="+", required=True, help="um ou mais raw_with_decisions_<label>.csv")
    p12.add_argument("--positions", nargs="+", default=["P1", "P2"], help="posições de fronteira a analisar (default: P1 P2)")
    p12.add_argument("--min-observations", type=int, default=30,
                      help="abaixo disto, a posição fica marcada com * (default: 30)")
    p12.add_argument("--concentration-threshold", type=float, default=0.5,
                      help="fração acima da qual uma única repetição a dominar a posição marca a linha com † (default: 0.5)")
    add_common(p12)
    p12.set_defaults(func=cmd_doorway_distribution)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
