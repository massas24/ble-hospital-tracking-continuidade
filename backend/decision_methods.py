"""
Algoritmos de decisão de ambiente puros e reproduzíveis para comparar quatro configurações progressivamente mais
restritas sobre a mesma sequência de detecções BLE brutas para um
único beacon (MAC):

1. decide_baseline - a leitura mais recente vence, sem filtragem
2. decide_median - RSSI mediano em uma janela deslizante
3. decide_median_hysteresis - margem adicional necessária para alterar o ambiente
4. decide_median_hysteresis_persistence - N leituras consecutivas adicionais para confirmar

Cada configuração se baseia na anterior, em vez de duplicar a lógica:
decide_hysteresis() e decide_persistence() são primitivas genéricas que
operam em qualquer sequência de candidatos com formato {"room", "rssi"} - elas não
se importam se esses candidatos são detecções brutas ou já filtradas pela mediana.
decide_median_hysteresis() alimenta o resultado por ponto de decide_median() com o RSSI mediano/ambiente vencedor. decide_hysteresis(); decide_median_hysteresis_persistence()
alimenta a sequência de salas desse resultado em decide_persistence(). Ambas as primitivas
permanecem diretamente acessíveis em detecções brutas também, se necessário de forma independente.

Cada função recebe uma lista cronológica ordenada de dicionários de detecção
(cada um com pelo menos as chaves "room" e "rssi") para UM MAC e retorna uma
lista do mesmo comprimento com a decisão tomada em cada ponto. Sem E/S, sem
MongoDB, sem estado global além da constante padrão de nível de módulo abaixo -
estes são testáveis ​​unitariamente com listas construídas manualmente.

"changed" é definido uniformemente em todos os métodos como "o 'decided_room' desta linha
difere do 'decided_room' da linha anterior" (None conta como um
valor distinto, portanto, a primeira decisão de um método também é "changed").

Os chamadores que desejam uma métrica de "número de transições entre duas salas estabelecidas"
devem excluir o primeiro True (consulte analyze_room_decisions.py).
""
"""

import statistics
from datetime import datetime, timedelta

# Kept in sync with backend/app.py's HYSTERESIS_MARGIN constant
HYSTERESIS_MARGIN = 5

# Duplicado (não importado) de metrics.TIME_FORMAT/_parse: decision_methods.py
# é importado por app.py, e metrics.py é deliberadamente nunca importado por
# app.py (ver CLAUDE.md) - importar aqui furaria essa fronteira só para
# poupar 2 linhas.
TIME_FORMAT = "%Y-%m-%d %H:%M:%S"


def _parse_time(time_str):
    return datetime.strptime(time_str, TIME_FORMAT)


def _is_numeric(value):
    return isinstance(value, (int, float))


def filter_min_rssi(detections, min_rssi):
    """Descarta as deteções cujo RSSI numérico está abaixo de min_rssi (um limite inferior para o sinal fraco),
    antes mesmo de chegarem a uma função de decisão - espelha, na
    camada de decisão, o limite de RSSI que o firmware original da Bella aplicava no próprio
    ESP32 (ver nota metodológica no README). raw_detections no MongoDB
    permanece completo independentemente; apenas esta lista na memória é filtrada.

    As deteções com RSSI em falta/não numérico ("" ou em falta) são mantidas tal como estão -
    não são "fracas", não transportam qualquer sinal e já são
    tratadas pelas verificações _is_numeric dentro das funções de decisão.

    min_rssi=None desativa a filtragem completamente (retorna as deteções inalteradas),
    que é o padrão - este é um novo recurso sem comportamento anterior a
    preservar, pelo que deve ser explicitamente ativado.

    """
    if min_rssi is None:
        return detections
    return [d for d in detections if not _is_numeric(d.get("rssi")) or d["rssi"] >= min_rssi]


def decide_baseline(detections):
    """Método de referência: prevalece sempre a leitura mais recente, sem qualquer filtragem.

    Retorna um dicionário por deteção de entrada:

    {"decided_room": str|None, "changed": bool}

    """
    results = []
    previous_room = None

    for detection in detections:
        decided_room = detection.get("room")
        results.append({
            "decided_room": decided_room,
            "changed": decided_room != previous_room,
        })
        previous_room = decided_room

    return results


def decide_hysteresis(detections, margin=HYSTERESIS_MARGIN):
    """Réplica exata do bloco de histerese bledata() do app.py, reproduzido offline.

    Retorna um dicionário por deteção de entrada:

    {"decided_room": str|None, "decided_rssi": value|None,

    "changed": bool, "rejected": bool}

    """
    results = []
    state = None  # {"room": ..., "rssi": ...}
    previous_room = None

    for detection in detections:
        room = detection.get("room")
        rssi = detection.get("rssi")
        rejected = False

        if state is None or state["room"] == room:
            # First sighting, or same room as before: accept unconditionally
            # and refresh the baseline (matches the live code, including not
            # requiring rssi to be numeric on this branch)
            state = {"room": room, "rssi": rssi}
        else:
            stored_rssi = state.get("rssi")
            strong_enough = (
                _is_numeric(rssi)
                and _is_numeric(stored_rssi)
                and rssi >= stored_rssi + margin
            )
            if strong_enough:
                state = {"room": room, "rssi": rssi}
            else:
                rejected = True  # state stays unchanged

        decided_room = state["room"]
        results.append({
            "decided_room": decided_room,
            "decided_rssi": state.get("rssi"),
            "changed": decided_room != previous_room,
            "rejected": rejected,
        })
        previous_room = decided_room

    return results


def decide_median(detections, window=5):
    """Decisão de sala por RSSI mediano com janela deslizante.

    No ponto i, considera as últimas detecções brutas da `janela` até e
    incluindo i (menos perto do início da sequência), calcula o
    RSSI mediano por sala entre as entradas de RSSI numérico nessa janela e
    escolhe a sala com a mediana mais elevada.

    Desempate, aplicado apenas quando 2 ou mais salas partilham a mesma mediana máxima:

    1. mantém a sala previamente decidida, se estiver entre as empatadas
    2. caso contrário, a sala empatou com o maior número de amostras numéricas na janela
    3. caso contrário, a sala empatada cuja leitura qualificada mais recente seja posterior
    4. caso contrário, ordem alfabética (recurso alternativo determinístico, não deve ocorrer)

    Retorna um dicionário por deteção de entrada:
    {"decided_room": str|None, "decided_median_rssi": float|None,
    "changed": bool, "num_valid_in_window": int}
    "decided_median_rssi" é o rssi mediano da sala vencedora na janela atual, ou o valor anterior mantido quando a janela não tem quaisquer dados numéricos (necessário posteriormente por decide_median_hysteresis()).
    """
    results = []
    previous_room = None
    previous_rssi = None

    for i in range(len(detections)):
        window_slice = detections[max(0, i - window + 1): i + 1]

        by_room = {}
        for pos, d in enumerate(window_slice):
            rssi = d.get("rssi")
            if not _is_numeric(rssi):
                continue
            by_room.setdefault(d.get("room"), []).append((pos, rssi))

        num_valid = sum(len(v) for v in by_room.values())

        if not by_room:
            # No numeric rssi anywhere in the window: hold the previous
            # decision (may still be None if none has ever been made)
            decided_room = previous_room
            decided_median_rssi = previous_rssi
        else:
            medians = {
                room: statistics.median(rssi for _, rssi in vals)
                for room, vals in by_room.items()
            }
            best = max(medians.values())
            tied = [room for room, m in medians.items() if m == best]

            if len(tied) > 1 and previous_room in tied:
                decided_room = previous_room
            elif len(tied) == 1:
                decided_room = tied[0]
            else:
                counts = {room: len(by_room[room]) for room in tied}
                max_count = max(counts.values())
                tied = [room for room in tied if counts[room] == max_count]
                if len(tied) == 1:
                    decided_room = tied[0]
                else:
                    last_pos = {room: max(pos for pos, _ in by_room[room]) for room in tied}
                    max_last = max(last_pos.values())
                    tied = [room for room in tied if last_pos[room] == max_last]
                    decided_room = sorted(tied)[0]

            decided_median_rssi = medians[decided_room]

        results.append({
            "decided_room": decided_room,
            "decided_median_rssi": decided_median_rssi,
            "changed": decided_room != previous_room,
            "num_valid_in_window": num_valid,
        })
        previous_room = decided_room
        previous_rssi = decided_median_rssi

    return results


def decide_persistence(detections, streak=3):
    """Persistência baseada em sequências: aceita um quarto (ou uma mudança de quarto) apenas após
    `sequência` leituras brutas consecutivas concordarem com ele. As linhas anteriores à primeira
    decisão são definidos com `decided_room=None` (aquecimento explícito).

    Retorna um dicionário por deteção de entrada:

    {"decided_room": str|None, "changed": bool}

    """
    results = []
    current_decision = None
    candidate_room = None
    candidate_streak = 0
    previous_room = None

    for detection in detections:
        room = detection.get("room")

        if current_decision is None or room != current_decision:
            # Either still warming up, or this reading challenges the
            # established decision - both accumulate towards a candidate
            if room == candidate_room:
                candidate_streak += 1
            else:
                candidate_room = room
                candidate_streak = 1

            if candidate_streak >= streak:
                current_decision = candidate_room
                candidate_room = None
                candidate_streak = 0
        else:
            # Agrees with the established decision: reset any pending challenger
            candidate_room = None
            candidate_streak = 0

        results.append({
            "decided_room": current_decision,
            "changed": current_decision != previous_room,
        })
        previous_room = current_decision

    return results


def decide_median_hysteresis(detections, window=5, margin=HYSTERESIS_MARGIN):
    """Filtragem mediana + histerese: executa primeiro decide_median() e depois alimenta
    a sua vitória por ponto (sala, rssi mediano) em decide_hysteresis() como se
    fossem as "detecções" - decide_hysteresis() não se importa se a
    sala/rssi que recebe são brutos ou já filtrados pela mediana.

    Retorna um dicionário por deteção de entrada (mesmo formato que decide_hysteresis()):

    {"sala_decidida": str|None, "rssi_decidida": value|None,

    "alterado": bool, "rejeitado": bool}

    """
    median_results = decide_median(detections, window=window)
    candidates = [
        {"room": r["decided_room"], "rssi": r["decided_median_rssi"]}
        for r in median_results
    ]
    return decide_hysteresis(candidates, margin=margin)


def decide_median_hysteresis_persistence(detections, window_sec=8.0, margin=HYSTERESIS_MARGIN, streak=3):
    """Filtragem mediana (janela temporal) + histerese corrigida + persistência: executa
    decide_median_hysteresis_windowed() primeiro e depois alimenta a sua sequência de salas em
    decide_persistence() (que analisa sempre apenas "room", nunca "rssi").
    Só usada offline - decide_persistence() em si fica intocado.

    Retorna um dicionário por deteção de entrada (mesmo formato que decide_persistence()):

    {"decided_room": str|None, "changed": bool}

    """
    mh_results = decide_median_hysteresis_windowed(detections, window_sec=window_sec, margin=margin)
    candidates = [{"room": r["decided_room"]} for r in mh_results]
    return decide_persistence(candidates, streak=streak)


def decide_median_windowed(detections, window_sec=8.0):
    """Como decide_median(), mas com janela TEMPORAL real em vez de contagem
    fixa de deteções: no ponto i, considera todas as deteções j<=i cujo
    "time" caia em [time[i] - window_sec, time[i]]. Só usada offline -
    decide_median() em si fica intocado (usado ao vivo por app.py através de
    decide_median_hysteresis()).

    Cada deteção de entrada precisa agora também da chave "time" (string
    TIME_FORMAT). O parsing é feito uma única vez à entrada, não repetido
    por janela.

    Mesmo desempate de decide_median() (sala anterior, depois mais amostras,
    depois leitura mais recente, depois ordem alfabética).

    Retorna um dicionário por deteção de entrada:
    {"decided_room": str|None, "decided_median_rssi": float|None,
    "changed": bool, "num_valid_in_window": int, "medians_by_room": dict}
    "medians_by_room" é o dict COMPLETO de medianas por sala nesta janela
    (não só a da sala vencedora) - necessário para decide_median_hysteresis_windowed()
    comparar contra a sala atualmente confirmada, não só a candidata.
    """
    results = []
    previous_room = None
    previous_rssi = None

    times = [_parse_time(d["time"]) for d in detections]

    left = 0
    for i in range(len(detections)):
        while times[i] - times[left] > timedelta(seconds=window_sec):
            left += 1
        window_slice = detections[left: i + 1]

        by_room = {}
        for pos, d in enumerate(window_slice):
            rssi = d.get("rssi")
            if not _is_numeric(rssi):
                continue
            by_room.setdefault(d.get("room"), []).append((pos, rssi))

        num_valid = sum(len(v) for v in by_room.values())

        if not by_room:
            decided_room = previous_room
            decided_median_rssi = previous_rssi
            medians_by_room = {}
        else:
            medians_by_room = {
                room: statistics.median(rssi for _, rssi in vals)
                for room, vals in by_room.items()
            }
            best = max(medians_by_room.values())
            tied = [room for room, m in medians_by_room.items() if m == best]

            if len(tied) > 1 and previous_room in tied:
                decided_room = previous_room
            elif len(tied) == 1:
                decided_room = tied[0]
            else:
                counts = {room: len(by_room[room]) for room in tied}
                max_count = max(counts.values())
                tied = [room for room in tied if counts[room] == max_count]
                if len(tied) == 1:
                    decided_room = tied[0]
                else:
                    last_pos = {room: max(pos for pos, _ in by_room[room]) for room in tied}
                    max_last = max(last_pos.values())
                    tied = [room for room in tied if last_pos[room] == max_last]
                    decided_room = sorted(tied)[0]

            decided_median_rssi = medians_by_room[decided_room]

        results.append({
            "decided_room": decided_room,
            "decided_median_rssi": decided_median_rssi,
            "changed": decided_room != previous_room,
            "num_valid_in_window": num_valid,
            "medians_by_room": medians_by_room,
        })
        previous_room = decided_room
        previous_rssi = decided_median_rssi

    return results


def decide_median_hysteresis_windowed(detections, window_sec=8.0, margin=HYSTERESIS_MARGIN):
    """Histerese corrigida: compara o candidato (sala vencedora da mediana
    neste ponto) contra a mediana da sala ATUALMENTE CONFIRMADA na MESMA
    janela corrente - não contra um RSSI histórico congelado de quando essa
    sala foi confirmada pela última vez (ao contrário de decide_hysteresis(),
    que fica intocado para uso ao vivo/compatibilidade). Só usada offline.

    Se a sala atualmente confirmada não tiver nenhuma observação válida na
    janela corrente, o candidato é aceite sem comparação - MAS só se o
    próprio candidato tiver uma mediana válida (janela totalmente vazia de
    RSSI numérico não deve mudar o estado às cegas).

    Retorna um dicionário por deteção de entrada:
    {"decided_room": str|None, "decided_rssi": value|None, "changed": bool,
    "rejected": bool, "candidate_room": str|None, "candidate_rssi": value|None,
    "current_room_rssi": value|None, "difference_db": float|None}
    """
    median_results = decide_median_windowed(detections, window_sec=window_sec)

    results = []
    current_room = None
    current_rssi = None
    previous_room = None

    for m in median_results:
        candidate_room = m["decided_room"]
        medians_by_room = m["medians_by_room"]
        candidate_rssi = medians_by_room.get(candidate_room)
        rejected = False
        difference_db = None
        # RSSI da sala confirmada ANTES desta deteção, na janela ATUAL - a
        # base de comparação usada por esta decisão (None quando não há
        # comparação: primeira deteção, ou sala atual sem dados agora).
        current_room_rssi = medians_by_room.get(current_room) if current_room is not None else None

        if current_room is None or candidate_room == current_room:
            current_room = candidate_room
            current_rssi = candidate_rssi
        elif current_room_rssi is None:
            # Sala atual sem qualquer observação válida na janela: só aceita
            # o candidato se ELE tiver suporte - janela vazia de RSSI não
            # deve mudar o estado às cegas.
            if candidate_rssi is not None:
                current_room = candidate_room
                current_rssi = candidate_rssi
            else:
                rejected = True
        else:
            difference_db = candidate_rssi - current_room_rssi if candidate_rssi is not None else None
            strong_enough = candidate_rssi is not None and candidate_rssi >= current_room_rssi + margin
            if strong_enough:
                current_room = candidate_room
                current_rssi = candidate_rssi
            else:
                rejected = True

        results.append({
            "decided_room": current_room,
            "decided_rssi": current_rssi,
            "changed": current_room != previous_room,
            "rejected": rejected,
            "candidate_room": candidate_room,
            "candidate_rssi": candidate_rssi,
            "current_room_rssi": current_room_rssi,
            "difference_db": difference_db,
        })
        previous_room = current_room

    return results
