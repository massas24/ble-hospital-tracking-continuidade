import { useState, useEffect } from "react";
import axios from "axios";
import BeaconHistoryTable from "./BeaconHistoryTable";

function WhitelistAdmin() {
  const [items, setItems] = useState([]);
  const [mac, setMac] = useState("");
  const [error, setError] = useState("");
  const [selectedMac, setSelectedMac] = useState(null);
  const username = localStorage.getItem("username");

  useEffect(() => {
    fetchList();
  }, []);

  const fetchList = () => {
    axios.get("/api/whitelist", { headers: { "X-User": username } })
      .then(res => setItems(res.data))
      .catch(() => setItems([]));
  };

  const addMac = async () => {
    setError("");
    if (!mac.trim()) return;
    try {
      await axios.post("/api/whitelist", { mac: mac.trim() }, { headers: { "X-User": username } });
      setItems([...items, { mac: mac.trim() }]);
      setMac("");
    } catch (err) {
      setError(err.response?.data?.error || "Unable to add MAC");
    }
  };

  const deleteMac = async (macToDelete) => {
    await axios.delete(`/api/whitelist/${macToDelete}`, { headers: { "X-User": username } });
    setItems(items.filter(item => item.mac !== macToDelete));
    if (selectedMac === macToDelete) setSelectedMac(null);
  };

  return (
    <div className="card p-4 page-card">
      <h2>Beacon Whitelist</h2>
      <div style={{ display: "flex", gap: 12, marginBottom: 18 }}>
        <input
          placeholder="MAC address"
          value={mac}
          onChange={e => setMac(e.target.value)}
          className="form-input"
          style={{ flexGrow: 1 }}
        />
        <button onClick={addMac} className="btn btn-primary">Add MAC</button>
      </div>
      {error && <div className="text-danger mb-3">{error}</div>}
      <table className="table table-striped">
        <thead>
          <tr>
            <th>MAC Address</th>
            <th>Action</th>
            <th>History</th>
          </tr>
        </thead>
        <tbody>
          {items.length === 0 ? (
            <tr>
              <td colSpan="3" className="text-center">No MACs in whitelist</td>
            </tr>
          ) : (
            items.map(item => (
              <tr key={item.mac}>
                <td>{item.mac}</td>
                <td>
                  <button onClick={() => deleteMac(item.mac)} className="btn btn-danger btn-sm">
                    Delete
                  </button>
                </td>
                <td>
                  <button onClick={() => setSelectedMac(item.mac)} className="btn btn-info btn-sm">
                    View History
                  </button>
                </td>
              </tr>
            ))
          )}
        </tbody>
      </table>

      {/* Render BeaconHistoryTable when a MAC is selected */}
      {selectedMac && <BeaconHistoryTable mac={selectedMac} token={username} />}
    </div>
  );
}

export default WhitelistAdmin;
