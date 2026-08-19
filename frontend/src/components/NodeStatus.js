// NodeStatus - technical infrastructure status panel (guião secção 3.11:
// "estado técnico dos nós"). Per esp_id: online/offline (threshold
// adjustable here, not on the server - see OFFLINE_THRESHOLD_STORAGE_KEY),
// last communication, detection rate, RSSI health, and lost/duplicate/
// reordered batch counts, plus a small Mirth Connect delivery status
// section. Backend: GET /api/node-status.
import { useState, useEffect } from "react";
import axios from "axios";
import Badge from "./Badge";

const OFFLINE_THRESHOLD_STORAGE_KEY = "nodeOfflineThresholdSec";
const DEFAULT_OFFLINE_THRESHOLD_SEC = 60;
const POLL_MS = 5000;

function OnlineBadge({ secondsSinceLastSeen, thresholdSec }) {
  if (secondsSinceLastSeen == null) {
    return <Badge tone="secondary">Nunca visto</Badge>;
  }
  if (secondsSinceLastSeen <= thresholdSec) {
    return <Badge tone="success">Online</Badge>;
  }
  return <Badge tone="danger">Offline</Badge>;
}

function formatSeconds(value) {
  if (value == null) return "-";
  if (value < 60) return `${Math.round(value)}s`;
  return `${Math.floor(value / 60)}min ${Math.round(value % 60)}s`;
}

export default function NodeStatus() {
  const username = localStorage.getItem("username");
  const headers = { "X-User": username };

  const [nodes, setNodes] = useState([]);
  const [mirth, setMirth] = useState(null);
  const [rateWindowSec, setRateWindowSec] = useState(null);
  const [error, setError] = useState("");
  const [offlineThreshold, setOfflineThreshold] = useState(
    Number(localStorage.getItem(OFFLINE_THRESHOLD_STORAGE_KEY)) || DEFAULT_OFFLINE_THRESHOLD_SEC
  );

  const refresh = () => {
    axios.get("/api/node-status", { headers })
      .then(res => {
        setNodes(res.data.nodes || []);
        setMirth(res.data.mirth || null);
        setRateWindowSec(res.data.rate_window_sec);
        setError("");
      })
      .catch(() => setError("Falha ao obter o estado dos nós"));
  };

  useEffect(() => {
    refresh();
    const interval = setInterval(refresh, POLL_MS);
    return () => clearInterval(interval);
  }, []);

  const changeThreshold = (value) => {
    const num = Number(value);
    setOfflineThreshold(num);
    localStorage.setItem(OFFLINE_THRESHOLD_STORAGE_KEY, String(num));
  };

  return (
    <div className="card p-4 page-card-wide">
      <h2>Estado dos Nós</h2>

      {error && <div className="alert alert-danger mb-3">{error}</div>}

      <div className="mb-3 d-flex align-items-center gap-2">
        <label htmlFor="offlineThreshold" className="mb-0">Limiar de nó offline (s):</label>
        <input
          id="offlineThreshold"
          type="number"
          min="1"
          className="form-control"
          style={{ width: 100 }}
          value={offlineThreshold}
          onChange={(e) => changeThreshold(e.target.value)}
        />
        <span className="text-muted small">
          Ajuste local, sem reiniciar o backend. Não confundir com o limiar de beacon inativo
          (INACTIVE_TIMEOUT_SEC, página Mirth) - são conceitos diferentes que hoje coincidem por acaso no valor 60.
        </span>
      </div>

      <p className="text-muted small">
        "Deteções/min" conta todo o tráfego BLE do scan (qualquer dispositivo, não só beacons seguidos) -
        é só um sinal de que o nó está vivo e a escanear. "RSSI mediano" é o que realmente diferencia um nó
        mal posicionado ou degradado de um saudável, mesmo quando ambos escaneiam à mesma taxa
        {rateWindowSec != null && ` (janela de ${Math.round(rateWindowSec / 60)} min)`}.
      </p>

      {nodes.length > 0 ? (
        <table className="table table-striped mb-4">
          <thead>
            <tr>
              <th>ESP ID</th>
              <th>Sala</th>
              <th>Estado</th>
              <th>Última comunicação</th>
              <th>Deteções/min</th>
              <th>RSSI mediano (dBm)</th>
              <th>Lotes perdidos</th>
              <th>Lotes duplicados</th>
              <th>Reordenados</th>
            </tr>
          </thead>
          <tbody>
            {nodes.map((n) => (
              <tr key={n.esp_id}>
                <td>{n.esp_id}</td>
                <td>{n.room || <span className="text-muted fst-italic">não mapeado</span>}</td>
                <td><OnlineBadge secondsSinceLastSeen={n.seconds_since_last_seen} thresholdSec={offlineThreshold} /></td>
                <td>{n.last_seen || "-"} {n.last_seen && `(há ${formatSeconds(n.seconds_since_last_seen)})`}</td>
                <td>{n.detections_per_min}</td>
                <td>{n.median_rssi_dbm != null ? n.median_rssi_dbm : "-"}</td>
                <td>{n.gap_count}</td>
                <td>{n.duplicate_count}</td>
                <td>{n.reorder_count}</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <p className="text-muted fst-italic">Nenhum nó configurado ou visto ainda</p>
      )}

      <h3>Estado da integração Mirth</h3>
      {mirth ? (
        <ul className="list-unstyled">
          <li>Última confirmação: {mirth.last_success || "-"}</li>
          <li>Última falha: {mirth.last_failure || "-"}</li>
          <li>Falhas nesta sessão: {mirth.failure_count_session}</li>
        </ul>
      ) : (
        <p className="text-muted fst-italic">Sem dados</p>
      )}
    </div>
  );
}
