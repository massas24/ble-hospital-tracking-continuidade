"""
Simular um único beacon movendo-se entre duas salas para exercitar a
lógica de histerese em POST /api/bledata.

Requer que o backend (Flask + MongoDB) já esteja a ser executado em separado:

cd backend && python app.py

Uso:

python simulate_hysteresis.py [--base-url http://localhost:5000] [--delay 1.0]

Nota: /api/bledata nunca informa o chamador se a histerese aceitou ou
rejeitou uma determinada leitura - esta decisão apenas aparece como uma mensagem "Histerese
rejeitou..." impresso na própria consola do backend. Portanto, este script mantém um
espelho local da mesma regra (HYSTERESIS_MARGIN) apenas para imprimir um
resumo esperado de aceitação/rejeição. Observe a consola do backend enquanto este script é executado
e verifique se as linhas de rejeição correspondem aos passos "rejeitados" aqui impressos - esta
comparação é a validação real, o resumo deste script é apenas um guia.
"""

import argparse
import time

import requests

HYSTERESIS_MARGIN = 5  # Must match backend/app.py's HYSTERESIS_MARGIN

MAC = "aa:bb:cc:dd:ee:01"
ROOM_A = "Quarto-101"
ROOM_B = "Quarto-102"
ESP_A = "ESP-101"
ESP_B = "ESP-102"

AUTH_HEADERS = {"X-User": "simulate_hysteresis"}


def setup(base_url):
    # Best-effort: these can fail harmlessly on repeated runs (mac already
    # whitelisted, mapping already exists), so errors are ignored here.
    try:
        requests.post(f"{base_url}/api/whitelist", json={"mac": MAC}, headers=AUTH_HEADERS, timeout=5)
    except requests.exceptions.RequestException as e:
        print(f"Aviso: falha ao adicionar à whitelist ({e})")
    for esp_id, room in ((ESP_A, ROOM_A), (ESP_B, ROOM_B)):
        try:
            requests.post(f"{base_url}/api/esp-mapping", json={"esp_id": esp_id, "room": room},
                          headers=AUTH_HEADERS, timeout=5)
        except requests.exceptions.RequestException as e:
            print(f"Aviso: falha ao mapear {esp_id} -> {room} ({e})")


def send_reading(base_url, esp_id, rssi):
    payload = [{"mac": MAC, "esp_id": esp_id, "rssi": rssi}]
    resp = requests.post(f"{base_url}/api/bledata", json=payload, timeout=5)
    resp.raise_for_status()


def expected_outcome(state, room, rssi):
    """Rede espelhada a regra de histerese backend/app.py, utilizada apenas para construir o
    resumo impresso (a resposta da API não expõe aceitar/rejeitar)."""
    current = state.get("current")
    if current is None:
        state["current"] = {"room": room, "rssi": rssi}
        return "init"
    if current["room"] == room:
        state["current"] = {"room": room, "rssi": rssi}
        return "same_room"
    if rssi >= current["rssi"] + HYSTERESIS_MARGIN:
        state["current"] = {"room": room, "rssi": rssi}
        return "accepted"
    return "rejected"


def run_step(base_url, state, step_name, esp_id, room, rssi, delay):
    outcome = expected_outcome(state, room, rssi)
    print(f"[{step_name}] esp={esp_id} room={room} rssi={rssi} -> esperado: {outcome}")
    send_reading(base_url, esp_id, rssi)
    if delay:
        time.sleep(delay)
    return outcome


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://localhost:5000")
    parser.add_argument("--delay", type=float, default=1.0, help="segundos de espera entre leituras")
    args = parser.parse_args()

    print("A preparar whitelist e mapeamento de salas...")
    setup(args.base_url)

    state = {}
    outcomes = []

    print("\n--- Cenario 1: mudanca clara e sustentada (deve ser aceite) ---")
    outcomes.append(run_step(args.base_url, state, "1.1 baseline em Quarto-101", ESP_A, ROOM_A, -60, args.delay))
    outcomes.append(run_step(args.base_url, state, "1.2 confirma Quarto-101", ESP_A, ROOM_A, -58, args.delay))
    outcomes.append(run_step(args.base_url, state, "1.3 mudanca forte para Quarto-102", ESP_B, ROOM_B, -40, args.delay))

    print("\n--- Cenario 2: oscilacao perto da fronteira (deve ser rejeitada repetidamente) ---")
    outcomes.append(run_step(args.base_url, state, "2.1 tentativa fraca para Quarto-101", ESP_A, ROOM_A, -41, args.delay))
    outcomes.append(run_step(args.base_url, state, "2.2 tentativa fraca para Quarto-101", ESP_A, ROOM_A, -39, args.delay))
    outcomes.append(run_step(args.base_url, state, "2.3 tentativa fraca para Quarto-101", ESP_A, ROOM_A, -36, args.delay))

    print("\n--- Cenario 3: leitura forte apos a oscilacao (deve ser finalmente aceite) ---")
    outcomes.append(run_step(args.base_url, state, "3.1 leitura forte para Quarto-101", ESP_A, ROOM_A, -20, args.delay))

    total = len(outcomes)
    accepted = outcomes.count("accepted")
    rejected = outcomes.count("rejected")
    ignored = total - accepted - rejected  # init / same_room, sem decisao de mudanca

    print("\n=== Resumo ===")
    print(f"Leituras enviadas: {total}")
    print(f"Mudancas aceites: {accepted}")
    print(f"Mudancas rejeitadas pela histerese: {rejected}")
    print(f"Sem decisao de mudanca (1a leitura / mesma sala): {ignored}")


if __name__ == "__main__":
    main()
