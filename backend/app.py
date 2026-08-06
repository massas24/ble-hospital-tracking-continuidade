#==============================================================================
# SECTION 1: IMPORTS AND INITIALIZATION
#==============================================================================
# Import Flask core pieces: app creation, access to request body, and JSON helper
from flask import Flask, request, jsonify  # Flask web framework utilities
# Import CORS helper to allow cross-origin requests from the frontend
from flask_cors import CORS  # Enables Cross-Origin Resource Sharing
# MongoDB client and index direction constant
from pymongo import MongoClient, ASCENDING  # MongoDB client and sorting/index constant
# Password hashing helpers for secure password storage and verification
from werkzeug.security import generate_password_hash, check_password_hash
# Date/time helpers for timestamps and expiry calculations
from datetime import datetime, timedelta
# Timezone handling library
import pytz
# Utilities for wrapping routes with auth check
import functools
# Secure token generator for reset links
import secrets
# HTTP client used to POST events to external system (Mirth)
import requests
# Used to read the Mirth endpoint from an environment variable
import os
# Generates a unique id per ingestion batch, for raw detection logging
import uuid
# Pure median/hysteresis/persistence decision functions, reused here to
# compute location_status live without touching the existing hysteresis path
import decision_methods
# Used to convert ground_truth's Mongo _id into a client-usable string id
# (the one collection in this app where clients need to reference/delete a
# specific document by id, e.g. to undo a mistaken field tap)
from bson import ObjectId
from bson.errors import InvalidId
# Loads backend/.env into os.environ, if that file exists, so the env vars
# below don't have to be set manually in every new terminal
from dotenv import load_dotenv

# Explicit path (not just load_dotenv()'s default cwd-search) so this works
# the same regardless of which directory app.py is launched from. Silently
# does nothing if backend/.env doesn't exist - every os.environ.get(...)
# below then falls back to its existing default, unchanged from today.
load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))
#------------------------------------------------------------------------------
# Initialize Flask app and enable CORS
app = Flask(__name__)  # Create Flask application instance
CORS(app)  # Allow cross-origin requests (used by the React frontend)
app.secret_key = "change_this_secret"  # Secret key used by Flask sessions (should be changed)

# Mirth endpoint - override with the MIRTH_URL env var (e.g. for local testing
# against mock_mirth.py); defaults to the real production Mirth server
MIRTH_URL = os.environ.get("MIRTH_URL", "http://192.168.1.117:6661")

#==============================================================================
# SECTION 2: DATABASE CONFIGURATION
#==============================================================================
# Create a MongoDB client pointing to local MongoDB instance
client = MongoClient("mongodb://localhost:27017")
# Select (or create) database named temp1_db
db = client["temp1_db"]
# Collections used by the app
admin_users = db["admin_users"]  # Stores admin user credentials and reset tokens
beacon_history = db["beacon_history"]  # Stores historical beacon sightings (append-only)
beacon_latest = db["beacon_latest"]  # Stores the latest known state per beacon (upsert)
esp_mapping = db["esp_mapping"]  # Maps ESP device IDs to room names
beacon_whitelist = db["beacon_whitelist"]  # MAC addresses allowed to be tracked
# Raw, unprocessed per-node detections (append-only) - kept alongside
# beacon_history/beacon_latest for offline experimentation with different
# location-decision methods (median, hysteresis, persistence, ...)
raw_detections = db["raw_detections"]
# Ground truth: manually-recorded "beacon X was really in room Y at time T"
# events, tapped in the field via the /ground-truth mobile page. Offline
# analysis pairs consecutive events per (experiment_id, mac) into intervals.
ground_truth = db["ground_truth"]
# Acquisition-time trial metadata (scan duration/interval, firmware RSSI
# cutoff), one document per experiment_id - distinct from the transient
# current_experiment_id label, which only stamps raw_detections.
experiments = db["experiments"]

# Ensure indexes for performance and uniqueness
beacon_latest.create_index("mac", unique=True)  # Ensure one document per MAC
beacon_history.create_index([("mac", ASCENDING), ("time", ASCENDING)])  # Composite index for queries
raw_detections.create_index([("mac", ASCENDING), ("time", ASCENDING)])  # Composite index for queries
raw_detections.create_index("batch_id")  # Group all detections from the same ingestion batch
ground_truth.create_index([("experiment_id", ASCENDING), ("mac", ASCENDING), ("time", ASCENDING)])
experiments.create_index("experiment_id", unique=True)

# In-memory state for currently seen devices (used between requests)
live_devices = []  # List view of devices currently reported
# Configure local timezone for timestamping
LOCAL_TIMEZONE = pytz.timezone("Europe/Lisbon")  # Use Lisbon timezone for local timestamps

#==============================================================================
# BEACON LOCATION AND SENT STATUS STATE
#==============================================================================
# Minimum RSSI improvement (in dBm) a new room's reading must have over the
# currently stored room's reading before a room change is accepted (hysteresis)
HYSTERESIS_MARGIN = int(os.environ.get("HYSTERESIS_MARGIN", "5"))
# Tracks last known room and RSSI for a beacon by MAC
beacon_locations = {}  # { mac: {"room": ..., "rssi": ...} }
# Tracks beacons that were manually sent (unused/commented state)
manually_sent_beacons = {}

#==============================================================================
# LOCATION STATUS CONFIGURATION (median + hysteresis + persistence, read-time)
#==============================================================================
# These mirror analyze_room_decisions.py's own --median-window/--persistence-streak
# defaults (5/3), so live location_status reflects the same configuration
# documented in the offline analysis, while remaining independently tunable.
MEDIAN_WINDOW = int(os.environ.get("MEDIAN_WINDOW", "5"))
PERSISTENCE_STREAK = int(os.environ.get("PERSISTENCE_STREAK", "3"))
# How many recent raw_detections (per mac) feed the live location_status
# recomputation. Must be well above MEDIAN_WINDOW/PERSISTENCE_STREAK: since
# decide_persistence keeps no state between calls, a too-small window would
# make every beacon look permanently "em transição" even when long-stable.
LOCATION_STATUS_HISTORY_SIZE = int(os.environ.get("LOCATION_STATUS_HISTORY_SIZE", "30"))
# A whitelisted beacon is reported "desconhecida" once this many seconds have
# passed since its last detection. No background scheduler exists in this
# app, so this is evaluated at read time (see apply_location_status_overrides
# below), not written once and left stale.
INACTIVE_TIMEOUT_SEC = int(os.environ.get("INACTIVE_TIMEOUT_SEC", "60"))
# Minimum RSSI (dBm) for a reading to be considered by the decision layer
# when computing location_status - readings weaker than this are dropped
# before decide_median_hysteresis/decide_persistence ever see them (see
# decision_methods.filter_min_rssi). raw_detections in MongoDB is never
# filtered, only this live computation. Unset/empty means disabled (no
# filtering) - this is a new feature, so it defaults OFF rather than
# guessing a value; set e.g. MIN_RSSI=-60 to reproduce Bella's original
# firmware-side cutoff (see README methodological note).
_min_rssi_env = os.environ.get("MIN_RSSI", "").strip()
MIN_RSSI = float(_min_rssi_env) if _min_rssi_env else None

# Manually-set label for the experimental trial currently running, stamped
# onto every raw_detections document until changed via /api/experiment
current_experiment_id = None

#==============================================================================
# SECTION 3: AUTHENTICATION MIDDLEWARE
#==============================================================================
# Decorator to require a basic header-based auth check for protected routes
def auth_required(f):
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        # Read username from custom header "X-User"
        username = request.headers.get("X-User")
        # If header is missing, return 401 Unauthorized
        if not username:
            return jsonify({"error": "Unauthorized"}), 401
        # Otherwise call the wrapped function
        return f(*args, **kwargs)
    return wrapper

#==============================================================================
# SECTION 4: USER AUTHENTICATION ENDPOINTS
#==============================================================================

# Endpoint to create a new admin user
@app.route("/api/signup", methods=["POST"])
def signup():
    data = request.get_json()

    # Validate JSON
    if not isinstance(data, dict):
        return jsonify({
            "error": "Invalid JSON format. Expected object."
        }), 400

    username = (data.get("username") or "").strip()
    password = data.get("password") or ""

    # Validate fields
    if not username or not password:
        return jsonify({
            "error": "Username and password are required"
        }), 400

    # Check existing user
    if admin_users.find_one({"username": username}):
        return jsonify({
            "error": "User already exists"
        }), 400

    # Store hashed password
    admin_users.insert_one({
        "username": username,
        "password": generate_password_hash(password)
    })

    return jsonify({
        "status": "ok",
        "message": "Signup successful"
    })
# Endpoint to login an admin user
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
# Endpoint to initiate password reset flow
@app.route("/api/forgot-password", methods=["POST"])
def forgot_password():
    data = request.json
    username = data.get("username", "").strip().lower()
    user = admin_users.find_one({"username": username})
    # Always respond with a generic message (do not reveal whether account exists)
    if not user:
        return jsonify({"message": "If the account exists, a reset email will be sent."}), 200
    # Create secure token and expiry time
    token = secrets.token_urlsafe(48)
    expiry = datetime.utcnow() + timedelta(hours=1)
    # Store token and expiry on user document
    admin_users.update_one(
        {"username": username},
        {"$set": {"reset_token": token, "reset_expiry": expiry}}
    )
    # For now, print reset URL to stdout (replace with real email sending in production)
    print(f"Password reset link: http://localhost:3000/reset-password?token={token}")
    return jsonify({"message": "If the account exists, a reset email will be sent."}), 200

# Endpoint to finish password reset using token
@app.route("/api/reset-password", methods=["POST"])
def reset_password():
    data = request.json
    token = data.get("token")
    new_password = data.get("password")
    user = admin_users.find_one({"reset_token": token})  # Find user by token
    # Validate token presence and expiry
    if not user or "reset_expiry" not in user or user["reset_expiry"] < datetime.utcnow():
        return jsonify({"error": "Invalid or expired token"}), 400
    # Update password and remove token/expiry
    admin_users.update_one(
        {"_id": user["_id"]},
        {"$set": {"password": generate_password_hash(new_password)},
         "$unset": {"reset_token": "", "reset_expiry": ""}}
    )
    return jsonify({"status": "ok", "message": "Password reset successful"})

#==============================================================================
# SECTION 5: DEVICE WHITELIST MANAGEMENT
#==============================================================================
# Routes to add/remove/list whitelisted beacon MAC addresses
@app.route("/api/whitelist", methods=["GET", "POST"])
@auth_required
def whitelist():
    if request.method == "POST":
        data = request.json
        # Normalize MAC format and remove stray quotes
        mac = data.get("mac", "").replace("-", ":").lower().strip().replace('"', '')
        # Validate MAC value
        if not mac:
            return jsonify({"error": "No MAC specified"}), 400
        # Prevent duplicates
        if beacon_whitelist.find_one({"mac": mac}):
            return jsonify({"error": "MAC already whitelisted"}), 400
        # Insert with timestamp
        beacon_whitelist.insert_one({"mac": mac, "added_at": datetime.now(LOCAL_TIMEZONE)})
        return jsonify({"status": "ok"})
    # On GET return all whitelisted MACs (exclude internal _id)
    wl = list(beacon_whitelist.find({}, {"_id": 0}))
    return jsonify(wl)

# Route to delete a specific MAC from whitelist
@app.route("/api/whitelist/<mac>", methods=["DELETE"])
@auth_required
def delete_whitelist(mac):
    mac = mac.replace("-", ":").lower().strip().replace('"', '')
    beacon_whitelist.delete_one({"mac": mac})
    return jsonify({"status": "ok"})

#==============================================================================
# SECTION 6: ESP ROOM MAPPING MANAGEMENT
#==============================================================================
# Manage mapping between ESP devices and human-readable room names
@app.route("/api/esp-mapping", methods=["GET", "POST"])
@auth_required
def esp_mapping_api():
    if request.method == "POST":
        data = request.json
        esp_id = data.get("esp_id")
        room = data.get("room")
        # Validate input
        if not esp_id or not room:
            return jsonify({"error": "Missing fields"}), 400
        # Upsert mapping (insert or update existing)
        esp_mapping.update_one({"esp_id": esp_id}, {"$set": {"room": room}}, upsert=True)
        return jsonify({"status": "ok"})
    # On GET return list of mappings
    rooms = list(esp_mapping.find({}, {"_id": 0}))
    return jsonify(rooms)

# Route to delete a mapping by esp_id
@app.route("/api/delete-room/<esp_id>", methods=["DELETE"])
@auth_required
def delete_room(esp_id):
    esp_mapping.delete_one({"esp_id": esp_id})
    return jsonify({"status": "ok"})

#==============================================================================
# SECTION 6B: EXPERIMENT LABELING (for raw_detections)
#==============================================================================
# Get/set the experiment_id manually stamped onto raw_detections while an
# experimental trial is running. Cleared by setting an empty/missing value.
#
# POST also optionally registers acquisition-time trial metadata (scan
# duration/interval, firmware RSSI cutoff - fixed for the duration of a
# trial's data collection) into the separate `experiments` collection, one
# document per experiment_id. This is distinct from current_experiment_id
# itself: that stays a transient in-memory label used only to stamp
# raw_detections; `experiments` is a persisted record of the trial's
# acquisition configuration, kept alongside the data it was collected under.
ACQUISITION_PARAM_FIELDS = ("scan_duration_sec", "upload_interval_ms", "firmware_rssi_cutoff", "notes")


def _now_str():
    return datetime.now(LOCAL_TIMEZONE).strftime("%Y-%m-%d %H:%M:%S")


@app.route("/api/experiment", methods=["GET", "POST"])
@auth_required
def experiment_api():
    global current_experiment_id
    if request.method == "POST":
        data = request.json or {}
        current_experiment_id = data.get("experiment_id") or None

        # Only touch the experiments collection if there is an active
        # experiment_id AND the request actually carries acquisition fields -
        # a bare {"experiment_id": "t1"} re-affirmation must never wipe out
        # acquisition params registered by an earlier call for the same trial.
        if current_experiment_id:
            update_fields = {
                field: data[field] for field in ACQUISITION_PARAM_FIELDS if field in data
            }
            if update_fields:
                update_fields["updated_at"] = _now_str()
                experiments.update_one(
                    {"experiment_id": current_experiment_id},
                    {"$set": update_fields, "$setOnInsert": {"created_at": _now_str()}},
                    upsert=True,
                )

        return jsonify({"status": "ok", "experiment_id": current_experiment_id})
    # On GET return the currently active experiment_id (may be null)
    return jsonify({"experiment_id": current_experiment_id})


# List all registered trials and their acquisition parameters
@app.route("/api/experiments", methods=["GET"])
@auth_required
def experiments_view():
    return jsonify(list(experiments.find({}, {"_id": 0})))

#==============================================================================
# SECTION 6D: GROUND TRUTH EVENTS
#==============================================================================
# Manually-tapped "beacon X entered room Y at time T" events, recorded live
# in the field (see frontend GroundTruthMarker.js) or retroactively with an
# explicit "time". Ground-truth *intervals* are derived offline by pairing
# consecutive events per (experiment_id, mac) - see analyze_room_decisions.py.
def _ground_truth_doc_to_json(doc):
    doc["id"] = str(doc.pop("_id"))
    return doc


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

        # experiment_id defaults to the ambient current_experiment_id, same
        # convention already used when raw_detections stamps its own rows
        experiment_id = data.get("experiment_id") or current_experiment_id

        # Optional explicit time, for retroactive entry when there was no
        # network in the field to tap the event live; otherwise server "now"
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
            "note": data.get("note") or None,
        }
        result = ground_truth.insert_one(doc)
        doc["_id"] = result.inserted_id
        return jsonify({"status": "ok", **_ground_truth_doc_to_json(doc)})

    # GET: list events, optionally filtered, for review in the dashboard
    query = {}
    experiment_id = request.args.get("experiment_id")
    if experiment_id:
        query["experiment_id"] = experiment_id
    mac = request.args.get("mac")
    if mac:
        query["mac"] = mac.replace("-", ":").lower().strip().replace('"', "")

    events = list(ground_truth.find(query).sort([("time", 1), ("_id", 1)]))
    return jsonify([_ground_truth_doc_to_json(e) for e in events])


# Undo a mistaken field tap
@app.route("/api/ground-truth/<event_id>", methods=["DELETE"])
@auth_required
def delete_ground_truth(event_id):
    try:
        oid = ObjectId(event_id)
    except (InvalidId, TypeError):
        return jsonify({"error": "Invalid event id"}), 400
    ground_truth.delete_one({"_id": oid})
    return jsonify({"status": "ok"})

#==============================================================================
# SECTION 6C: LOCATION STATUS HELPERS
#==============================================================================
# Overrides location_status to "desconhecida" (in place) for any doc whose
# last detection is older than INACTIVE_TIMEOUT_SEC. This is the only way to
# surface staleness: a beacon that stops sending never triggers bledata()
# again, so there is no write-time hook to flip its status - it must be
# recomputed at read time, on every request. Docs missing/unparseable "time"
# are left untouched.
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

#==============================================================================
# SECTION 7: DEVICE DATA ENDPOINTS
#==============================================================================
# Returns the in-memory list of live devices detected in the last ingestion
@app.route("/api/data", methods=["GET"])
@auth_required
def get_data():
    return jsonify(live_devices)

# Return historical sightings for a given MAC
@app.route("/api/beacon-history/<mac>", methods=["GET"])
@auth_required
def beacon_history_view(mac):
    mac = mac.replace("-", ":").lower().strip().replace('"', '')  # Normalize MAC
    history = list(beacon_history.find({"mac": mac}, {"_id": 0}).sort("time", -1))  # Newest first
    return jsonify(history)

# Return the latest-known documents for all beacons
@app.route("/api/beacon-latest", methods=["GET"])
@auth_required
def beacon_latest_view():
    latest = list(beacon_latest.find({}, {"_id": 0}))
    apply_location_status_overrides(latest)
    return jsonify(latest)

# Return both active and inactive (whitelisted but not currently active) beacons
@app.route("/api/all-beacons", methods=["GET"])
@auth_required
def get_all_beacons():
    whitelisted = list(beacon_whitelist.find({}, {"_id": 0}))
    active_beacons = list(beacon_latest.find({}, {"_id": 0}))
    apply_location_status_overrides(active_beacons)
    active_macs = {b.get("mac") for b in active_beacons}  # Set of active MACs
    active = [b for b in active_beacons]
    # "Inactive" means whitelisted but never yet detected (no beacon_latest
    # doc at all) - unconditionally "desconhecida" since there's no "time" to
    # compare against.
    inactive = [dict(b, location_status="desconhecida") for b in whitelisted if b.get("mac") not in active_macs]
    return jsonify({
        "active": active,
        "inactive": inactive,
        "total_active": len(active),
        "total_inactive": len(inactive)
    })

#==============================================================================
# SECTION 8: BLE DATA INGESTION
#==============================================================================
# Per-esp_id sequence tracking for missing/duplicate batch detection (guião
# secção 3) - only in memory, same lifetime as beacon_locations (resets on
# backend restart). Keyed by esp_id; each value tracks the boot_id of the
# node's current session, since node_seq restarts at 1 on every firmware
# boot and would otherwise look like duplicates/gaps across a restart.
NODE_SEQ_STATE = {}  # {esp_id: {"boot_id": ..., "last_seq": ...}}


def _parse_bledata_payload(payload):
    """Accepts the legacy shape (a bare list of device dicts, no batch-level
    metadata) and the new batch shape (an object with esp_id/node_seq/
    boot_id/node_time plus a "readings" list). Returns (devices, node_seq,
    node_time, batch_esp_id, boot_id); the new fields are None when absent
    (legacy format, or NTP unsynced at send time for node_time specifically -
    boot_id/node_seq are always sent unconditionally by the new firmware,
    but are defensively coerced to None if missing or the wrong type)."""
    if isinstance(payload, list):
        return payload, None, None, None, None
    if isinstance(payload, dict) and isinstance(payload.get("readings"), list):
        batch_esp_id = payload.get("esp_id") or ""
        devices = [dict(r, esp_id=r.get("esp_id") or batch_esp_id) for r in payload["readings"]]
        node_seq = payload.get("node_seq")
        if not isinstance(node_seq, int):
            node_seq = None
        boot_id = payload.get("boot_id")
        if not isinstance(boot_id, int):
            boot_id = None
        return devices, node_seq, payload.get("node_time"), batch_esp_id, boot_id
    return None, None, None, None, None


def _check_node_seq(esp_id, node_seq, boot_id):
    """Detects missing/duplicate batches per node (guião secção 3) - only
    prints (same convention as the hysteresis-rejection log below), never
    blocks ingestion or persists to Mongo. boot_id identifies a continuous
    running session of the node (node_seq restarts at 0 on every firmware
    boot) - a boot_id change is never compared as a gap/duplicate, it just
    resets tracking for the new session. Without boot_id (legacy format, or
    a missing field) there is no safe way to tell sessions apart, so the
    check is skipped entirely in that case."""
    if not esp_id or node_seq is None or boot_id is None:
        return
    state = NODE_SEQ_STATE.get(esp_id)
    if state is None or state.get("boot_id") != boot_id:
        if state is not None:
            print(f"Info: {esp_id} reiniciou (novo boot_id) - a reiniciar rastreio de node_seq")
        NODE_SEQ_STATE[esp_id] = {"boot_id": boot_id, "last_seq": node_seq}
        return
    last_seq = state["last_seq"]
    if node_seq == last_seq:
        print(f"Aviso: lote duplicado de {esp_id} (node_seq={node_seq} repetido)")
    elif node_seq > last_seq + 1:
        print(f"Aviso: {node_seq - last_seq - 1} lote(s) em falta de {esp_id} "
              f"(esperado {last_seq + 1}, recebido {node_seq})")
    elif node_seq < last_seq:
        print(f"Aviso: node_seq de {esp_id} recuou dentro da mesma sessão "
              f"(esperado >={last_seq + 1}, recebido {node_seq}) - inesperado")
    state["last_seq"] = node_seq


# Endpoint that receives a batch of BLE scans from ESP devices
@app.route("/api/bledata", methods=["POST"])
def bledata():
    # Declare globals used for storing ephemeral state
    global live_devices, beacon_locations, manually_sent_beacons

    payload = request.get_json()
    devices, node_seq, node_time, batch_esp_id, boot_id = _parse_bledata_payload(payload)
    if devices is None:
        return jsonify({"error": "Invalid data format"}), 400

    # Timestamp for all incoming devices
    now_dt = datetime.now(LOCAL_TIMEZONE)
    now_str = now_dt.strftime("%Y-%m-%d %H:%M:%S")
    # One id per ingestion batch (this POST request), so raw detections from
    # the same request can be grouped/correlated later
    batch_id = str(uuid.uuid4())
    # Use a persistent attribute on the function to keep a dict between calls
    if not hasattr(bledata, "live_devices_dict"):
        bledata.live_devices_dict = {}

    # Runs once per POST, before/independent of the per-device loop below -
    # so a valid batch with 0 readings still counts towards the sequence.
    _check_node_seq(batch_esp_id, node_seq, boot_id)

    # Process each reported device
    for device in devices:
        # Normalize MAC and set into the device record
        mac = device["mac"].replace("-", ":").lower().strip().replace('"', '')
        device["mac"] = mac
        device["time"] = now_str  # Add timestamp

        # Map esp_id to a room name, default to 'unknown'
        mapping = esp_mapping.find_one({"esp_id": device.get("esp_id", "")})
        device["room"] = mapping["room"] if mapping else "unknown"
        # Unique key per mac+esp to store latest observation
        key = f"{mac}_{device.get('esp_id','')}"
        bledata.live_devices_dict[key] = device.copy()

        # Only persist and notify for whitelisted MACs
        if beacon_whitelist.find_one({"mac": mac}):
            # Append raw, unprocessed detection for offline experimentation
            # (kept separate from beacon_history, which stays raw on the same
            # convention, and from beacon_latest, which reflects the
            # hysteresis-filtered room decision - see below)
            raw_detections.insert_one({
                "mac": mac,
                "esp_id": device.get("esp_id", ""),
                "room": device["room"],
                "rssi": device.get("rssi", ""),
                "time": now_str,
                "node_time": node_time,
                "node_seq": node_seq,
                "boot_id": boot_id,
                "batch_id": batch_id,
                "experiment_id": current_experiment_id,
            })

            # Live location_status (confirmada/em transição), computed
            # separately from the hysteresis/Mirth logic below by replaying
            # decision_methods' pure median+hysteresis+persistence chain over
            # a recent window of this mac's raw_detections. Does not affect
            # beacon_locations, the Mirth notification, or the room/rssi/time
            # written to beacon_latest just below - failure here must never
            # break ingestion.
            try:
                recent_docs = list(
                    raw_detections.find(
                        {"mac": mac}, {"room": 1, "rssi": 1, "time": 1}
                    ).sort([("time", -1), ("_id", -1)]).limit(LOCATION_STATUS_HISTORY_SIZE)
                )
                recent_docs.reverse()  # back to ascending chronological order
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

            # Location-change detection with hysteresis: only accept a room
            # change if the new RSSI is at least HYSTERESIS_MARGIN dBm
            # stronger than the RSSI stored for the current room. Runs
            # BEFORE beacon_latest is written below, so beacon_latest can
            # reflect this filtered/stable state - previously beacon_latest
            # (and so the dashboard) always showed whichever node most
            # recently reported, completely unfiltered, which with several
            # nodes concurrently seeing the same beacon made the dashboard
            # flicker between rooms every few seconds regardless of the
            # hysteresis margin (hysteresis only ever gated the Mirth
            # notification below, never what got displayed).
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
                    mirth_url = MIRTH_URL  # Destination for notifications
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
                        # Post movement event to Mirth with a short timeout
                        requests.post(
                            mirth_url,
                            json=movement_payload,
                            timeout=5,
                            headers={'Content-Type': 'application/json'}
                        )
                    except requests.exceptions.RequestException as e:
                        # Log failure but do not fail the whole ingestion.
                        # Plain ASCII prefix on purpose - a "✗" here used to
                        # raise UnicodeEncodeError on Windows consoles (cp1252
                        # can't encode it), which crashed this exact request
                        # with a 500 despite this try/except's whole point
                        # being to swallow Mirth failures without failing.
                        print(f"Aviso: falha ao enviar mudança de localização de {mac} para o Mirth: {str(e)}")

                    # Accepted: update stored room/RSSI to the new reading
                    beacon_locations[mac] = {
                        "room": new_room, "rssi": new_rssi,
                        "esp_id": device.get("esp_id", ""), "esp_name": device.get("esp_name", ""),
                    }
                else:
                    # Rejected: not enough signal improvement yet - keep the
                    # previously stored room/RSSI unchanged
                    if isinstance(new_rssi, (int, float)) and isinstance(stored_rssi, (int, float)):
                        required_rssi = stored_rssi + HYSTERESIS_MARGIN
                        print(f"Histerese rejeitou mudança de {current['room']} para {new_room} "
                              f"({mac}): RSSI insuficiente: novo={new_rssi}, necessário >={required_rssi}")
                    else:
                        print(f"Histerese rejeitou mudança de {current['room']} para {new_room} "
                              f"({mac}): RSSI em falta ou inválido (novo={new_rssi}, guardado={stored_rssi})")
            else:
                # First sighting since startup, or still in the same room:
                # (re)confirm the stored room and refresh the RSSI baseline
                beacon_locations[mac] = {
                    "room": new_room, "rssi": new_rssi,
                    "esp_id": device.get("esp_id", ""), "esp_name": device.get("esp_name", ""),
                }

            # Append to historical collection - raw/unfiltered, same
            # convention as raw_detections, on purpose (not the hysteresis-
            # filtered state written to beacon_latest just below).
            beacon_history.insert_one({
                "esp_id": device.get("esp_id", ""),
                "esp_name": device.get("esp_name", ""),
                "room": device["room"],
                "mac": mac,
                "rssi": device.get("rssi", ""),
                "time": now_str,
            })
            # Upsert latest state for this MAC - room/rssi/esp_id/esp_name
            # now reflect the hysteresis-filtered beacon_locations state
            # (stable, only changes on an accepted transition), not the raw
            # per-detection reading just above. "time" stays unconditional
            # (updates on every detection regardless of hysteresis outcome)
            # so staleness detection (INACTIVE_TIMEOUT_SEC,
            # apply_location_status_overrides) keeps working correctly for a
            # beacon that's still being seen but just hasn't had an accepted
            # room change recently.
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

    # Convert live data dict to a list for the /api/data endpoint
    live_devices = list(bledata.live_devices_dict.values())
    return jsonify({"status": "success", "received": len(devices)})

#==============================================================================
# SECTION 9: SEND ACTIVE BEACONS TO MIRTH (MANUAL)
#==============================================================================
# Manual endpoint to push all currently active beacons to Mirth at once
@app.route("/api/send-active-beacons-to-mirth", methods=["POST"])
@auth_required
def send_active_beacons_to_mirth():
    global beacon_locations  # (left for compatibility; not used for sending)

    try:
        # Read latest-known beacons from DB
        active_beacons = list(beacon_latest.find({}, {"_id": 0}))
        mirth_url = MIRTH_URL

        beacons_to_send = []  # Accumulate payload
        sent_count = 0

        for beacon in active_beacons:
            mac = beacon.get("mac", "")
            room = beacon.get("room", "")
            # Add structured beacon info to array
            beacons_to_send.append({
                "esp_id": beacon.get("esp_id", ""),
                "esp_name": beacon.get("esp_name", ""),
                "room": room,
                "mac": mac,
                "rssi": beacon.get("rssi", ""),
                "time": beacon.get("time", "")
            })
            sent_count += 1

        # Build payload and POST to Mirth
        payload = {
            "beacons": beacons_to_send,
            "summary": "Successfully sent active beacons to Mirth"
        }
        requests.post(
            mirth_url,
            json=payload,
            timeout=5,
            headers={'Content-Type': 'application/json'}
        )

        # Return summary of operation
        return jsonify({
            "status": "success",
            "message": "Successfully sent active beacons to Mirth",
            "sent_count": sent_count,
            "total_beacons": len(active_beacons)
        })

    except Exception as e:
        # On any error return 500 with the exception message
        return jsonify({"status": "error", "error": str(e)}), 500

#==============================================================================
# SECTION 10: APPLICATION ENTRY POINT
#==============================================================================
# Run the Flask app when the file is executed directly
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
