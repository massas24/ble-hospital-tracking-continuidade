// BeaconManagement component
// Responsible for displaying active/inactive beacons and sending active beacons to Mirth

import { useState, useEffect } from 'react'; // React hooks used in the component

export default function BeaconManagement() {
  // State that holds active beacons (latest sightings)
  const [activeBeacons, setActiveBeacons] = useState([]);
  // State that holds whitelisted but currently inactive beacons
  const [inactiveBeacons, setInactiveBeacons] = useState([]);
  // Loading flag used while sending beacons
  const [loading, setLoading] = useState(false);
  // Message shown in the UI for success/error/warning
  const [message, setMessage] = useState('');
  // Message type to control alert styling ('success', 'danger', 'warning')
  const [messageType, setMessageType] = useState(''); // 'success' or 'danger'
  // Tracks which beacon@room combinations have been sent already: { "mac_room": true }
  const [sentBeacons, setSentBeacons] = useState({});

  // Load beacons when the component mounts and poll every 5s for updates
  useEffect(() => {
    loadBeacons(); // initial load
    const interval = setInterval(loadBeacons, 5000); // periodic refresh
    return () => clearInterval(interval); // cleanup on unmount
  }, []);

  // Fetches active/inactive beacons from the backend
  const loadBeacons = async () => {
    try {
      const username = localStorage.getItem('username'); // header-based auth uses username
      const res = await fetch('http://127.0.0.1:5000/api/all-beacons', {
        headers: { 'X-User': username }
      });
      const data = await res.json();
      // Update state with fetched lists (use empty arrays as fallback)
      setActiveBeacons(data.active || []);
      setInactiveBeacons(data.inactive || []);
      
      // Clean up sentBeacons: remove keys for beacons that no longer exist in active list
      setSentBeacons(prevSentBeacons => {
        // Build set of valid keys from the returned active beacons
        const validKeys = new Set((data.active || []).map(b => `${b.mac}_${b.room}`));
        const newSent = {};
        Object.keys(prevSentBeacons).forEach(key => {
          if (validKeys.has(key)) newSent[key] = true; // only keep still-active keys
        });
        return newSent;
      });

    } catch (err) {
      // Handle fetch errors and notify user
      console.error('Error loading beacons:', err);
      setMessage('Error loading beacons');
      setMessageType('danger');
    }
  };

  // Sends active beacons to Mirth, but avoids re-sending beacons that are already sent
  const sendActiveBeaconsToMirth = async () => {
    setLoading(true); // show loading UI
    try {
      const username = localStorage.getItem('username');
      
      // Determine which active beacons are newly eligible to send
      const newlySentBeacons = {};
      let countToSend = 0;
      let countAlreadySent = 0;
      
      activeBeacons.forEach(beacon => {
        const beaconKey = `${beacon.mac}_${beacon.room}`; // unique per mac+room
        if (sentBeacons[beaconKey]) {
          // Already sent for this exact location
          countAlreadySent++;
        } else {
          // Mark as to-be-sent in this request
          newlySentBeacons[beaconKey] = true;
          countToSend++;
        }
      });
      
      // If nothing to send, show a warning and exit early
      if (countToSend === 0) {
        setMessage(`All ${countAlreadySent} active beacons already sent at current locations`);
        setMessageType('warning');
        setLoading(false);
        setTimeout(() => setMessage(''), 4000);
        return;
      }
      
      // Call backend endpoint that performs the batch send
      const res = await fetch('http://127.0.0.1:5000/api/send-active-beacons-to-mirth', {
        method: 'POST',
        headers: { 'X-User': username }
      });
      const data = await res.json();
      
      // Update local state and show success/error message depending on response
      if (data.status === 'success') {
        // Merge new sent keys with existing ones to prevent re-sends
        setSentBeacons(prev => ({ ...prev, ...newlySentBeacons }));
        setMessage('✓ Successfully sent active beacons to Mirth');
        setMessageType('success');
      } else {
        setMessage('✗ Error sending beacons to Mirth');
        setMessageType('danger');
      }
      
      setTimeout(() => setMessage(''), 4000); // auto-clear message after a short delay
    } catch (err) {
      // Network or unexpected errors
      setMessage('✗ Error sending beacons to Mirth');
      setMessageType('danger');
      console.error(err);
      setTimeout(() => setMessage(''), 4000);
    } finally {
      setLoading(false);
    }
  };

  // Render UI
  return (
    <div className="card p-4" style={{ maxWidth: "900px", margin: "auto" }}>
      <h2>Beacon Management</h2>
      <div className="mb-3">
        {/* Button to trigger manual send, disabled when loading or no active beacons */}
        <button
          onClick={sendActiveBeaconsToMirth}
          disabled={loading || activeBeacons.length === 0}
          className="btn btn-primary"
        >
          {loading ? 'Sending...' : 'Send to Mirth'}
        </button>
      </div>
      
      {/* Show message alert when present */}
      {message && (
        <div className={`alert alert-${messageType} mb-3`} role="alert">
          {message}
        </div>
      )}

      {/* Active beacons table */}
      <h3>Active Beacons ({activeBeacons.length})</h3>
      {activeBeacons.length > 0 ? (
        <table className="table table-striped mb-4">
          <thead>
            <tr>
              <th>MAC Address</th>
              <th>Room</th>
              <th>RSSI</th>
              <th>Last Seen</th>
              <th>Location Status</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {activeBeacons.map((b) => {
              const beaconKey = `${b.mac}_${b.room}`;
              const isSent = sentBeacons[beaconKey]; // whether this MAC+room was sent
              return (
                <tr key={b.mac} style={{ backgroundColor: isSent ? '#f0f0f0' : 'transparent' }}>
                  <td>{b.mac}</td>
                  <td>{b.room}</td>
                  <td>{b.rssi}</td>
                  <td>{b.time}</td>
                  <td>{b.location_status || '-'}</td>
                  <td>{isSent ? '✓ Sent' : 'Pending'}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      ) : (
        <p className="text-muted fst-italic">No active beacons</p>
      )}

      {/* Inactive (whitelisted) beacons table */}
      <h3>Inactive Beacons ({inactiveBeacons.length})</h3>
      {inactiveBeacons.length > 0 ? (
        <table className="table table-striped">
          <thead>
            <tr>
              <th>MAC Address</th>
              <th>Whitelisted On</th>
            </tr>
          </thead>
          <tbody>
            {inactiveBeacons.map((b) => (
              <tr key={b.mac}>
                <td>{b.mac}</td>
                <td>{b.added_at}</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <p className="text-muted fst-italic">No inactive beacons</p>
      )}
    </div>
  );
}
