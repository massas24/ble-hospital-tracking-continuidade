// Import React hooks and axios for API calls
import { useState, useEffect } from "react";
import axios from "axios";

// Devices component shows live BLE device data
function Devices() {
  const [devices, setDevices] = useState([]); // Store device list
  const username = localStorage.getItem("username"); // Get username from local storage

  // Fetch devices from backend every second
  useEffect(() => {
    const interval = setInterval(() => {
      axios.get("/api/data", { headers: { "X-User": username } })
        .then(res => setDevices(res.data))
        .catch(console.error);
    }, 1000);
    return () => clearInterval(interval);
  }, [username]);

  // Render device table
  return (
    <div className="card p-4 page-card-wide">
      <h2>Live BLE Devices</h2>
      <table className="table table-striped">
        <thead>
          <tr>
            <th>ESP ID</th><th>ESP Name</th><th>Room</th><th>MAC</th><th>RSSI</th><th>Time</th>
          </tr>
        </thead>
        <tbody>
          {devices.length ? devices.map((d, i) => (
            <tr key={i}>
              <td>{d.esp_id}</td>
              <td>{d.esp_name}</td>
              <td>{d.room}</td>
              <td>{d.mac}</td>
              <td>{d.rssi}</td>
              <td>{d.time}</td>
            </tr>
          )) : <tr><td colSpan="6" className="text-center">No devices</td></tr>}
        </tbody>
      </table>
    </div>
  );
}

export default Devices;
