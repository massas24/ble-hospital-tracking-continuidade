"""
Varredura de um parâmetro de decisão (--median-window, --hysteresis-margin
ou --persistence-streak) através de várias repetições, para a figura 8 do
guião (secção "5.6 Influência dos parâmetros" - janela temporal, histerese
E persistência, não só a janela).

Orquestração pura: corre analyze_room_decisions.py por subprocesso, uma vez
por (repetição, valor do parâmetro) - nunca importa/refatora o main() dele,
para não desestabilizar um script já a funcionar só para isto. Agrega entre
repetições reaproveitando statistical_analysis.descriptive_stats (importado,
não reimplementado) e statistical_analysis.check_consistent_analysis_parameters
(garante que só o parâmetro escolhido difere entre as repetições comparadas
em cada ponto da varredura).

Uso:
  python sweep_parameter.py --experiment-id ensaio3 ensaio4 ensaio5 \\
      --parameter median-window --values 1 3 5 8 10 \\
      --mac aa:bb:cc:dd:ee:01
"""
import argparse
import os
import subprocess
import sys

import pandas as pd

from statistical_analysis import (
    METHODS, DESCRIPTIVE_METRICS, descriptive_stats, check_consistent_analysis_parameters,
)

PARAMETER_FLAGS = {
    "median-window": "--median-window",
    "hysteresis-margin": "--hysteresis-margin",
    "persistence-streak": "--persistence-streak",
}
# analyze_room_decisions.py declares --median-window/--persistence-streak as
# int and --hysteresis-margin as float - --values is always parsed as float
# here (so e.g. "5" and "5.5" can both be typed), so the swept value must be
# cast to the RIGHT type before being formatted into the subprocess command,
# or int-typed flags reject "5.0" outright.
PARAMETER_TYPES = {
    "median-window": int,
    "hysteresis-margin": float,
    "persistence-streak": int,
}
# Nomes dos argumentos fixos correspondentes, para reencaminhar os OUTROS
# 2 parâmetros de decisão inalterados em cada chamada.
PARAMETER_ARG_NAMES = {
    "median-window": "median_window",
    "hysteresis-margin": "hysteresis_margin",
    "persistence-streak": "persistence_streak",
}


def run_one(experiment_id, parameter, value, args, output_dir):
    typed_value = PARAMETER_TYPES[parameter](value)
    cmd = [
        sys.executable, "analyze_room_decisions.py",
        "--experiment-id", experiment_id,
        PARAMETER_FLAGS[parameter], str(typed_value),
        "--no-plots",
        "--output-dir", output_dir,
        "--mongo-uri", args.mongo_uri,
        "--db-name", args.db_name,
    ]
    if args.mac:
        cmd += ["--mac"] + args.mac
    # Reencaminha os OUTROS 2 parâmetros de decisão, fixos - só o
    # escolhido em --parameter varia.
    for name, flag in PARAMETER_FLAGS.items():
        if name == parameter:
            continue
        cmd += [flag, str(getattr(args, PARAMETER_ARG_NAMES[name]))]
    if args.min_rssi is not None:
        cmd += ["--min-rssi", str(args.min_rssi)]

    print(f"A correr: experiment_id={experiment_id!r} {parameter}={value} -> {output_dir}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--experiment-id", nargs="+", required=True, help="conjunto de repetições")
    parser.add_argument("--parameter", required=True, choices=sorted(PARAMETER_FLAGS.keys()))
    parser.add_argument("--values", nargs="+", required=True, type=float)
    parser.add_argument("--mac", nargs="+", default=None)
    parser.add_argument("--median-window", type=int, default=5, help="fixo, exceto se --parameter for este")
    parser.add_argument("--hysteresis-margin", type=float, default=5, help="fixo, exceto se --parameter for este")
    parser.add_argument("--persistence-streak", type=int, default=3, help="fixo, exceto se --parameter for este")
    parser.add_argument("--min-rssi", type=float, default=None)
    parser.add_argument("--mongo-uri", default="mongodb://localhost:27017")
    parser.add_argument("--db-name", default="temp1_db")
    parser.add_argument("--output-dir", default="sweep_output")
    parser.add_argument("--label", default=None, help="default: o próprio --parameter")
    args = parser.parse_args()

    label = args.label or args.parameter
    failures = []
    pair_summary_paths = {}  # {value: [decision_summary_<eid>.csv, ...]}

    for value in args.values:
        value_str = str(value).rstrip("0").rstrip(".") if "." in str(value) else str(value)
        pair_summary_paths[value] = []
        for experiment_id in args.experiment_id:
            pair_output_dir = os.path.join(args.output_dir, f"{args.parameter}_{value_str}", experiment_id)
            result = run_one(experiment_id, args.parameter, value, args, pair_output_dir)
            if result.returncode != 0:
                failures.append((experiment_id, value, result.stderr.strip()[-500:]))
                continue
            pair_summary_paths[value].append(os.path.join(pair_output_dir, f"decision_summary_{experiment_id}.csv"))

    if failures:
        print(f"\n{len(failures)} combinação(ões) falharam:")
        for experiment_id, value, stderr in failures:
            print(f"  experiment_id={experiment_id!r} {args.parameter}={value}: {stderr}")

    # Agregação por valor do parâmetro, reaproveitando descriptive_stats -
    # nunca reimplementada aqui.
    rows = []
    for value, summary_paths in pair_summary_paths.items():
        if not summary_paths:
            print(f"AVISO: nenhuma repetição válida para {args.parameter}={value} - sem linha na varredura.")
            continue
        warnings = check_consistent_analysis_parameters(
            summary_paths, ignore_keys=[PARAMETER_ARG_NAMES[args.parameter]]
        )
        for w in warnings:
            print(f"AVISO [{args.parameter}={value}]: {w}")

        dfs = [pd.read_csv(p) for p in summary_paths]
        combined = pd.concat(dfs, ignore_index=True)
        macs = sorted(combined["mac"].unique())
        for mac in macs:
            mac_df = combined[combined["mac"] == mac]
            for method in METHODS:
                for metric in DESCRIPTIVE_METRICS:
                    values = mac_df.loc[mac_df["method"] == method, metric].dropna().tolist()
                    stats = descriptive_stats(values)
                    rows.append({
                        "parameter": args.parameter, "parameter_value": value,
                        "mac": mac, "method": method, "metric": metric,
                        "n_repetitions": stats["n"], "mean": stats["mean"],
                        "ci_lower": stats["ci_lower"], "ci_upper": stats["ci_upper"],
                    })

    os.makedirs(args.output_dir, exist_ok=True)
    sweep_csv = os.path.join(args.output_dir, f"parameter_sweep_{args.parameter}_{label}.csv")
    pd.DataFrame(rows, columns=[
        "parameter", "parameter_value", "mac", "method", "metric", "n_repetitions", "mean", "ci_lower", "ci_upper",
    ]).to_csv(sweep_csv, index=False)
    print(f"\nVarredura escrita: {sweep_csv}")
    if failures:
        print(f"({len(failures)} combinação(ões) falharam - ver acima)")


if __name__ == "__main__":
    main()
