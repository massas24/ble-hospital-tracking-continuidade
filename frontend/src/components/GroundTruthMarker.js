// GroundTruthMarker - mobile-friendly page for tapping "I am now in room X"
// while physically walking around with a beacon, away from the laptop.
// Rendered as a top-level route (see App.js), outside DashboardLayout, so it
// doesn't inherit the fixed-sidebar desktop layout.
import { useState, useEffect } from "react";
import axios from "axios";

function GroundTruthMarker() {
  const username = localStorage.getItem("username");
  const headers = { "X-User": username };

  const [experimentId, setExperimentId] = useState(null);
  const [macs, setMacs] = useState([]);
  const [rooms, setRooms] = useState([]);
  const [selectedMac, setSelectedMac] = useState(localStorage.getItem("groundTruthMac") || "");
  const [recentTaps, setRecentTaps] = useState([]);
  const [error, setError] = useState("");
  const [manualTime, setManualTime] = useState(false);
  const [manualTimeValue, setManualTimeValue] = useState("");

  useEffect(() => {
    axios.get("/api/experiment", { headers })
      .then(res => setExperimentId(res.data.experiment_id))
      .catch(() => setExperimentId(null));

    axios.get("/api/whitelist", { headers })
      .then(res => setMacs(res.data.map(w => w.mac)))
      .catch(() => setMacs([]));

    axios.get("/api/esp-mapping", { headers })
      .then(res => {
        const distinctRooms = [...new Set(res.data.map(m => m.room))].sort();
        setRooms(distinctRooms);
      })
      .catch(() => setRooms([]));
  }, []);

  const chooseMac = (mac) => {
    setSelectedMac(mac);
    localStorage.setItem("groundTruthMac", mac);
  };

  const tapRoom = async (room) => {
    setError("");
    if (!selectedMac) {
      setError("Escolhe primeiro o MAC do beacon");
      return;
    }
    const body = { mac: selectedMac, room };
    if (manualTime && manualTimeValue) {
      body.time = manualTimeValue.replace("T", " ") + ":00";
    }
    try {
      const res = await axios.post("/api/ground-truth", body, { headers });
      setRecentTaps(prev => [res.data, ...prev].slice(0, 20));
    } catch (err) {
      setError(err.response?.data?.error || "Falha ao registar a marcação");
    }
  };

  const undoTap = async (id) => {
    try {
      await axios.delete(`/api/ground-truth/${id}`, { headers });
      setRecentTaps(prev => prev.filter(t => t.id !== id));
    } catch (err) {
      setError("Falha ao desfazer");
    }
  };

  return (
    <div style={{ maxWidth: 480, margin: "auto", padding: 16 }}>
      <h3 className="mb-3">Ground Truth</h3>

      {experimentId ? (
        <div className="alert alert-info py-2">Ensaio atual: <strong>{experimentId}</strong></div>
      ) : (
        <div className="alert alert-danger py-2">
          Sem experiment_id ativo — as marcações vão ficar sem ensaio associado. Define um em <code>/api/experiment</code> antes de começares.
        </div>
      )}

      <div className="mb-3">
        <label className="form-label">Beacon (MAC)</label>
        <select
          className="form-select"
          value={selectedMac}
          onChange={e => chooseMac(e.target.value)}
        >
          <option value="">-- escolhe --</option>
          {macs.map(mac => <option key={mac} value={mac}>{mac}</option>)}
        </select>
      </div>

      <div className="form-check mb-3">
        <input
          className="form-check-input"
          type="checkbox"
          id="manualTimeCheck"
          checked={manualTime}
          onChange={e => setManualTime(e.target.checked)}
        />
        <label className="form-check-label" htmlFor="manualTimeCheck">
          Hora manual (entrada retroativa, sem rede na altura)
        </label>
        {manualTime && (
          <input
            type="datetime-local"
            className="form-control mt-2"
            value={manualTimeValue}
            onChange={e => setManualTimeValue(e.target.value)}
          />
        )}
      </div>

      {error && <div className="alert alert-warning py-2">{error}</div>}

      <div className="d-grid gap-2 mb-4">
        {rooms.map(room => (
          <button
            key={room}
            className="btn btn-primary btn-lg"
            onClick={() => tapRoom(room)}
          >
            Estou agora em: {room}
          </button>
        ))}
        {rooms.length === 0 && (
          <p className="text-muted">Nenhuma sala mapeada ainda (ver ESP Mapping).</p>
        )}
      </div>

      <h5>Últimas marcações</h5>
      <ul className="list-group">
        {recentTaps.map(tap => (
          <li key={tap.id} className="list-group-item d-flex justify-content-between align-items-center">
            <span>{tap.time} — {tap.room}</span>
            <button className="btn btn-sm btn-outline-danger" onClick={() => undoTap(tap.id)}>
              Desfazer
            </button>
          </li>
        ))}
        {recentTaps.length === 0 && (
          <li className="list-group-item text-muted">Ainda sem marcações nesta sessão.</li>
        )}
      </ul>
    </div>
  );
}

export default GroundTruthMarker;
