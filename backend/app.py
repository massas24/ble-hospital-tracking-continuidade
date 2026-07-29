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

# Ensure indexes for performance and uniqueness
beacon_latest.create_index("mac", unique=True)  # Ensure one document per MAC
beacon_history.create_index([("mac", ASCENDING), ("time", ASCENDING)])  # Composite index for queries
raw_detections.create_index([("mac", ASCENDING), ("time", ASCENDING)])  # Composite index for queries
raw_detections.create_index("batch_id")  # Group all detections from the same ingestion batch

# In-memory state for currently seen devices (used between requests)
live_devices = []  # List view of devices currently reported
# Configure local timezone for timestamping
LOCAL_TIMEZONE = pytz.timezone("Europe/Lisbon")  # Use Lisbon timezone for local timestamps

#==============================================================================
# BEACON LOCATION AND SENT STATUS STATE
#==============================================================================
# Minimum RSSI improvement (in dBm) a new room's reading must have over the
# currently stored room's reading before a room change is accepted (hysteresis)
HYSTERESIS_MARGIN = 5
# Tracks last known room and RSSI for a beacon by MAC
beacon_locations = {}  # { mac: {"room": ..., "rssi": ...} }
# Tracks beacons that were manually sent (unused/commented state)
manually_sent_beacons = {}

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
@app.route("/api/experiment", methods=["GET", "POST"])
@auth_required
def experiment_api():
    global current_experiment_id
    if request.method == "POST":
        data = request.json or {}
        current_experiment_id = data.get("experiment_id") or None
        return jsonify({"status": "ok", "experiment_id": current_experiment_id})
    # On GET return the currently active experiment_id (may be null)
    return jsonify({"experiment_id": current_experiment_id})

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
    return jsonify(latest)

# Return both active and inactive (whitelisted but not currently active) beacons
@app.route("/api/all-beacons", methods=["GET"])
@auth_required
def get_all_beacons():
    whitelisted = list(beacon_whitelist.find({}, {"_id": 0}))
    active_beacons = list(beacon_latest.find({}, {"_id": 0}))
    active_macs = {b.get("mac") for b in active_beacons}  # Set of active MACs
    active = [b for b in active_beacons]
    inactive = [b for b in whitelisted if b.get("mac") not in active_macs]
    return jsonify({
        "active": active,
        "inactive": inactive,
        "total_active": len(active),
        "total_inactive": len(inactive)
    })

#==============================================================================
# SECTION 8: BLE DATA INGESTION
#==============================================================================
# Endpoint that receives a batch of BLE scans from ESP devices
@app.route("/api/bledata", methods=["POST"])
def bledata():
    # Declare globals used for storing ephemeral state
    global live_devices, beacon_locations, manually_sent_beacons

    devices = request.get_json()  # Expect a JSON array of device dicts
    # Validate payload type
    if not isinstance(devices, list):
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
            # (kept separate from beacon_history/beacon_latest, which already
            # reflect the hysteresis-based room decision)
            raw_detections.insert_one({
                "mac": mac,
                "esp_id": device.get("esp_id", ""),
                "room": device["room"],
                "rssi": device.get("rssi", ""),
                "time": now_str,
                "batch_id": batch_id,
                "experiment_id": current_experiment_id,
            })
            # Append to historical collection
            beacon_history.insert_one({
                "esp_id": device.get("esp_id", ""),
                "esp_name": device.get("esp_name", ""),
                "room": device["room"],
                "mac": mac,
                "rssi": device.get("rssi", ""),
                "time": now_str,
            })
            # Upsert latest state for this MAC
            beacon_latest.update_one(
                {"mac": mac},
                {"$set": {
                    "esp_id": device.get("esp_id", ""),
                    "esp_name": device.get("esp_name", ""),
                    "room": device["room"],
                    "mac": mac,
                    "rssi": device.get("rssi", ""),
                    "time": now_str,
                }},
                upsert=True
            )
            # Location-change detection with hysteresis: only accept a room
            # change if the new RSSI is at least HYSTERESIS_MARGIN dBm
            # stronger than the RSSI stored for the current room
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
                        # Log failure but do not fail the whole ingestion
                        print(f"✗ Failed to send location change for {mac} to Mirth: {str(e)}")

                    # Accepted: update stored room/RSSI to the new reading
                    beacon_locations[mac] = {"room": new_room, "rssi": new_rssi}
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
                beacon_locations[mac] = {"room": new_room, "rssi": new_rssi}
 
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
