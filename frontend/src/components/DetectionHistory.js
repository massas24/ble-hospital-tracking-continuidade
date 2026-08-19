// DetectionHistory - searchable detection history with filters by room,
// beacon, and time interval, plus CSV export (guião secção 3.11:
// "histórico pesquisável", "filtros por sala, beacon e intervalo
// temporal", "exportação de dados"). Scoped for ad-hoc filtered look-ups,
// not a bulk-export replacement for analyze_room_decisions.py.
import { useState, useEffect } from "react";
import axios from "axios";

// bledata() writes room="unknown" for any esp_id with no esp_mapping entry
// (backend/app.py) - that literal never shows up in esp_mapping's distinct
// rooms, so it's added here as a fixed extra option.
const UNKNOWN_ROOM = "unknown";

// datetime-local gives "YYYY-MM-DDTHH:mm" - the backend stores/compares
// "YYYY-MM-DD HH:MM:SS" strings. ":59" on the end bound (not ":00") so
// picking e.g. 15:30 as an end time doesn't exclude 15:30:01-15:30:59.
function toBackendTime(datetimeLocalValue, isEnd) {
  if (!datetimeLocalValue) return "";
  return datetimeLocalValue.replace("T", " ") + (isEnd ? ":59" : ":00");
}

export default function DetectionHistory() {
  const username = localStorage.getItem("username");
  const headers = { "X-User": username };

  const [rooms, setRooms] = useState([]);
  const [macs, setMacs] = useState([]);
  const [room, setRoom] = useState("");
  const [mac, setMac] = useState("");
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [results, setResults] = useState([]);
  const [truncated, setTruncated] = useState(false);
  const [exportTruncated, setExportTruncated] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
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

  const buildParams = () => {
    const params = {};
    if (room) params.room = room;
    if (mac) params.mac = mac;
    if (start) params.start = toBackendTime(start, false);
    if (end) params.end = toBackendTime(end, true);
    return params;
  };

  const search = () => {
    setLoading(true);
    setError("");
    setExportTruncated(false);
    axios.get("/api/detection-history", { headers, params: buildParams() })
      .then(res => {
        setResults(res.data.results || []);
        setTruncated(!!res.data.truncated);
      })
      .catch(err => {
        setError(err.response?.data?.error || "Falha ao pesquisar o histórico");
        setResults([]);
        setTruncated(false);
      })
      .finally(() => setLoading(false));
  };

  const exportCsv = () => {
    setError("");
    setExportTruncated(false);
    axios.get("/api/detection-history/export", {
      headers, params: buildParams(), responseType: "blob",
    })
      .then(res => {
        // Read the truncation signal BEFORE triggering the download, so the
        // warning shows even though the user's attention moves to the
        // browser's download UI right after (the filename itself also
        // carries a "_truncated" suffix as a second, more durable signal -
        // see backend/app.py).
        if (res.headers["x-export-truncated"] === "true") {
          setExportTruncated(true);
        }
        const disposition = res.headers["content-disposition"] || "";
        const match = disposition.match(/filename=([^;]+)/);
        const filename = match ? match[1].trim() : "deteccoes.csv";
        const url = URL.createObjectURL(new Blob([res.data], { type: "text/csv" }));
        const link = document.createElement("a");
        link.href = url;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        link.remove();
        URL.revokeObjectURL(url);
      })
      .catch(() => setError("Falha ao exportar CSV"));
  };

  return (
    <div className="card p-4 page-card-wide">
      <h2>Histórico de Deteções</h2>

      {error && <div className="alert alert-danger mb-3">{error}</div>}
      {exportTruncated && (
        <div className="alert alert-warning mb-3">
          Exportação truncada a 5000 linhas - refina os filtros para um ficheiro completo.
        </div>
      )}

      <div className="row g-2 mb-3">
        <div className="col-auto">
          <label className="form-label mb-0">Sala</label>
          <select className="form-select" value={room} onChange={e => setRoom(e.target.value)}>
            <option value="">Todas</option>
            {rooms.map(r => <option key={r} value={r}>{r}</option>)}
            {!rooms.includes(UNKNOWN_ROOM) && <option value={UNKNOWN_ROOM}>unknown</option>}
          </select>
        </div>
        <div className="col-auto">
          <label className="form-label mb-0">Beacon (MAC)</label>
          <select className="form-select" value={mac} onChange={e => setMac(e.target.value)}>
            <option value="">Todos</option>
            {macs.map(m => <option key={m} value={m}>{m}</option>)}
          </select>
        </div>
        <div className="col-auto">
          <label className="form-label mb-0">Início</label>
          <input type="datetime-local" className="form-control" value={start} onChange={e => setStart(e.target.value)} />
        </div>
        <div className="col-auto">
          <label className="form-label mb-0">Fim</label>
          <input type="datetime-local" className="form-control" value={end} onChange={e => setEnd(e.target.value)} />
        </div>
        <div className="col-auto d-flex align-items-end gap-2">
          <button className="btn btn-primary" onClick={search} disabled={loading}>
            {loading ? "A pesquisar..." : "Pesquisar"}
          </button>
          <button className="btn btn-outline-secondary" onClick={exportCsv}>
            Exportar CSV
          </button>
        </div>
      </div>

      {truncated && (
        <div className="alert alert-warning mb-3">
          A mostrar as 500 mais recentes - refina os filtros para veres tudo.
        </div>
      )}

      {results.length > 0 ? (
        <table className="table table-striped">
          <thead>
            <tr>
              <th>Hora</th>
              <th>MAC</th>
              <th>Sala</th>
              <th>ESP ID</th>
              <th>RSSI</th>
            </tr>
          </thead>
          <tbody>
            {results.map((r, idx) => (
              <tr key={idx}>
                <td>{r.time}</td>
                <td>{r.mac}</td>
                <td>{r.room}</td>
                <td>{r.esp_id}</td>
                <td>{r.rssi}</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <p className="text-muted fst-italic">Sem resultados - ajusta os filtros e pesquisa.</p>
      )}
    </div>
  );
}
