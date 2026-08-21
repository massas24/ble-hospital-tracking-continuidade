import { useState, useEffect } from "react";
import axios from "axios";

const EMPTY_FORM = { esp_id: "", room: "", scan_duration_sec: "", upload_interval_ms: "" };

function AdminPanel() {
  const [mappings, setMappings] = useState([]);
  const [form, setForm] = useState(EMPTY_FORM);
  const [message, setMessage] = useState(null);
  const [defaults, setDefaults] = useState(null);
  const username = localStorage.getItem("username");

  
  useEffect(() => {
    if (!username) return;
    axios.get("/api/esp-mapping", { headers: { "X-User": username } })
      .then(res => setMappings(res.data))
      .catch(console.error);
    
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
      setMessage({ type: "success", text: res.data.note || "Mapeamento guardado." });
    } catch (err) {
      setMessage({ type: "danger", text: err.response?.data?.error || "Failed to add mapping" });
    }
  };


  const deleteMapping = async (esp_id) => {
    setMessage(null);
    try {
      await axios.delete(`/api/delete-room/${esp_id}`, { headers: { "X-User": username } });
      setMappings(mappings.filter(m => m.esp_id !== esp_id));
    } catch (err) {
      
      setMessage({ type: "danger", text: err.response?.data?.error || "Failed to delete mapping" });
    }
  };

  return (
  <div className="card p-4 page-card">
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
          Scan Duration / Upload Interval são opcionais - em branco usa os valores globais.
          Bloqueado durante um ensaio ativo, e só faz efeito depois de reiniciar fisicamente o nó.
        </small>
        <button onClick={addMapping} className="btn btn-primary">Add Mapping</button>
      </div>
      <table className="table table-striped">
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
