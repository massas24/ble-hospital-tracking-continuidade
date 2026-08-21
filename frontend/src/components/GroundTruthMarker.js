
import { useState, useEffect } from "react";
import axios from "axios";

const SCENARIOS = [
  { value: "centro_sala", label: "Centro da sala" },
  { value: "junto_parede", label: "Junto à parede" },
  { value: "junto_porta", label: "Junto à porta" },
  { value: "movimento", label: "Movimento entre salas" },
];
const SCENARIO_LABELS = Object.fromEntries(SCENARIOS.map(s => [s.value, s.label]));

const STALE_EXPERIMENT_THRESHOLD_MIN = 120;

function suggestExperimentName() {
  const d = new Date();
  const pad = n => String(n).padStart(2, "0");
  return `ensaio_${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}_${pad(d.getHours())}-${pad(d.getMinutes())}`;
}

function formatElapsed(elapsedMin) {
  if (elapsedMin == null) return null;
  const rounded = Math.round(elapsedMin);
  return rounded < 60 ? `${rounded} min` : `${Math.floor(rounded / 60)}h${String(rounded % 60).padStart(2, "0")}`;
}

function GroundTruthMarker() {
  const username = localStorage.getItem("username");
  const headers = { "X-User": username };

  const [experimentId, setExperimentId] = useState(null);
  const [experimentStartedAt, setExperimentStartedAt] = useState(null);
  const [experimentElapsedMin, setExperimentElapsedMin] = useState(null);
  const [macs, setMacs] = useState([]);
  const [rooms, setRooms] = useState([]);
  const [selectedMac, setSelectedMac] = useState(localStorage.getItem("groundTruthMac") || "");
  const [scenario, setScenario] = useState(localStorage.getItem("groundTruthScenario") || "centro_sala");
  const [recentTaps, setRecentTaps] = useState([]);
  const [error, setError] = useState("");
  const [manualTime, setManualTime] = useState(false);
  const [manualTimeValue, setManualTimeValue] = useState("");

  const [showStartForm, setShowStartForm] = useState(false);
  const [newExperimentName, setNewExperimentName] = useState("");
  const [pendingOverwriteName, setPendingOverwriteName] = useState(null);
  const [recentExperiments, setRecentExperiments] = useState([]);
  const [endedSummary, setEndedSummary] = useState(null);

  const refreshExperimentStatus = () => {
    axios.get("/api/experiment", { headers })
      .then(res => {
        setExperimentId(res.data.experiment_id);
        setExperimentStartedAt(res.data.experiment_started_at);
        setExperimentElapsedMin(res.data.experiment_elapsed_min);
      })
      .catch(() => {
        setExperimentId(null);
        setExperimentStartedAt(null);
        setExperimentElapsedMin(null);
      });
  };

  const fetchRecentExperiments = () => {
    axios.get("/api/experiments", { headers })
      .then(res => {
        const sorted = [...res.data].sort((a, b) => (b.created_at || "").localeCompare(a.created_at || ""));
        setRecentExperiments(sorted.slice(0, 8));
      })
      .catch(() => setRecentExperiments([]));
  };

  useEffect(() => {
    refreshExperimentStatus();
    fetchRecentExperiments();

    axios.get("/api/whitelist", { headers })
      .then(res => setMacs(res.data.map(w => w.mac)))
      .catch(() => setMacs([]));

    axios.get("/api/esp-mapping", { headers })
      .then(res => {
        const distinctRooms = [...new Set(res.data.map(m => m.room))].sort();
        setRooms(distinctRooms);
      })
      .catch(() => setRooms([]));

    
    const interval = setInterval(refreshExperimentStatus, 60000);
    return () => clearInterval(interval);
  }, []);

  const chooseMac = (mac) => {
    setSelectedMac(mac);
    localStorage.setItem("groundTruthMac", mac);
  };

  const chooseScenario = (value) => {
    setScenario(value);
    localStorage.setItem("groundTruthScenario", value);
  };

  const openStartForm = () => {
    setError("");
    setNewExperimentName(suggestExperimentName());
    setPendingOverwriteName(null);
    setShowStartForm(true);
  };

  const startExperiment = async (name) => {
    setError("");
    try {
      const res = await axios.post("/api/experiment", { experiment_id: name }, { headers });
      setExperimentId(res.data.experiment_id);
      setExperimentStartedAt(res.data.experiment_started_at || null);
      setExperimentElapsedMin(res.data.experiment_elapsed_min);
      setShowStartForm(false);
      setNewExperimentName("");
      
      setEndedSummary(res.data.ended_summary || null);
      fetchRecentExperiments();
    } catch (err) {
      setError(err.response?.data?.error || "Falha ao iniciar o ensaio");
    }
  };

  const submitStartForm = () => {
    const name = newExperimentName.trim();
    if (!name) {
      setError("Indica um nome para o ensaio");
      return;
    }
    if (experimentId) {
      setPendingOverwriteName(name);
      return;
    }
    startExperiment(name);
  };

  const confirmOverwrite = () => {
    startExperiment(pendingOverwriteName);
    setPendingOverwriteName(null);
  };
  const cancelOverwrite = () => setPendingOverwriteName(null);

  const stopExperiment = async () => {
    setError("");
    try {
      const res = await axios.post("/api/experiment", { experiment_id: null }, { headers });
      setExperimentId(res.data.experiment_id);
      setExperimentStartedAt(res.data.experiment_started_at || null);
      setExperimentElapsedMin(res.data.experiment_elapsed_min);
      setEndedSummary(res.data.ended_summary || null);
      fetchRecentExperiments();
    } catch (err) {
      setError(err.response?.data?.error || "Falha ao terminar o ensaio");
    }
  };

  const tapRoom = async (room) => {
    setError("");
    if (!selectedMac) {
      setError("Escolhe primeiro o MAC do beacon");
      return;
    }
    const body = { mac: selectedMac, room, scenario };
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

  const isStale = experimentElapsedMin != null && experimentElapsedMin >= STALE_EXPERIMENT_THRESHOLD_MIN;

  return (
    <div style={{ maxWidth: 480, margin: "auto", padding: 16 }}>
      <h3 className="mb-3">Ground Truth</h3>

      {/* Indicador persistente do ensaio ativo - substitui o antigo alerta
          vermelho/azul binário. Nunca bloqueia as marcações. */}
      <div className={`alert ${experimentId ? (isStale ? "alert-warning" : "alert-success") : "alert-secondary"} py-2`}>
        {experimentId ? (
          <div className="d-flex justify-content-between align-items-center flex-wrap gap-2">
            <span>
              <strong>{experimentId}</strong> — ativo há {formatElapsed(experimentElapsedMin) || "instantes"}
              {isStale && <span> — ainda precisas disto ativo?</span>}
            </span>
            <div className="d-flex gap-2">
              <button className="btn btn-sm btn-outline-primary" onClick={openStartForm}>Iniciar ensaio</button>
              <button className="btn btn-sm btn-outline-danger" onClick={stopExperiment}>Terminar ensaio</button>
            </div>
          </div>
        ) : (
          <div className="d-flex justify-content-between align-items-center flex-wrap gap-2">
            <span>Sem ensaio ativo — as marcações vão ficar sem ensaio associado.</span>
            <button className="btn btn-sm btn-primary" onClick={openStartForm}>Iniciar ensaio</button>
          </div>
        )}
      </div>

      {/* Formulário inline de início (nunca window.prompt()) */}
      {showStartForm && (
        <div className="card p-3 mb-3">
          {pendingOverwriteName ? (
            <div className="alert alert-warning py-2 mb-0">
              <strong>{experimentId}</strong> a decorrer há {formatElapsed(experimentElapsedMin) || "instantes"} — substituir por <strong>{pendingOverwriteName}</strong>?
              <div className="d-flex gap-2 mt-2">
                <button className="btn btn-sm btn-danger" onClick={confirmOverwrite}>Sim, substituir</button>
                <button className="btn btn-sm btn-secondary" onClick={cancelOverwrite}>Cancelar</button>
              </div>
            </div>
          ) : (
            <>
              <label className="form-label">Nome do ensaio</label>
              <input type="text" className="form-control mb-2"
                value={newExperimentName} onChange={e => setNewExperimentName(e.target.value)} />
              <div className="d-flex gap-2 mb-2">
                <button className="btn btn-sm btn-primary" onClick={submitStartForm}>Confirmar</button>
                <button className="btn btn-sm btn-secondary" onClick={() => setShowStartForm(false)}>Cancelar</button>
              </div>
              {recentExperiments.length > 0 && (
                <div>
                  <small className="text-muted">Ensaios recentes:</small>
                  <ul className="list-unstyled mb-0" style={{ fontSize: "0.85em" }}>
                    {recentExperiments.map(exp => (
                      <li key={exp.experiment_id} className="text-muted">{exp.experiment_id}</li>
                    ))}
                  </ul>
                </div>
              )}
            </>
          )}
        </div>
      )}

      {/* Resumo automático - aparece depois de "Terminar" e também depois
          de um "Iniciar" que substituiu um ensaio ativo */}
      {endedSummary && (
        <div className="card p-3 mb-3">
          <div className="d-flex justify-content-between align-items-center mb-2">
            <h6 className="mb-0">Resumo: {endedSummary.experiment_id}</h6>
            <button className="btn btn-sm btn-outline-secondary" onClick={() => setEndedSummary(null)}>Fechar</button>
          </div>
          {endedSummary.macs.length === 0 ? (
            <p className="text-muted mb-0">Sem dados registados neste ensaio.</p>
          ) : (
            <table className="table table-sm mb-0">
              <thead><tr><th>MAC</th><th>Deteções</th><th>Eventos GT</th><th>Transições</th><th>Duração</th></tr></thead>
              <tbody>
                {endedSummary.macs.map(m => (
                  <tr key={m.mac}>
                    <td>{m.mac}</td>
                    <td>{m.num_raw_detections}</td>
                    <td>{m.num_ground_truth_events}</td>
                    <td>{m.num_transitions}</td>
                    <td>{m.duration_sec != null ? `${Math.round(m.duration_sec)}s` : "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
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

      {/* Cenário (guião secção 9) - default "Centro da sala", lembrado por
          dispositivo. "Vários beacons" (5º cenário do guião) fica de fora
          de propósito - é uma condição do ensaio inteiro, não por toque. */}
      <div className="mb-3">
        <label className="form-label d-block">Cenário</label>
        <div className="d-flex flex-wrap gap-2">
          {SCENARIOS.map(s => (
            <button key={s.value} type="button"
              className={`btn btn-sm ${scenario === s.value ? "btn-secondary" : "btn-outline-secondary"}`}
              onClick={() => chooseScenario(s.value)} style={{ flex: "1 1 45%" }}>
              {s.label}
            </button>
          ))}
        </div>
        <small className="text-muted d-block mt-1">
          Aplica-se a todas as leituras até à próxima marcação — se mudares de cenário sem mudar de sala, toca na sala outra vez para o registar.
        </small>
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
            <span>{tap.time} — {tap.room}{tap.scenario ? ` (${SCENARIO_LABELS[tap.scenario] || tap.scenario})` : ""}</span>
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
