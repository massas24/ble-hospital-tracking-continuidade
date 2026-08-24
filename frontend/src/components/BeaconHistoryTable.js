import React, { useState, useEffect } from "react";
import axios from "axios";

export default function BeaconHistoryTable({ mac, token }) {
  const [history, setHistory] = useState([]);

  useEffect(() => {
    if (!mac) return;

    axios.get(`/api/beacon-history/${mac}`, {
      headers: { "X-User": token }
    })
    .then(res => setHistory(res.data))
    .catch(() => setHistory([]));
  }, [mac, token]);

  return (
    <div style={{ marginTop: 24 }}>
      <h3>History for beacon: {mac}</h3>
      <div className="table-responsive">
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ background: "#eef1f7" }}>
              <th style={{ textAlign: "left", padding: 10 }}>ESP ID</th>
              <th style={{ textAlign: "left", padding: 10 }}>ESP Name</th>
              <th style={{ textAlign: "left", padding: 10 }}>Room</th>
              <th style={{ textAlign: "left", padding: 10 }}>MAC</th>
              <th style={{ textAlign: "left", padding: 10 }}>RSSI</th>
              <th style={{ textAlign: "left", padding: 10 }}>Time</th>
            </tr>
          </thead>
          <tbody>
            {history.length === 0 ? (
              <tr>
                <td colSpan="6" style={{ padding: 12, textAlign: "center" }}>No history available</td>
              </tr>
            ) : (
              history.map((item, idx) => (
                <tr key={idx} style={{ borderBottom: "1px solid #ddd" }}>
                  <td style={{ padding: 8 }}>{item.esp_id}</td>
                  <td style={{ padding: 8 }}>{item.esp_name}</td>
                  <td style={{ padding: 8 }}>{item.room}</td>
                  <td style={{ padding: 8 }}>{item.mac}</td>
                  <td style={{ padding: 8 }}>{item.rssi}</td>
                  <td style={{ padding: 8 }}>{item.time}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
