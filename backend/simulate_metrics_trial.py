"""
Generates a synthetic BLE trial with a KNOWN ground truth, entirely by
script - no physical beacon movement, no manual tapping. Designed to
exercise backend/metrics.py's computations against a known-by-construction
result: at least two clean movements the decision methods should detect
(for latency statistics), one real movement the hysteresis-based methods
should fail to confirm (a "missed movement"), and one spurious blip the
less-strict methods should register as a movement but persistence should
suppress (a "false movement").

Timing: never sends an explicit "time" to /api/ground-truth. Each
ground-truth tap is POSTed (and its response awaited) BEFORE the paired
/api/bledata reading, so both land on the same server clock with zero
client/server timezone risk - /api/bledata has no time-override mechanism
at all, so this is the only way to keep the two in sync.

Requires the backend (Flask + MongoDB) to already be running separately:
    cd backend && python app.py

Usage:
    python simulate_metrics_trial.py [--base-url http://localhost:5000] [--delay 1.0]

Run against a DEDICATED/isolated backend instance, not one also serving
real ESP32/dashboard traffic - current_experiment_id is a single
process-global in app.py, and this script repeatedly overwrites it.

Approximate RSSI values below are tuned against HYSTERESIS_MARGIN=5,
median_window=5, persistence_streak=3 (analyze_room_decisions.py's own
defaults) - verify empirically after running, don't assume exact numbers
matter more than the qualitative shape of each step.
"""

import argparse
import time

import requests

from simulate_hysteresis import MAC, ROOM_A, ROOM_B, ESP_A, ESP_B, AUTH_HEADERS, setup, send_reading


def post_experiment(base_url, experiment_id, **acquisition_params):
    body = {"experiment_id": experiment_id, **acquisition_params}
    resp = requests.post(f"{base_url}/api/experiment", json=body, headers=AUTH_HEADERS, timeout=5)
    resp.raise_for_status()


def post_ground_truth(base_url, room, note=None):
    body = {"mac": MAC, "room": room}
    if note:
        body["note"] = note
    resp = requests.post(f"{base_url}/api/ground-truth", json=body, headers=AUTH_HEADERS, timeout=5)
    resp.raise_for_status()
    return resp.json()


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--base-url", default="http://localhost:5000")
    parser.add_argument("--delay", type=float, default=1.0, help="segundos de espera entre leituras")
    parser.add_argument("--experiment-id", default=None, help="default: metrics_trial_<epoch>")
    args = parser.parse_args()

    experiment_id = args.experiment_id or f"metrics_trial_{int(time.time())}"

    def tap(room, note=None):
        post_ground_truth(args.base_url, room, note=note)
        # The server clock has only 1-second resolution (same as
        # raw_detections' own "time"), same as everywhere else in this
        # project (no NTP). A short --delay between readings can otherwise
        # let a tap and its very next reading land in the same server
        # second, collapsing that ground-truth interval to zero width and
        # making it unmatchable - always force a full extra second here,
        # regardless of --delay, so every tap starts a genuinely distinct
        # second from whatever reading follows it.
        time.sleep(1.1)

    def read(esp_id, rssi):
        send_reading(args.base_url, esp_id, rssi)
        if args.delay:
            time.sleep(args.delay)

    print(f"A preparar ensaio '{experiment_id}'...")
    setup(args.base_url)
    post_experiment(
        args.base_url, experiment_id,
        scan_duration_sec=5, upload_interval_ms=2000,
        firmware_rssi_cutoff=-90,
        notes="Ensaio sintetico gerado por script, para validar as metricas de ground truth",
    )

    print("\n--- Passo 1: assentar em Quarto-101 ---")
    tap(ROOM_A, note="inicio do ensaio")
    read(ESP_A, -60)
    read(ESP_A, -58)
    read(ESP_A, -61)
    read(ESP_A, -60)
    read(ESP_A, -59)

    print("--- Passo 2: movimento FALSO (pico isolado, sem toque novo - gt continua Quarto-101) ---")
    # Forte o suficiente para vencer a mediana (bate a mediana ~-59 de
    # Quarto-101) e por isso aparece em baseline/median - mas FRACO DE
    # PROPOSITO para nao passar a margem de histerese (precisa de
    # >= -59+5=-54; -56 fica abaixo disso), por isso median_hysteresis
    # rejeita-o de imediato (nunca chega a mudar), e por consequencia a
    # persistencia (alimentada pela decisao do median_hysteresis, nao pela
    # leitura bruta) tambem nunca vê Quarto-102 aqui - fica corretamente
    # sem nenhum movimento falso.
    read(ESP_B, -56)

    print("--- Passo 3: reassentar em Quarto-101 (leituras extra de sobra para a janela da mediana esquecer por completo o pico) ---")
    read(ESP_A, -59)
    read(ESP_A, -60)
    read(ESP_A, -58)
    read(ESP_A, -59)
    read(ESP_A, -60)
    read(ESP_A, -58)

    print("--- Passo 4: movimento real NAO DETETADO (leituras fracas, gt muda para Quarto-102) ---")
    tap(ROOM_B, note="movimento real, mas fraco - deve ficar por detetar na histerese")
    read(ESP_B, -56)
    read(ESP_B, -55)

    print("--- Passo 5: regresso a Quarto-101 (fecha a janela anterior, 1a deteccao limpa) ---")
    tap(ROOM_A)
    read(ESP_A, -34)
    read(ESP_A, -33)
    read(ESP_A, -35)
    read(ESP_A, -34)

    print("--- Passo 6: manter em Quarto-101 ---")
    read(ESP_A, -59)
    read(ESP_A, -60)
    read(ESP_A, -58)

    print("--- Passo 7: movimento LIMPO (2a deteccao, inequivoca para os 4 metodos) ---")
    tap(ROOM_B)
    read(ESP_B, -34)
    read(ESP_B, -33)
    read(ESP_B, -35)
    read(ESP_B, -34)
    read(ESP_B, -33)

    print("--- Passo 8: manter + 3o ciclo (mais volume/duracao) ---")
    read(ESP_B, -59)
    read(ESP_B, -60)
    read(ESP_B, -58)
    tap(ROOM_A)
    read(ESP_A, -34)
    read(ESP_A, -33)
    read(ESP_A, -35)
    read(ESP_A, -34)
    read(ESP_A, -33)

    print(f"\n=== Ensaio '{experiment_id}' concluido ===")
    print(f"Corre a seguir: python analyze_room_decisions.py --experiment-id {experiment_id}")


if __name__ == "__main__":
    main()
