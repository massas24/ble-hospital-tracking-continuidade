import { useState, useEffect } from "react";
import axios from "axios";

const EMPTY_FORM = { esp_id: "", room: "", scan_duration_sec: "", upload_interval_ms: "" };

function AdminPanel() {
  const [mappings, setMappings] = useState([]);
  const [form, setForm] = useState(EMPTY_FORM);
  const [message, setMessage] = useState(null); // { type: "success" | "danger", text }
  const [defaults, setDefaults] = useState(null); // { scan_duration_sec, upload_interval_ms } - resolved global defaults
  const username = localStorage.getItem("username");

  // Fetch mappings on component mount and when username changes
  useEffect(() => {
    if (!username) return;
    axios.get("/api/esp-mapping", { headers: { "X-User": username } })
      .then(res => setMappings(res.data))
      .catch(console.error);
    // GET /api/node-config with no esp_id resolves straight to the global
    // defaults (guião secção 7) - the same call a node itself makes at
    // boot for an esp_id with no override. Fetched once so the "padrão"
    // cells below can show the actual number, not just the bare word.
    axios.get("/api/node-config")
      .then(res => setDefaults({
        scan_duration_sec: res.data.scan_duration_sec,
        upload_interval_ms: res.data.upload_interval_ms,
      }))
      .catch(console.error);
  }, [username]);

  const refreshMappings = async () => {
    const res = await axios.get("/api/esp-mapping", { headers: { "X-User": username } });
    setMappings(res.data);
  };

  // Add/update mapping. Room is only required the first time an esp_id is
  // registered (mirrors the backend's own rule) - so an already-mapped node
  // can have just its scan config changed without retyping its room.
  const addMapping = async () => {
    setMessage(null);
    const espId = form.esp_id.trim();
    const room = form.room.trim();
    const alreadyHasRoom = mappings.some(m => m.esp_id === espId && m.room);

    if (!espId) {
      setMessage({ type: "danger", text: "Preenche o ESP ID." });
      return;
    }
    if (!room && !alreadyHasRoom) {
      setMessage({ type: "danger", text: "Preenche o Room (é o primeiro registo deste ESP ID)." });
      return;
    }

    const payload = { esp_id: espId };
    if (room) payload.room = room;

    // scan_duration_sec/upload_interval_ms (guião secção 7) are optional -
    // only sent when filled in, and validated client-side first so a typo
    // doesn't need a round trip to discover (the backend re-validates the
    // same rule regardless, this is just a faster echo of it).
    for (const [field, label] of [
      ["scan_duration_sec", "Scan Duration (s)"],
      ["upload_interval_ms", "Upload Interval (ms)"],
    ]) {
      const raw = form[field].trim();
      if (!raw) continue;
      const value = Number(raw);
      if (!Number.isInteger(value) || value <= 0) {
        setMessage({ type: "danger", text: `${label} tem de ser um número inteiro positivo.` });
        return;
      }
      payload[field] = value;
    }

    try {
      const res = await axios.post("/api/esp-mapping", payload, { headers: { "X-User": username } });
      await refreshMappings();
      setForm(EMPTY_FORM);
      // The backend adds a "reinicia para aplicar" note whenever scan
      // config actually changed - surface it verbatim when present, since
      // it's the easiest place to miss that the change isn't live yet.
      setMessage({ type: "success", text: res.data.note || "Mapeamento guardado." });
    } catch (err) {
      setMessage({ type: "danger", text: err.response?.data?.error || "Failed to add mapping" });
    }
  };

  // Delete mapping
  const deleteMapping = async (esp_id) => {
    setMessage(null);
    try {
      await axios.delete(`/api/delete-room/${esp_id}`, { headers: { "X-User": username } });
      setMappings(mappings.filter(m => m.esp_id !== esp_id));
    } catch (err) {
      // Surfaces the backend's real reason (e.g. blocked because a trial is
      // active) instead of a generic message - the same 409 guard the
      // config fields above are already subject to.
      setMessage({ type: "danger", text: err.response?.data?.error || "Failed to delete mapping" });
    }
  };

  return (
  <div className="card p-4" style={{ maxWidth: 900, margin: "auto", boxShadow: "0 6px 24px #e3e6f0", background: '#fff', color: '#5a5c69', borderRadius: '0.35rem' }}>
      <h2>ESP Mappings</h2>
      {message && (
        <div className={`alert alert-${message.type} d-flex justify-content-between align-items-center`} role="alert">
          <span>{message.text}</span>
          <button type="button" className="btn-close" aria-label="Fechar" onClick={() => setMessage(null)}></button>
        </div>
      )}
      <div className="mb-3">
        <input
          placeholder="ESP ID"
          value={form.esp_id}
          onChange={e => setForm({ ...form, esp_id: e.target.value })}
          className="form-control mb-2"
        />
        <input
          placeholder="Room"
          value={form.room}
          onChange={e => setForm({ ...form, room: e.target.value })}
          className="form-control mb-2"
        />
        <div className="row g-2 mb-2">
          <div className="col">
            <input
              type="number"
              min="1"
              step="1"
              placeholder="Scan Duration (s) - opcional"
              value={form.scan_duration_sec}
              onChange={e => setForm({ ...form, scan_duration_sec: e.target.value })}
              className="form-control"
            />
          </div>
          <div className="col">
            <input
              type="number"
              min="1"
              step="1"
              placeholder="Upload Interval (ms) - opcional"
              value={form.upload_interval_ms}
              onChange={e => setForm({ ...form, upload_interval_ms: e.target.value })}
              className="form-control"
            />
          </div>
        </div>
        <small className="text-muted d-block mb-2">
          Scan Duration / Upload Interval são opcionais (guião secção 7) - em branco usa os valores globais.
          Bloqueado durante um ensaio ativo, e só faz efeito depois de reiniciar fisicamente o nó.
        </small>
        <button onClick={addMapping} className="btn btn-primary">Add Mapping</button>
      </div>
      <table className="table table-bordered">
        <thead>
          <tr>
            <th>ESP ID</th>
            <th>Room</th>
            <th>Scan (s)</th>
            <th>Upload (ms)</th>
            <th>Action</th>
          </tr>
        </thead>
        <tbody>
          {mappings.length ? (
            mappings.map((m, idx) => (
              <tr key={idx}>
                <td>{m.esp_id}</td>
                <td>{m.room || <span className="text-muted">&mdash;</span>}</td>
                <td>{m.scan_duration_sec ?? (
                  <span className="text-muted">padrão{defaults ? ` (${defaults.scan_duration_sec}s)` : ""}</span>
                )}</td>
                <td>{m.upload_interval_ms ?? (
                  <span className="text-muted">padrão{defaults ? ` (${defaults.upload_interval_ms}ms)` : ""}</span>
                )}</td>
                <td>
                  <button onClick={() => deleteMapping(m.esp_id)} className="btn btn-danger btn-sm">
                    Delete
                  </button>
                </td>
              </tr>
            ))
          ) : (
            <tr>
              <td colSpan="5" className="text-center">No mappings yet</td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}

export default AdminPanel;
