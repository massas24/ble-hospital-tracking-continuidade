from flask import Flask, request, jsonify, Response
from flask_cors import CORS
from pymongo import MongoClient, ASCENDING
from werkzeug.security import generate_password_hash, check_password_hash

from datetime import datetime, timedelta

import pytz
import functools
import secrets
import requests
import os
import uuid
import csv
import io
import decision_methods

from bson import ObjectId
from bson.errors import InvalidId
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))
# Configuração da aplicação Flask e CORS.
app = Flask(__name__)
# expose_headers necessário para o frontend ler X-Export-Truncated e
# Content-Disposition numa resposta cross-origin (ver /api/detection-history/export).
CORS(app, expose_headers=["X-Export-Truncated", "Content-Disposition"])
app.secret_key = "change_this_secret"  # alterar antes de produção

# Sobreponível via MIRTH_URL para testar contra mock_mirth.py.
MIRTH_URL = os.environ.get("MIRTH_URL", "http://localhost:6661")

# SECÇÃO 2: CONFIGURAÇÃO DA BASE DE DADOS
client = MongoClient("mongodb://localhost:27017")
# DB_NAME permite apontar para uma base de dados isolada (ex. temp1_db_verify)
# sem tocar nos dados reais de ensaios, no mesmo mongod local.
DB_NAME = os.environ.get("DB_NAME", "temp1_db")
db = client[DB_NAME]

admin_users = db["admin_users"]
beacon_history = db["beacon_history"]
beacon_latest = db["beacon_latest"]
esp_mapping = db["esp_mapping"]
beacon_whitelist = db["beacon_whitelist"]
raw_detections = db["raw_detections"]
ground_truth = db["ground_truth"]
experiments = db["experiments"]
app_state = db["app_state"]

beacon_latest.create_index("mac", unique=True)
beacon_history.create_index([("mac", ASCENDING), ("time", ASCENDING)])
raw_detections.create_index([("mac", ASCENDING), ("time", ASCENDING)])
raw_detections.create_index("batch_id")
# Cobre pesquisas só por sala ou só por tempo, não cobertas pelo índice (mac, time) acima.
raw_detections.create_index([("room", ASCENDING), ("time", ASCENDING)])
raw_detections.create_index("time")
# Suporta a consulta de RSSI por nó em _node_median_rssi (painel de estado dos nós).
raw_detections.create_index([("esp_id", ASCENDING), ("time", ASCENDING)])
ground_truth.create_index([("experiment_id", ASCENDING), ("mac", ASCENDING), ("time", ASCENDING)])
experiments.create_index("experiment_id", unique=True)

live_devices = []  # dispositivos vistos na última ingestão, para /api/data
LOCAL_TIMEZONE = pytz.timezone("Europe/Lisbon")

# Estado de localização e envio dos beacons
# Margem mínima de RSSI (dBm) que a sala nova tem de superar em relação à
# guardada para uma mudança ser aceite (histerese).
HYSTERESIS_MARGIN = int(os.environ.get("HYSTERESIS_MARGIN", "5"))
beacon_locations = {}  # {mac: {"room": ..., "rssi": ...}}
manually_sent_beacons = {}

# Configuração do location_status (mediana + histerese + persistência, calculado em leitura)
MEDIAN_WINDOW = int(os.environ.get("MEDIAN_WINDOW", "5"))
PERSISTENCE_STREAK = int(os.environ.get("PERSISTENCE_STREAK", "3"))
# Nº de raw_detections recentes usadas para recalcular o location_status;
# tem de ser bem maior que MEDIAN_WINDOW/PERSISTENCE_STREAK, ou um beacon
# estável apareceria sempre como "em transição".
LOCATION_STATUS_HISTORY_SIZE = int(os.environ.get("LOCATION_STATUS_HISTORY_SIZE", "30"))
# Um beacon passa a "desconhecida" ao fim deste tempo sem deteções. Sem
# scheduler em segundo plano, isto é recalculado em cada leitura
# (apply_location_status_overrides), não escrito uma vez e deixado a desatualizar.
INACTIVE_TIMEOUT_SEC = int(os.environ.get("INACTIVE_TIMEOUT_SEC", "60"))
# RSSI mínimo considerado pela camada de decisão do location_status; não
# filtra raw_detections em si, só este cálculo. Vazio desativa o filtro.
_min_rssi_env = os.environ.get("MIN_RSSI", "").strip()
MIN_RSSI = float(_min_rssi_env) if _min_rssi_env else None

# Janela (segundos) usada por GET /api/node-status para detections_per_min e median_rssi_dbm.
NODE_RATE_WINDOW_SEC = int(os.environ.get("NODE_RATE_WINDOW_SEC", "300"))

# Identificador do ensaio ativo, gravado em cada raw_detections até ser alterado via /api/experiment.
current_experiment_id = None
current_experiment_started_at = None

# Recupera o ensaio ativo do Mongo ao arrancar, para um restart do backend
# a meio de um ensaio não perder a etiqueta silenciosamente.
_saved_experiment_state = app_state.find_one({"_id": "current_experiment"})
if _saved_experiment_state:
    current_experiment_id = _saved_experiment_state.get("experiment_id")
    current_experiment_started_at = _saved_experiment_state.get("started_at")

# SECÇÃO 3: MIDDLEWARE DE AUTENTICAÇÃO
def auth_required(f):
    """Exige o cabeçalho X-User; não valida credenciais, só a sua presença."""
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        username = request.headers.get("X-User")
        if not username:
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return wrapper

# SECÇÃO 4: ENDPOINTS DE AUTENTICAÇÃO

@app.route("/api/signup", methods=["POST"])
def signup():
    data = request.get_json()

    if not isinstance(data, dict):
        return jsonify({
            "error": "Invalid JSON format. Expected object."
        }), 400

    username = (data.get("username") or "").strip()
    password = data.get("password") or ""

    if not username or not password:
        return jsonify({
            "error": "Username and password are required"
        }), 400

    if admin_users.find_one({"username": username}):
        return jsonify({
            "error": "User already exists"
        }), 400

    admin_users.insert_one({
        "username": username,
        "password": generate_password_hash(password)
    })

    return jsonify({
        "status": "ok",
        "message": "Signup successful"
    })

@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json()

    if not isinstance(data, dict):
        return jsonify({"error": "Invalid JSON format"}), 400

    username = (data.get("username") or "").strip()
    password = data.get("password") or ""

    user = admin_users.find_one({"username": username})

    if not user or not check_password_hash(user["password"], password):
        return jsonify({"error": "Invalid credentials"}), 401

    return jsonify({
        "status": "ok",
        "username": username
    })

@app.route("/api/forgot-password", methods=["POST"])
def forgot_password():
    data = request.json
    username = data.get("username", "").strip().lower()
    user = admin_users.find_one({"username": username})
    # Resposta genérica sempre, para não revelar se a conta existe.
    if not user:
        return jsonify({"message": "If the account exists, a reset email will be sent."}), 200
    token = secrets.token_urlsafe(48)
    expiry = datetime.utcnow() + timedelta(hours=1)
    admin_users.update_one(
        {"username": username},
        {"$set": {"reset_token": token, "reset_expiry": expiry}}
    )
    # TODO: enviar por email; por agora fica só registado no log.
    print(f"Password reset link: http://localhost:3000/reset-password?token={token}")
    return jsonify({"message": "If the account exists, a reset email will be sent."}), 200

@app.route("/api/reset-password", methods=["POST"])
def reset_password():
    data = request.json
    token = data.get("token")
    new_password = data.get("password")
    # Tem de ser string não vazia antes de chegar à query Mongo, ou um valor
    # como {"$ne": null} seria interpretado como operador em vez de token literal.
    if not isinstance(token, str) or not token:
        return jsonify({"error": "Invalid or expired token"}), 400
    if not isinstance(new_password, str) or not new_password:
        return jsonify({"error": "Password is required"}), 400
    user = admin_users.find_one({"reset_token": token})
    if not user or "reset_expiry" not in user or user["reset_expiry"] < datetime.utcnow():
        return jsonify({"error": "Invalid or expired token"}), 400
    admin_users.update_one(
        {"_id": user["_id"]},
        {"$set": {"password": generate_password_hash(new_password)},
         "$unset": {"reset_token": "", "reset_expiry": ""}}
    )
    return jsonify({"status": "ok", "message": "Password reset successful"})

# SECÇÃO 5: GESTÃO DA WHITELIST DE BEACONS
@app.route("/api/whitelist", methods=["GET", "POST"])
@auth_required
def whitelist():
    if request.method == "POST":
        data = request.json
        mac = data.get("mac", "").replace("-", ":").lower().strip().replace('"', '')
        if not mac:
            return jsonify({"error": "No MAC specified"}), 400
        if beacon_whitelist.find_one({"mac": mac}):
            return jsonify({"error": "MAC already whitelisted"}), 400
        beacon_whitelist.insert_one({"mac": mac, "added_at": datetime.now(LOCAL_TIMEZONE)})
        return jsonify({"status": "ok"})
    wl = list(beacon_whitelist.find({}, {"_id": 0}))
    return jsonify(wl)

@app.route("/api/whitelist/<mac>", methods=["DELETE"])
@auth_required
def delete_whitelist(mac):
    mac = mac.replace("-", ":").lower().strip().replace('"', '')
    beacon_whitelist.delete_one({"mac": mac})
    return jsonify({"status": "ok"})

# SECÇÃO 6: GESTÃO DO MAPEAMENTO ESP-SALA
# Configuração de aquisição por esp_id, guardada no mesmo documento que a
# sala - sala e configuração são independentes, um nó pode ter uma, outra, ambas ou nenhuma.
DEFAULT_SCAN_DURATION_SEC = int(os.environ.get("DEFAULT_SCAN_DURATION_SEC", "5"))
DEFAULT_UPLOAD_INTERVAL_MS = int(os.environ.get("DEFAULT_UPLOAD_INTERVAL_MS", "10000"))
ACQUISITION_CONFIG_FIELDS = ("scan_duration_sec", "upload_interval_ms")


def _validate_positive_int(value, field_name):
    """Valida um inteiro positivo, excluindo bool explicitamente
    (isinstance(True, int) é True em Python)."""
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        return f"{field_name} deve ser um número inteiro positivo"
    return None


@app.route("/api/esp-mapping", methods=["GET", "POST"])
@auth_required
def esp_mapping_api():
    if request.method == "POST":
        data = request.json or {}
        esp_id = data.get("esp_id")
        room = data.get("room")
        existing = esp_mapping.find_one({"esp_id": esp_id}) if esp_id else None

        # A sala só é obrigatória no primeiro registo do esp_id; um POST
        # seguinte pode atualizar só a configuração de aquisição.
        if not esp_id or (not room and not (existing and existing.get("room"))):
            return jsonify({"error": "Missing fields"}), 400

        config_fields = {}
        for field in ACQUISITION_CONFIG_FIELDS:
            if field in data:
                error = _validate_positive_int(data[field], field)
                if error:
                    return jsonify({"error": error}), 400
                config_fields[field] = data[field]

        # A configuração de aquisição não pode mudar com um ensaio ativo;
        # só a sala continua a poder ser corrigida.
        if config_fields and current_experiment_id:
            return jsonify({
                "error": (
                    f"Não é possível alterar a configuração de aquisição de '{esp_id}' "
                    f"com um ensaio ativo ('{current_experiment_id}')"
                )
            }), 409

        update_fields = dict(config_fields)
        if room:
            update_fields["room"] = room
        esp_mapping.update_one({"esp_id": esp_id}, {"$set": update_fields}, upsert=True)

        response = {"status": "ok"}
        if config_fields:
            # O nó só relê a configuração ao arrancar.
            response["note"] = "A nova configuração só faz efeito depois de reiniciar o nó fisicamente."
        return jsonify(response)
    rooms = list(esp_mapping.find({}, {"_id": 0}))
    return jsonify(rooms)

@app.route("/api/delete-room/<esp_id>", methods=["DELETE"])
@auth_required
def delete_room(esp_id):
    # Bloqueado com um ensaio ativo - perder a sala de um nó a meio do
    # ensaio deixaria as suas deteções seguintes sem sala atribuída.
    if current_experiment_id and esp_mapping.find_one({"esp_id": esp_id}):
        return jsonify({
            "error": (
                f"Não é possível remover o mapeamento de '{esp_id}' com um ensaio ativo "
                f"('{current_experiment_id}') - as deteções seguintes desse nó ficariam sem sala."
            )
        }), 409
    esp_mapping.delete_one({"esp_id": esp_id})
    return jsonify({"status": "ok"})

# Sem @auth_required: os nós nunca enviam X-User. Um esp_id desconhecido
# recebe os valores globais por omissão em vez de erro.
@app.route("/api/node-config", methods=["GET"])
def node_config():
    esp_id = request.args.get("esp_id") or ""
    mapping = esp_mapping.find_one({"esp_id": esp_id}) if esp_id else None

    result = {}
    for field, default in (
        ("scan_duration_sec", DEFAULT_SCAN_DURATION_SEC),
        ("upload_interval_ms", DEFAULT_UPLOAD_INTERVAL_MS),
    ):
        override = mapping.get(field) if mapping else None
        if override is not None:
            result[field] = override
            result[f"{field}_source"] = "esp_id"
        else:
            result[field] = default
            result[f"{field}_source"] = "default"
    return jsonify(result)

# SECÇÃO 6B: ETIQUETA DE ENSAIO (para raw_detections)
# GET/POST do experiment_id gravado em cada raw_detections enquanto um
# ensaio decorre. Um POST também pode registar metadados de aquisição
# (duração do scan, intervalo, corte de RSSI do firmware) na coleção
# `experiments`, um documento por experiment_id - distinta de
# current_experiment_id, que é só a etiqueta em memória usada para gravar raw_detections.
ACQUISITION_PARAM_FIELDS = ("scan_duration_sec", "upload_interval_ms", "firmware_rssi_cutoff", "notes")


def _now_str():
    return datetime.now(LOCAL_TIMEZONE).strftime("%Y-%m-%d %H:%M:%S")


def _persist_current_experiment():
    """Guarda current_experiment_id/current_experiment_started_at de forma
    durável, num documento único sempre substituído."""
    app_state.update_one(
        {"_id": "current_experiment"},
        {"$set": {"experiment_id": current_experiment_id, "started_at": current_experiment_started_at}},
        upsert=True,
    )


def _experiment_elapsed_min():
    """Minutos decorridos desde o início do ensaio, calculados sempre no
    servidor, nunca no relógio do cliente. None se não houver ensaio ativo."""
    if not current_experiment_id or not current_experiment_started_at:
        return None
    fmt = "%Y-%m-%d %H:%M:%S"
    elapsed = datetime.strptime(_now_str(), fmt) - datetime.strptime(current_experiment_started_at, fmt)
    return elapsed.total_seconds() / 60.0


def _compute_ended_summary(experiment_id):
    """Resumo por MAC do ensaio que acabou de ser encerrado ou substituído.
    Agregação direta em pymongo, sem pandas. Devolve
    {"experiment_id":, "macs": [...]}, um registo por MAC com pelo menos
    uma deteção ou evento de ground truth."""
    detection_stats = {
        row["_id"]: row
        for row in raw_detections.aggregate([
            {"$match": {"experiment_id": experiment_id}},
            {"$group": {
                "_id": "$mac",
                "num_raw_detections": {"$sum": 1},
                "first_detection_time": {"$min": "$time"},
                "last_detection_time": {"$max": "$time"},
            }},
        ])
    }
    ground_truth_stats = {
        row["_id"]: row
        for row in ground_truth.aggregate([
            {"$match": {"experiment_id": experiment_id}},
            {"$group": {"_id": "$mac", "num_ground_truth_events": {"$sum": 1}}},
        ])
    }

    macs = sorted(set(detection_stats) | set(ground_truth_stats))
    mac_summaries = []
    for mac in macs:
        det = detection_stats.get(mac, {})
        gt = ground_truth_stats.get(mac, {})
        num_raw_detections = det.get("num_raw_detections", 0)
        num_ground_truth_events = gt.get("num_ground_truth_events", 0)
        first_time = det.get("first_detection_time")
        last_time = det.get("last_detection_time")

        duration_sec = None
        if first_time and last_time:
            duration_sec = (
                datetime.strptime(last_time, "%Y-%m-%d %H:%M:%S")
                - datetime.strptime(first_time, "%Y-%m-%d %H:%M:%S")
            ).total_seconds()

        mac_summaries.append({
            "mac": mac,
            "num_raw_detections": num_raw_detections,
            "num_ground_truth_events": num_ground_truth_events,
            "num_transitions": max(0, num_ground_truth_events - 1),
            "first_detection_time": first_time,
            "last_detection_time": last_time,
            "duration_sec": duration_sec,
        })

    return {"experiment_id": experiment_id, "macs": mac_summaries}


@app.route("/api/experiment", methods=["GET", "POST"])
@auth_required
def experiment_api():
    global current_experiment_id, current_experiment_started_at
    if request.method == "POST":
        data = request.json or {}
        previous_experiment_id = current_experiment_id
        new_experiment_id = data.get("experiment_id") or None

        # Calculado antes de reatribuir current_experiment_id, sobre o
        # ensaio prestes a ser abandonado (encerramento explícito ou
        # substituição direta por um novo).
        ended_summary = None
        if previous_experiment_id and previous_experiment_id != new_experiment_id:
            ended_summary = _compute_ended_summary(previous_experiment_id)

        current_experiment_id = new_experiment_id
        is_new_experiment = bool(current_experiment_id) and current_experiment_id != previous_experiment_id
        if is_new_experiment:
            current_experiment_started_at = _now_str()
        elif not current_experiment_id:
            current_experiment_started_at = None
        # Caso contrário, mantém-se o mesmo experiment_id: não mexer em
        # current_experiment_started_at para o tempo decorrido continuar correto.

        _persist_current_experiment()

        # Só atualiza `experiments` havendo ensaio ativo e (novos campos de
        # aquisição ou experiment_id novo) - uma reafirmação sem alterações
        # nunca deve apagar parâmetros já registados.
        if current_experiment_id:
            update_fields = {
                field: data[field] for field in ACQUISITION_PARAM_FIELDS if field in data
            }
            if update_fields or is_new_experiment:
                mongo_update = {"$setOnInsert": {"created_at": _now_str()}}
                if update_fields:
                    update_fields["updated_at"] = _now_str()
                    mongo_update["$set"] = update_fields
                experiments.update_one(
                    {"experiment_id": current_experiment_id}, mongo_update, upsert=True,
                )

        response = {
            "status": "ok",
            "experiment_id": current_experiment_id,
            "experiment_started_at": current_experiment_started_at,
            "experiment_elapsed_min": _experiment_elapsed_min(),
        }
        if ended_summary is not None:
            response["ended_summary"] = ended_summary
        return jsonify(response)

    return jsonify({
        "experiment_id": current_experiment_id,
        "experiment_started_at": current_experiment_started_at,
        "experiment_elapsed_min": _experiment_elapsed_min(),
    })


@app.route("/api/experiments", methods=["GET"])
@auth_required
def experiments_view():
    return jsonify(list(experiments.find({}, {"_id": 0})))

# SECÇÃO 6D: EVENTOS DE GROUND TRUTH
# Eventos "beacon X entrou na sala Y à hora T", registados no terreno
# (GroundTruthMarker.js) ou retroativamente com "time" explícito. Os
# intervalos de ground truth são derivados offline a partir destes eventos
# (ver analyze_room_decisions.py).
def _ground_truth_doc_to_json(doc):
    doc["id"] = str(doc.pop("_id"))
    return doc


# Códigos de cenário do guião (secção 9), curtos e sem acentos para
# filtragem estável; os rótulos em português ficam só no frontend
# (SCENARIOS em GroundTruthMarker.js). Não validado no servidor.
SCENARIO_VALUES = ("centro_sala", "junto_parede", "junto_porta", "movimento")


@app.route("/api/ground-truth", methods=["GET", "POST"])
@auth_required
def ground_truth_api():
    if request.method == "POST":
        data = request.json or {}
        mac = data.get("mac", "").replace("-", ":").lower().strip().replace('"', "")
        room = (data.get("room") or "").strip()
        if not mac:
            return jsonify({"error": "No MAC specified"}), 400
        if not room:
            return jsonify({"error": "No room specified"}), 400

        experiment_id = data.get("experiment_id") or current_experiment_id

        # "time" explícito permite registo retroativo sem rede no terreno;
        # caso contrário usa-se a hora do servidor.
        time_str = data.get("time")
        if time_str:
            try:
                datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                return jsonify({"error": "Invalid time format, expected YYYY-MM-DD HH:MM:SS"}), 400
        else:
            time_str = _now_str()

        doc = {
            "mac": mac,
            "room": room,
            "experiment_id": experiment_id,
            "time": time_str,
            "scenario": (data.get("scenario") or "").strip() or None,
            "note": data.get("note") or None,
        }
        result = ground_truth.insert_one(doc)
        doc["_id"] = result.inserted_id
        return jsonify({"status": "ok", **_ground_truth_doc_to_json(doc)})

    query = {}
    experiment_id = request.args.get("experiment_id")
    if experiment_id:
        query["experiment_id"] = experiment_id
    mac = request.args.get("mac")
    if mac:
        query["mac"] = mac.replace("-", ":").lower().strip().replace('"', "")

    events = list(ground_truth.find(query).sort([("time", 1), ("_id", 1)]))
    return jsonify([_ground_truth_doc_to_json(e) for e in events])


@app.route("/api/ground-truth/<event_id>", methods=["DELETE"])
@auth_required
def delete_ground_truth(event_id):
    try:
        oid = ObjectId(event_id)
    except (InvalidId, TypeError):
        return jsonify({"error": "Invalid event id"}), 400
    ground_truth.delete_one({"_id": oid})
    return jsonify({"status": "ok"})

# SECÇÃO 6C: AUXILIARES DE ESTADO DE LOCALIZAÇÃO
# Marca location_status como "desconhecida" (in place) quando a última
# deteção é mais antiga que INACTIVE_TIMEOUT_SEC - recalculado em cada
# leitura, pois não há evento de escrita quando um beacon deixa de enviar dados.
def apply_location_status_overrides(docs):
    now = datetime.now(LOCAL_TIMEZONE)
    for doc in docs:
        time_str = doc.get("time")
        if not time_str:
            continue
        try:
            last_seen = LOCAL_TIMEZONE.localize(datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S"))
        except ValueError:
            continue
        if (now - last_seen).total_seconds() > INACTIVE_TIMEOUT_SEC:
            doc["location_status"] = "desconhecida"
    return docs

# SECÇÃO 7: ENDPOINTS DE DADOS DOS DISPOSITIVOS
@app.route("/api/data", methods=["GET"])
@auth_required
def get_data():
    return jsonify(live_devices)

@app.route("/api/beacon-history/<mac>", methods=["GET"])
@auth_required
def beacon_history_view(mac):
    mac = mac.replace("-", ":").lower().strip().replace('"', '')
    history = list(beacon_history.find({"mac": mac}, {"_id": 0}).sort("time", -1))
    return jsonify(history)

@app.route("/api/beacon-latest", methods=["GET"])
@auth_required
def beacon_latest_view():
    latest = list(beacon_latest.find({}, {"_id": 0}))
    apply_location_status_overrides(latest)
    return jsonify(latest)

@app.route("/api/all-beacons", methods=["GET"])
@auth_required
def get_all_beacons():
    whitelisted = list(beacon_whitelist.find({}, {"_id": 0}))
    active_beacons = list(beacon_latest.find({}, {"_id": 0}))
    apply_location_status_overrides(active_beacons)
    active_macs = {b.get("mac") for b in active_beacons}
    active = [b for b in active_beacons]
    # "Inativo" = na whitelist mas nunca detetado - sem "time" para comparar,
    # fica sempre "desconhecida".
    inactive = [dict(b, location_status="desconhecida") for b in whitelisted if b.get("mac") not in active_macs]
    return jsonify({
        "active": active,
        "inactive": inactive,
        "total_active": len(active),
        "total_inactive": len(inactive)
    })

# SECÇÃO 8: RECEÇÃO DE DADOS BLE
# Estado em memória por esp_id (node_seq, última comunicação, falhas/
# duplicados/reordenações, taxa de deteções) - perdido ao reiniciar o backend.
NODE_SEQ_STATE = {}

# Estado da integração com o Mirth Connect, incluindo o último envio
# bem-sucedido, a última falha e o número de falhas na sessão atual.
MIRTH_STATUS = {"last_success": None, "last_failure": None, "failure_count_session": 0}


def _parse_bledata_payload(payload):
    """Aceita o formato legado e o formato atual dos lotes BLE.
    Devolve os dados das leituras e os metadados do nó; campos inválidos ou
    ausentes são devolvidos como None.
    """
    if isinstance(payload, list):
        return payload, None, None, None, None, None, None
    if isinstance(payload, dict) and isinstance(payload.get("readings"), list):
        batch_esp_id = payload.get("esp_id")
        # Garante que esp_id é uma string antes de o utilizar como chave
        # interna ou numa consulta MongoDB.
        if not isinstance(batch_esp_id, str):
            batch_esp_id = ""
        devices = [dict(r, esp_id=r.get("esp_id") or batch_esp_id) for r in payload["readings"]]
        node_seq = payload.get("node_seq")
        if not isinstance(node_seq, int):
            node_seq = None
        boot_id = payload.get("boot_id")
        if not isinstance(boot_id, int):
            boot_id = None
        scan_duration_sec = payload.get("scan_duration_sec")
        if isinstance(scan_duration_sec, bool) or not isinstance(scan_duration_sec, int):
            scan_duration_sec = None
        upload_interval_ms = payload.get("upload_interval_ms")
        if isinstance(upload_interval_ms, bool) or not isinstance(upload_interval_ms, int):
            upload_interval_ms = None
        return devices, node_seq, payload.get("node_time"), batch_esp_id, boot_id, scan_duration_sec, upload_interval_ms
    return None, None, None, None, None, None, None


def _check_node_seq(esp_id, node_seq, boot_id, now_dt, num_readings):
    """Atualiza o estado técnico do nó e deteta lotes em falta, duplicados
    ou fora de ordem através de node_seq.
    Uma alteração de boot_id inicia uma nova sequência do nó, mantendo os
    contadores acumulados da sessão do backend.
    """
    if not esp_id or node_seq is None or boot_id is None:
        return
    state = NODE_SEQ_STATE.get(esp_id)
    if state is None or state["boot_id"] != boot_id:
        if state is None:
            state = NODE_SEQ_STATE[esp_id] = {
                "gap_count": 0, "duplicate_count": 0, "reorder_count": 0, "recent_batches": [],
            }
        else:
            print(f"Info: {esp_id} reiniciou (novo boot_id) - a reiniciar rastreio de node_seq")
        state["boot_id"] = boot_id
        state["last_seq"] = node_seq
    else:
        last_seq = state["last_seq"]
        if node_seq == last_seq:
            state["duplicate_count"] += 1
            print(f"Aviso: lote duplicado de {esp_id} (node_seq={node_seq} repetido)")
        elif node_seq > last_seq + 1:
            state["gap_count"] += node_seq - last_seq - 1
            print(f"Aviso: {node_seq - last_seq - 1} lote(s) em falta de {esp_id} "
                  f"(esperado {last_seq + 1}, recebido {node_seq})")
        elif node_seq < last_seq:
            state["reorder_count"] += 1
            print(f"Aviso: node_seq de {esp_id} recuou dentro da mesma sessão "
                  f"(esperado >={last_seq + 1}, recebido {node_seq}) - inesperado")
        state["last_seq"] = node_seq

    state["last_seen"] = now_dt.strftime("%Y-%m-%d %H:%M:%S")
    state["recent_batches"].append((now_dt.timestamp(), num_readings))
    cutoff = now_dt.timestamp() - NODE_RATE_WINDOW_SEC
    state["recent_batches"] = [b for b in state["recent_batches"] if b[0] >= cutoff]


def _node_median_rssi(esp_id, now_dt):
    """RSSI mediano (dBm) das deteções de beacons na whitelist para este
    esp_id, na janela NODE_RATE_WINDOW_SEC. Distingue um nó mal posicionado
    ou degradado de um saudável mesmo quando ambos escaneiam à mesma taxa.
    Devolve None se não houver deteções na janela."""
    window_start = now_dt.timestamp() - NODE_RATE_WINDOW_SEC
    window_start_str = datetime.fromtimestamp(window_start, LOCAL_TIMEZONE).strftime("%Y-%m-%d %H:%M:%S")
    docs = raw_detections.find(
        {"esp_id": esp_id, "time": {"$gte": window_start_str}}, {"rssi": 1}
    )
    values = sorted(d["rssi"] for d in docs if isinstance(d.get("rssi"), (int, float)))
    if not values:
        return None
    mid = len(values) // 2
    if len(values) % 2:
        return values[mid]
    return (values[mid - 1] + values[mid]) / 2.0


# Endpoint que recebe lotes de deteções BLE dos nós ESP32. Sem
# autenticação (os nós nunca enviam X-User). Grava sempre em raw_detections
# e recalcula, em paralelo, o location_status e a histerese ao vivo.
@app.route("/api/bledata", methods=["POST"])
def bledata():
    global live_devices, beacon_locations, manually_sent_beacons

    payload = request.get_json()
    devices, node_seq, node_time, batch_esp_id, boot_id, batch_scan_duration_sec, batch_upload_interval_ms = (
        _parse_bledata_payload(payload)
    )
    if devices is None:
        return jsonify({"error": "Invalid data format"}), 400

    now_dt = datetime.now(LOCAL_TIMEZONE)
    now_str = now_dt.strftime("%Y-%m-%d %H:%M:%S")
    # Um id por lote de ingestão, para correlacionar depois as deteções da mesma requisição.
    batch_id = str(uuid.uuid4())
    # Atributo persistente na função para manter o dicionário entre chamadas.
    if not hasattr(bledata, "live_devices_dict"):
        bledata.live_devices_dict = {}

    # len(devices) conta todos os dispositivos do scan, não só os da
    # whitelist - detections_per_min deve refletir se o nó está a escanear
    # normalmente, não quantos beacons de teste estão por perto.
    _check_node_seq(batch_esp_id, node_seq, boot_id, now_dt, len(devices))

    for device in devices:
        mac = device["mac"].replace("-", ":").lower().strip().replace('"', '')
        device["mac"] = mac
        device["time"] = now_str

        # Garante que esp_id é string antes de ser usado numa query Mongo,
        # evitando injeção de operadores (ex. {"$ne": null}).
        esp_id = device.get("esp_id", "")
        if not isinstance(esp_id, str):
            esp_id = ""
        device["esp_id"] = esp_id

        # mapping pode existir só com configuração de aquisição, sem sala definida.
        mapping = esp_mapping.find_one({"esp_id": device.get("esp_id", "")})
        device["room"] = mapping.get("room", "unknown") if mapping else "unknown"
        # Chave por mac+esp para guardar a última observação de cada combinação.
        key = f"{mac}_{device.get('esp_id','')}"
        bledata.live_devices_dict[key] = device.copy()

        if beacon_whitelist.find_one({"mac": mac}):
            # Deteção em bruto para análise offline; beacon_latest guarda só
            # o estado filtrado pela histerese (abaixo).
            raw_detections.insert_one({
                "mac": mac,
                "esp_id": device.get("esp_id", ""),
                "room": device["room"],
                "rssi": device.get("rssi", ""),
                "time": now_str,
                "node_time": node_time,
                "node_seq": node_seq,
                "boot_id": boot_id,
                # Configuração efetiva usada pelo nó neste lote, para
                # detetar divergências na análise offline.
                "scan_duration_sec": batch_scan_duration_sec,
                "upload_interval_ms": batch_upload_interval_ms,
                "batch_id": batch_id,
                "experiment_id": current_experiment_id,
            })

            # location_status é calculado à parte da histerese/Mirth abaixo,
            # replicando a cadeia mediana+histerese+persistência sobre as
            # deteções recentes deste mac. Uma falha aqui nunca deve
            # interromper a ingestão.
            try:
                recent_docs = list(
                    raw_detections.find(
                        {"mac": mac}, {"room": 1, "rssi": 1, "time": 1}
                    ).sort([("time", -1), ("_id", -1)]).limit(LOCATION_STATUS_HISTORY_SIZE)
                )
                recent_docs.reverse()  # volta à ordem cronológica ascendente
                recent_docs = decision_methods.filter_min_rssi(recent_docs, MIN_RSSI)

                mh_results = decision_methods.decide_median_hysteresis(
                    recent_docs, window=MEDIAN_WINDOW, margin=HYSTERESIS_MARGIN
                )
                persistence_results = decision_methods.decide_persistence(
                    [{"room": r["decided_room"]} for r in mh_results], streak=PERSISTENCE_STREAK
                )
                last_mh_room = mh_results[-1]["decided_room"] if mh_results else None
                last_persistence_room = persistence_results[-1]["decided_room"] if persistence_results else None

                if last_persistence_room is None or last_persistence_room != last_mh_room:
                    location_status = "em transição"
                else:
                    location_status = "confirmada"
            except Exception as e:
                print(f"Falha ao calcular location_status para {mac}: {str(e)}")
                location_status = None

            # Deteção de mudança de sala com histerese: só é aceite se o
            # novo RSSI superar o guardado em pelo menos HYSTERESIS_MARGIN
            # dBm. Corre antes de beacon_latest ser escrito, para o
            # dashboard refletir este estado filtrado e estável.
            new_room = device["room"]
            new_rssi = device.get("rssi")
            current = beacon_locations.get(mac)

            if current is not None and current["room"] != new_room:
                stored_rssi = current.get("rssi")
                strong_enough = (
                    isinstance(new_rssi, (int, float))
                    and isinstance(stored_rssi, (int, float))
                    and new_rssi >= stored_rssi + HYSTERESIS_MARGIN
                )
                if strong_enough:
                    old_room = current["room"]
                    mirth_url = MIRTH_URL
                    movement_payload = {
                        "event": "beacon_location_change",
                        "summary": f"Beacon {mac} moved from {old_room} to {new_room}",
                        "beacon": {
                            "esp_id": device.get("esp_id", ""),
                            "esp_name": device.get("esp_name", ""),
                            "room": new_room,
                            "mac": mac,
                            "rssi": device.get("rssi", ""),
                            "time": now_str
                        }
                    }
                    try:
                        requests.post(
                            mirth_url,
                            json=movement_payload,
                            timeout=5,
                            headers={'Content-Type': 'application/json'}
                        )
                        MIRTH_STATUS["last_success"] = now_str
                    except requests.exceptions.RequestException as e:
                        # Prefixo ASCII propositado - símbolos Unicode podem
                        # falhar em consolas Windows (cp1252).
                        print(f"Aviso: falha ao enviar mudança de localização de {mac} para o Mirth: {str(e)}")
                        MIRTH_STATUS["last_failure"] = now_str
                        MIRTH_STATUS["failure_count_session"] += 1

                    # Aceite: atualiza a sala e o RSSI guardados.
                    beacon_locations[mac] = {
                        "room": new_room, "rssi": new_rssi,
                        "esp_id": device.get("esp_id", ""), "esp_name": device.get("esp_name", ""),
                    }
                else:
                    # Rejeitado: sinal insuficiente, mantém a sala guardada.
                    if isinstance(new_rssi, (int, float)) and isinstance(stored_rssi, (int, float)):
                        required_rssi = stored_rssi + HYSTERESIS_MARGIN
                        print(f"Histerese rejeitou mudança de {current['room']} para {new_room} "
                              f"({mac}): RSSI insuficiente: novo={new_rssi}, necessário >={required_rssi}")
                    else:
                        print(f"Histerese rejeitou mudança de {current['room']} para {new_room} "
                              f"({mac}): RSSI em falta ou inválido (novo={new_rssi}, guardado={stored_rssi})")
            else:
                # Primeira deteção ou mesma sala: confirma e atualiza o RSSI guardado.
                beacon_locations[mac] = {
                    "room": new_room, "rssi": new_rssi,
                    "esp_id": device.get("esp_id", ""), "esp_name": device.get("esp_name", ""),
                }

            # Histórico em bruto, sem filtragem - ao contrário do estado
            # escrito em beacon_latest a seguir.
            beacon_history.insert_one({
                "esp_id": device.get("esp_id", ""),
                "esp_name": device.get("esp_name", ""),
                "room": device["room"],
                "mac": mac,
                "rssi": device.get("rssi", ""),
                "time": now_str,
            })
            # room/rssi refletem o estado filtrado pela histerese; "time"
            # atualiza sempre, independentemente da histerese, para a
            # deteção de inatividade continuar correta.
            stable = beacon_locations[mac]
            beacon_latest.update_one(
                {"mac": mac},
                {"$set": {
                    "esp_id": stable.get("esp_id", ""),
                    "esp_name": stable.get("esp_name", ""),
                    "room": stable["room"],
                    "mac": mac,
                    "rssi": stable.get("rssi", ""),
                    "time": now_str,
                    "location_status": location_status,
                }},
                upsert=True
            )

    live_devices = list(bledata.live_devices_dict.values())
    return jsonify({"status": "success", "received": len(devices)})

# SECÇÃO 8B: ESTADO TÉCNICO DOS NÓS
# Junta esp_mapping (para um nó configurado mas nunca visto aparecer como
# offline) com NODE_SEQ_STATE (para um nó a enviar dados mas sem sala
# mapeada aparecer com room=None). O limiar online/offline é decidido no frontend.
@app.route("/api/node-status", methods=["GET"])
@auth_required
def node_status():
    now_dt = datetime.now(LOCAL_TIMEZONE)
    rooms_by_esp = {m["esp_id"]: m.get("room") for m in esp_mapping.find({}, {"_id": 0})}
    all_esp_ids = set(rooms_by_esp.keys()) | set(NODE_SEQ_STATE.keys())

    nodes = []
    for esp_id in sorted(all_esp_ids):
        state = NODE_SEQ_STATE.get(esp_id)
        if state is None:
            nodes.append({
                "esp_id": esp_id, "room": rooms_by_esp.get(esp_id), "boot_id": None,
                "last_seen": None, "seconds_since_last_seen": None,
                "detections_per_min": 0.0, "median_rssi_dbm": None,
                "gap_count": 0, "duplicate_count": 0, "reorder_count": 0,
            })
            continue

        last_seen_str = state.get("last_seen")
        seconds_since_last_seen = None
        if last_seen_str:
            last_seen_dt = LOCAL_TIMEZONE.localize(datetime.strptime(last_seen_str, "%Y-%m-%d %H:%M:%S"))
            seconds_since_last_seen = (now_dt - last_seen_dt).total_seconds()

        # Refiltrado em leitura, para a taxa de um nó silencioso decair
        # para 0 em vez de manter o último valor calculado.
        cutoff = now_dt.timestamp() - NODE_RATE_WINDOW_SEC
        recent = [b for b in state.get("recent_batches", []) if b[0] >= cutoff]
        detections_per_min = sum(n for _, n in recent) / (NODE_RATE_WINDOW_SEC / 60.0)

        nodes.append({
            "esp_id": esp_id,
            "room": rooms_by_esp.get(esp_id),
            "boot_id": state.get("boot_id"),
            "last_seen": last_seen_str,
            "seconds_since_last_seen": seconds_since_last_seen,
            "detections_per_min": round(detections_per_min, 2),
            "median_rssi_dbm": _node_median_rssi(esp_id, now_dt),
            "gap_count": state.get("gap_count", 0),
            "duplicate_count": state.get("duplicate_count", 0),
            "reorder_count": state.get("reorder_count", 0),
        })

    return jsonify({
        "nodes": nodes,
        "rate_window_sec": NODE_RATE_WINDOW_SEC,
        "mirth": MIRTH_STATUS,
    })

# SECÇÃO 9: ENVIO MANUAL DE BEACONS ATIVOS PARA O MIRTH
@app.route("/api/send-active-beacons-to-mirth", methods=["POST"])
@auth_required
def send_active_beacons_to_mirth():
    print("========== MIRTH ENDPOINT CHAMADO ==========")
    global beacon_locations  # mantida por compatibilidade, não usada aqui

    try:
        active_beacons = list(beacon_latest.find({}, {"_id": 0}))
        mirth_url = MIRTH_URL

        beacons_to_send = []
        sent_count = 0

        for beacon in active_beacons:
            mac = beacon.get("mac", "")
            room = beacon.get("room", "")
            beacons_to_send.append({
                "esp_id": beacon.get("esp_id", ""),
                "esp_name": beacon.get("esp_name", ""),
                "room": room,
                "mac": mac,
                "rssi": beacon.get("rssi", ""),
                "time": beacon.get("time", "")
            })
            sent_count += 1

        payload = {
            "beacons": beacons_to_send,
            "summary": "Successfully sent active beacons to Mirth"
        }
        response = requests.post(
            mirth_url,
            json=payload,
            timeout=5,
            headers={'Content-Type': 'application/json'}
        )

        print(f"[MIRTH] URL: {mirth_url}")
        print(f"[MIRTH] HTTP status: {response.status_code}")
        print(f"[MIRTH] Response: {response.text}")
        return jsonify({
            "status": "success",
            "message": "Successfully sent active beacons to Mirth",
            "sent_count": sent_count,
            "total_beacons": len(active_beacons)
        })

    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500

# SECÇÃO 9B: HISTÓRICO DE DETEÇÕES PESQUISÁVEL + EXPORTAÇÃO CSV
def _build_detection_history_query(args):
    """Filtro Mongo para /api/detection-history e /export, a partir de
    room/mac/start/end opcionais. Devolve (query, mensagem_erro); em caso
    de erro o chamador deve responder 400 em vez de ignorar o valor inválido."""
    query = {}
    room = (args.get("room") or "").strip()
    if room:
        query["room"] = room
    mac = (args.get("mac") or "").strip()
    if mac:
        query["mac"] = mac.replace("-", ":").lower().strip().replace('"', "")
    time_filter = {}
    for param, op in (("start", "$gte"), ("end", "$lte")):
        value = (args.get(param) or "").strip()
        if not value:
            continue
        try:
            datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return None, f"{param} inválido, esperado YYYY-MM-DD HH:MM:SS"
        time_filter[op] = value
    if time_filter:
        query["time"] = time_filter
    return query, None


def _parse_limit(args, default, cap):
    """Devolve None se o limite não for numérico, para o chamador responder
    400 em vez de deixar rebentar um ValueError."""
    raw = args.get("limit", str(default))
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return None
    return min(max(value, 1), cap)


# Para consultas pontuais no dashboard - não substitui
# analyze_room_decisions.py para extrair um ensaio inteiro para análise offline.
@app.route("/api/detection-history", methods=["GET"])
@auth_required
def detection_history():
    query, error = _build_detection_history_query(request.args)
    if error:
        return jsonify({"error": error}), 400
    limit = _parse_limit(request.args, default=500, cap=5000)
    if limit is None:
        return jsonify({"error": "limit inválido"}), 400
    # Uma linha extra para detetar truncagem sem uma query de contagem à parte.
    docs = list(raw_detections.find(query, {"_id": 0}).sort("time", -1).limit(limit + 1))
    truncated = len(docs) > limit
    return jsonify({"results": docs[:limit], "truncated": truncated})


EXPORT_ROW_LIMIT = 5000

@app.route("/api/detection-history/export", methods=["GET"])
@auth_required
def detection_history_export():
    query, error = _build_detection_history_query(request.args)
    if error:
        return jsonify({"error": error}), 400
    docs = list(raw_detections.find(query, {"_id": 0}).sort("time", -1).limit(EXPORT_ROW_LIMIT + 1))
    truncated = len(docs) > EXPORT_ROW_LIMIT
    docs = docs[:EXPORT_ROW_LIMIT]
    # Lista de colunas explícita para o cabeçalho existir mesmo com 0 resultados.
    columns = ["time", "mac", "room", "esp_id", "rssi", "node_time", "node_seq", "boot_id", "batch_id", "experiment_id"]
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=columns, extrasaction="ignore")
    writer.writeheader()
    for doc in docs:
        writer.writerow(doc)
    stamp = datetime.now(LOCAL_TIMEZONE).strftime("%Y%m%d_%H%M%S")  # sem ":" - inválido em nomes de ficheiro no Windows
    # Truncagem sinalizada no cabeçalho X-Export-Truncated e no nome do
    # ficheiro, nunca dentro dos dados do CSV, para não poluir uma análise
    # posterior em pandas/Excel.
    filename = f"deteccoes_{stamp}{'_truncated' if truncated else ''}.csv"
    return Response(output.getvalue(), mimetype="text/csv", headers={
        "Content-Disposition": f"attachment; filename={filename}",
        "X-Export-Truncated": "true" if truncated else "false",
    })

# SECÇÃO 10: PONTO DE ENTRADA DA APLICAÇÃO
# PORT permite correr uma instância de verificação isolada em paralelo com a real (porta 5000).
if __name__ == "__main__":
    PORT = int(os.environ.get("PORT", "5000"))
    app.run(host="0.0.0.0", port=PORT, debug=False)
