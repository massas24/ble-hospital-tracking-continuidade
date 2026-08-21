"""
Orquestra analyze_room_decisions.py por subprocesso, um por experiment_id,
para processar em lote o protocolo de 75 ensaios do Prof. Carreto (11
posições estáticas x 5 repetições + 2 percursos x 10 repetições) sem correr
cada um à mão. Replica o padrão de subprocesso/caminhos previsíveis já
provado em sweep_parameter.py - aqui os 3 parâmetros de decisão ficam
FIXOS (mesmos valores para todos os ensaios), o que varia é o experiment_id,
não um parâmetro de decisão (propósito diferente de sweep_parameter.py,
mesmo mecanismo).

Convenção de nomenclatura esperada (ver analyze_room_decisions.
parse_trial_label): EST-<posição>-R<repetição> / DIN-<rota>-R<repetição>.

Uso:
  python batch_analyze_experiments.py --label campanha1 \\
      --discover-prefix EST- DIN- --mac aa:bb:cc:dd:ee:01

  python batch_analyze_experiments.py --label campanha1 \\
      --experiment-ids EST-A1-R1 EST-A1-R2 DIN-AB-R1 --mac aa:bb:cc:dd:ee:01
"""
import argparse
import json
import os
import subprocess
import sys

import pandas as pd
from pymongo import MongoClient

from analyze_room_decisions import parse_trial_label

# Soleiras de porta, sem sala verdadeira definível - a única situação onde
# a ausência de ground truth é esperada por desenho, não um esquecimento.
NO_GROUND_TRUTH_EXPECTED_POSITIONS = {"P1", "P2"}


def discover_experiment_ids(collection, prefixes):
    all_ids = collection.distinct("experiment_id")
    return sorted(eid for eid in all_ids if eid and any(eid.startswith(p) for p in prefixes))


def run_one(experiment_id, args, output_dir):
    cmd = [
        sys.executable, "analyze_room_decisions.py",
        "--experiment-id", experiment_id,
        "--median-window", str(args.median_window),
        "--hysteresis-margin", str(args.hysteresis_margin),
        "--persistence-streak", str(args.persistence_streak),
        "--no-plots",
        "--output-dir", output_dir,
        "--mongo-uri", args.mongo_uri,
        "--db-name", args.db_name,
    ]
    if args.mac:
        cmd += ["--mac"] + args.mac
    if args.min_rssi is not None:
        cmd += ["--min-rssi", str(args.min_rssi)]

    print(f"A correr: experiment_id={experiment_id!r} -> {output_dir}")
    return subprocess.run(cmd, capture_output=True, text=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--experiment-ids", nargs="+", default=[], help="experiment_id explícitos a processar")
    parser.add_argument("--discover-prefix", nargs="+", default=[],
                         help="descobre experiment_id em raw_detections cujo nome comece por qualquer um destes "
                              "prefixos (ex: EST- DIN-), além dos indicados em --experiment-ids")
    parser.add_argument("--mac", nargs="+", default=None)
    parser.add_argument("--median-window", type=int, default=5)
    parser.add_argument("--hysteresis-margin", type=float, default=5)
    parser.add_argument("--persistence-streak", type=int, default=3)
    parser.add_argument("--min-rssi", type=float, default=None)
    parser.add_argument("--mongo-uri", default="mongodb://localhost:27017")
    parser.add_argument("--db-name", default="temp1_db")
    parser.add_argument("--output-dir", default="batch_output")
    parser.add_argument("--label", required=True,
                         help="identifica esta campanha - usado no nome do CSV combinado "
                              "(raw_with_decisions_<label>.csv), para uma campanha nova não sobrescrever uma anterior")
    args = parser.parse_args()

    if not args.experiment_ids and not args.discover_prefix:
        raise SystemExit("Indica --experiment-ids e/ou --discover-prefix.")

    experiment_ids = list(dict.fromkeys(args.experiment_ids))  # preserva ordem, remove duplicados
    if args.discover_prefix:
        client = MongoClient(args.mongo_uri)
        raw_detections = client[args.db_name]["raw_detections"]
        discovered = discover_experiment_ids(raw_detections, args.discover_prefix)
        print(f"Descobertos {len(discovered)} experiment_id com prefixo {args.discover_prefix}: {discovered}")
        for eid in discovered:
            if eid not in experiment_ids:
                experiment_ids.append(eid)

    if not experiment_ids:
        raise SystemExit("Nenhum experiment_id para processar.")

    os.makedirs(args.output_dir, exist_ok=True)
    summary_paths = []
    detail_paths = []
    failures = []

    for experiment_id in experiment_ids:
        trial_type, trial_position = parse_trial_label(experiment_id)
        looks_intended = experiment_id.startswith("EST-") or experiment_id.startswith("DIN-")
        if looks_intended and trial_type is None:
            print(
                f"AVISO: {experiment_id!r} parece seguir a convenção EST-/DIN- mas não bate com o padrão completo "
                "EST-<posição>-R<n>/DIN-<rota>-R<n> - a processar à mesma, mas trial_type/trial_position vão "
                "ficar em branco na análise."
            )

        exp_output_dir = os.path.join(args.output_dir, experiment_id)
        result = run_one(experiment_id, args, exp_output_dir)
        if result.returncode != 0:
            failures.append((experiment_id, result.stderr.strip()[-500:]))
            continue

        summary_csv = os.path.join(exp_output_dir, f"decision_summary_{experiment_id}.csv")
        detail_csv = os.path.join(exp_output_dir, f"raw_with_decisions_{experiment_id}.csv")
        metadata_json = os.path.join(exp_output_dir, f"run_metadata_{experiment_id}.json")
        if not os.path.exists(summary_csv):
            print(f"AVISO: {experiment_id!r} correu sem erro mas não produziu {summary_csv} (sem deteções?) - a saltar.")
            continue
        summary_paths.append(summary_csv)
        detail_paths.append(detail_csv)

        if trial_type == "static" and trial_position not in NO_GROUND_TRUTH_EXPECTED_POSITIONS:
            with open(metadata_json, encoding="utf-8") as f:
                run_metadata = json.load(f)
            for mac, gt_summary in run_metadata.get("ground_truth_summary", {}).items():
                if gt_summary.get("events_loaded", 0) == 0:
                    print(
                        f"AVISO: {experiment_id!r} (posição {trial_position}, mac {mac}) não tem NENHUM evento "
                        "de ground truth - provável esquecimento de marcação (P1/P2 são as únicas posições "
                        "onde isto é esperado)."
                    )

    if failures:
        print(f"\n{len(failures)} experiment_id falharam:")
        for experiment_id, stderr in failures:
            print(f"  {experiment_id!r}: {stderr}")

    if not detail_paths:
        print("\nNenhum experiment_id produziu dados - nada para combinar.")
        return

    combined_detail = pd.concat([pd.read_csv(p) for p in detail_paths], ignore_index=True)
    combined_csv = os.path.join(args.output_dir, f"raw_with_decisions_{args.label}.csv")
    combined_detail.to_csv(combined_csv, index=False)
    print(f"\nCSV combinado ({len(detail_paths)} ensaios): {combined_csv}")

    print("\nPronto para estatística por repetição:")
    print(f"  python statistical_analysis.py per-repetition --summary-csv {' '.join(summary_paths)} --label {args.label}")
    print("\nPronto para as tabelas por posição / estático-dinâmico:")
    print(f"  python generate_report_figures.py position-table --detail-csv {combined_csv} --label {args.label}")
    print(
        f"  python generate_report_figures.py trial-type-summary --summary-csv {' '.join(summary_paths)} "
        f"--detail-csv {combined_csv} --label {args.label}"
    )
    if failures:
        print(f"\n({len(failures)} experiment_id falharam - ver acima)")


if __name__ == "__main__":
    main()
