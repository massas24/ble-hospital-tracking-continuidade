# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

A BLE-based real-time location system (RTLS) for a hospital (ULS Guarda), built as an academic internship continuation project. Beacons on patients/equipment are detected by ESP32 nodes per room, reported to a Flask/MongoDB backend, shown on a React dashboard, and forwarded to Mirth Connect on room changes.

The work in this repo is driven by two guião ("brief") documents in `docs/`:
- `docs/Proposta de Continuidade do Projeto RTLS Hospitalar.md` — the broader technical improvement plan (sections 3.1–3.11: node hardware, decision algorithm, location states, time sync, storage, comms robustness, backend/DB, Mirth event queue, hospital integration, security, dashboard). Its explicit framing: prioritize *room-level localization reliability* over new visual features or scope expansion.
- `docs/Comparação experimental de estratégias simples de localização BLE.docx.md` — the specific experimental methodology: compare baseline / median-window / +hysteresis / +persistence decision methods using raw, synchronized detections; defines the required metrics (accuracy, false-movements/hour, latency percentiles, per-scenario breakdown) and statistical tests (Wilcoxon, Friedman, effect size).
`docs/Final-MCM-FinalReport-BellaGnan.md` documents the original prototype this project continues from (referenced in `app.py`/README for the historical -60dBm firmware cutoff behavior).

When implementing a feature, check whether it's called out in these docs — comments in the code frequently cite a specific guião section as justification for a design choice.

## Commands

**Backend** (`backend/`, Python/Flask). A venv already exists at `backend/venv/`.
```powershell
cd backend
pip install -r requirements.txt              # backend runtime deps
pip install -r requirements-analysis.txt      # extra: pandas/matplotlib/scipy, only for the offline analysis scripts
python app.py                                 # listens on 0.0.0.0:5000 by default
```
Config is via environment variables, optionally loaded from `backend/.env` (copy from `backend/.env.example`; gitignored, one per machine). No `.env` present = every var falls back to the defaults documented in `.env.example`/README. Key ones: `MIRTH_URL`, `HYSTERESIS_MARGIN`, `MEDIAN_WINDOW`, `PERSISTENCE_STREAK`, `INACTIVE_TIMEOUT_SEC`, `MIN_RSSI`, `NODE_RATE_WINDOW_SEC`, `DB_NAME` (default `temp1_db`), `PORT` (default `5000`).

**Frontend** (`frontend/`, React/Bootstrap, `react-scripts` 5.0.1 — use Node 18.x, not 20+):
```powershell
cd frontend
npm install
npm start   # http://localhost:3000
```
`frontend/package.json`'s `"proxy"` **must stay `http://127.0.0.1:5000`, never `"localhost:5000"`** — on Windows, Node resolves `localhost` to IPv6 (`::1`) while Flask only listens on IPv4, producing a proxy `ECONNREFUSED` that shows up in-browser as a generic 500. Changing the proxy value requires restarting `npm start` (CRA only reads it at dev-server boot).

There is no test suite in this repo (no pytest/jest config, no test files) — don't assume one when asked to "run tests".

**Isolated backend instance** (for any verification/experimentation that must not touch real trial data): `DB_NAME` and `PORT` let a second backend process run against a throwaway database on the same local `mongod`, in parallel with the real one:
```powershell
$env:DB_NAME = "temp1_db_verify"; $env:PORT = "5001"; python app.py
```
Never test against the real `temp1_db` / port 5000 — this project has working trial data live in that database.

**Windows shell gotcha**: PowerShell's `curl` is aliased to `Invoke-WebRequest`, which does not accept `-H`/`-d` the way real curl does (`Cannot bind parameter 'Headers'`). Always use `curl.exe` explicitly, or `Invoke-RestMethod`.

**Analysis/dev scripts** (`backend/`, run with `requirements-analysis.txt` installed):
- `analyze_room_decisions.py --experiment-id <id> --mac <mac> [--db-name ...] [--median-window N] [--hysteresis-margin N] [--persistence-streak N] [--min-rssi N] [--no-plots]` — reads `raw_detections` from MongoDB, replays all 4 decision methods (baseline/median/+hysteresis/+persistence) offline, writes per-experiment CSVs + a `run_metadata_<label>.json` + timeline plots to `analysis_output/`.
- `statistical_analysis.py` — reads the CSVs `analyze_room_decisions.py` exported (never touches MongoDB directly) and runs the guião's paired comparison (Wilcoxon/Friedman/effect size) across the 4 methods; has `per-repetition` and `per-transition` CLI subcommands.
- `mock_mirth.py --port <p>` — local stand-in for Mirth Connect (prints received JSON, returns 200); pair with `MIRTH_URL=http://127.0.0.1:<p>`.
- `simulate_hysteresis.py` / `simulate_metrics_trial.py` — synthetic traffic generators that POST to `/api/bledata` using the **legacy bare-list payload format** (no `esp_id`/`node_seq`/`boot_id` at the batch level) — they do not exercise node_seq gap/duplicate tracking or the node-status panel.

## Architecture

**Ingestion → decision → storage is one path, but "current location" is computed twice, independently, for different consumers.** `POST /api/bledata` (no auth — devices don't send `X-User`) is the single ingestion endpoint, accepting either the legacy bare-list payload or the newer batch shape (`{esp_id, node_seq, boot_id, node_time?, readings: [...]}`). For each whitelisted MAC, ingestion writes three things in `app.py`, then two *separate* decision computations run over the same data:
1. `raw_detections` — append-only, every whitelisted-MAC reading, unfiltered. This is the only source the offline analysis scripts (`analyze_room_decisions.py`, `statistical_analysis.py`) read from.
2. `beacon_history` — append-only, raw per-detection room/rssi (same convention as `raw_detections`, kept separate).
3. `beacon_locations` (in-memory) → `beacon_latest` (one doc/MAC, upserted) — the **live hysteresis** path: a room change is only accepted if the new RSSI beats the stored RSSI by `HYSTERESIS_MARGIN`; only *accepted* transitions POST to Mirth Connect and update `beacon_latest.room/rssi`. `beacon_latest.time` updates unconditionally on every detection regardless of hysteresis outcome (needed for staleness detection independent of room changes).
4. `location_status` (`"confirmada"` / `"em transição"` / `"desconhecida"`) — computed *separately* by replaying `decision_methods.py`'s pure median→hysteresis→persistence chain over a recent window of that MAC's `raw_detections`. This is intentionally decoupled from #3's live hysteresis/Mirth logic (different question: "how far can I trust the shown room" vs "should I flip the shown room"). `"desconhecida"` is never written at ingest time — it's applied at **read** time (`apply_location_status_overrides`, used by `/api/beacon-latest` and `/api/all-beacons`) by comparing `beacon_latest.time` against `INACTIVE_TIMEOUT_SEC`, since there's no background scheduler to flip a beacon's status when it silently stops reporting.

`decision_methods.py` holds the pure, stateless median/hysteresis/persistence functions — reused both by the live `location_status` computation in `app.py` and by the offline `analyze_room_decisions.py`, so the two stay behaviorally consistent. `metrics.py` computes ground-truth-vs-decision accuracy/latency/false-movement metrics from the offline replay; it is never imported into `app.py` (deliberate dependency split — analysis deps like pandas/scipy live only in `requirements-analysis.txt`, never `requirements.txt`).

**Node liveness/sequencing** (`NODE_SEQ_STATE`, in-memory, keyed by `esp_id`) tracks per-node `boot_id`/`last_seq` to detect missing/duplicate/reordered batches from the new-format payload only (legacy bare-list senders aren't tracked — no batch-level `esp_id` to key on). It also backs `GET /api/node-status` (detection rate, RSSI health via median over recent whitelisted detections, gap/duplicate/reorder counts) — this state is deliberately *not* persisted across a backend restart (it's "current session" diagnostic info, unlike `current_experiment_id` below).

**Trial/experiment tracking is durable, everything else in-memory is not.** `current_experiment_id`/`current_experiment_started_at` (which experiment new `raw_detections`/`ground_truth` rows get stamped with) are mirrored into a tiny single-document `app_state` collection and reloaded at module import time, specifically so a backend restart mid-trial doesn't silently drop the experiment label onto incoming data with no warning. This is the one piece of otherwise-ephemeral state that gets this treatment — `beacon_locations`, `NODE_SEQ_STATE`, `MIRTH_STATUS` etc. are all allowed to reset on restart because losing them only delays a diagnosis, never mislabels data.

**Timestamp convention**: almost everywhere, times are plain `"%Y-%m-%d %H:%M:%S"` strings (Europe/Lisbon) compared *lexicographically* (works because the format is sortable) — `datetime.strptime` is used only in a few narrow, explicitly-commented spots that need real arithmetic (e.g. computing elapsed minutes or a rolling window cutoff). Don't introduce a second timestamp representation without a specific reason; follow the existing string-comparison convention.

**Auth is intentionally minimal**: `@auth_required` only checks that an `X-User` header is non-empty — it doesn't validate the user exists or check a password. Every `/api/*` route uses it except `/api/bledata`, `/api/signup`, `/api/login`, `/api/forgot-password`, `/api/reset-password`. Don't assume stronger access control exists than this.

**Frontend routing**: `App.js` has `/login`, `/signup`, and `/ground-truth` (wrapped only in `RequireAuth`, deliberately *outside* `DashboardLayout` — it's a mobile-first page for walking around with a beacon, so it has no fixed sidebar). Everything else nests under `DashboardLayout`, which owns its own `<Routes>` for the sidebar pages (whitelist/ESP-mapping admin, live devices, beacon/Mirth management, node status, detection history). Adding a dashboard page means adding both a `<Route>` in `DashboardLayout.js` and a `<Link>` in `Sidebar.js`.

**Firmware** (`esp32-firmware/rtls_node/rtls_node.ino`): syncs time via NTP at boot and periodically, sends the batch payload shape ingestion expects (`esp_id`, sequential `node_seq`, per-boot `boot_id`, optional `node_time`). No store-and-forward, retry/backoff, or node-level auth exists yet on either the firmware or backend side of `/api/bledata`.
