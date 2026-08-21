

import { useState, useEffect } from 'react'; // React hooks used in the component
import Badge from './Badge';

const STATUS_TONES = {
  confirmada: { tone: 'success', label: 'Confirmada' },
  'em transição': { tone: 'warning', label: 'Em transição' },
  desconhecida: { tone: 'secondary', label: 'Desconhecida' },
};

function StatusBadge({ status }) {
  const info = STATUS_TONES[status] || { tone: 'light', label: status || '-' };
  return <Badge tone={info.tone}>{info.label}</Badge>;
}

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
      
      console.error('Error loading beacons:', err);
      setMessage('Error loading beacons');
      setMessageType('danger');
    }
  };


  const sendActiveBeaconsToMirth = async () => {
    setLoading(true);
    try {
      const username = localStorage.getItem('username');
      
      
      const newlySentBeacons = {};
      let countToSend = 0;
      let countAlreadySent = 0;
      
      activeBeacons.forEach(beacon => {
        const beaconKey = `${beacon.mac}_${beacon.room}`;
        if (sentBeacons[beaconKey]) {
          
          countAlreadySent++;
        } else {
          
          newlySentBeacons[beaconKey] = true;
          countToSend++;
        }
      });
      
      
      if (countToSend === 0) {
        setMessage(`All ${countAlreadySent} active beacons already sent at current locations`);
        setMessageType('warning');
        setLoading(false);
        setTimeout(() => setMessage(''), 4000);
        return;
      }
      
      
      const res = await fetch('http://127.0.0.1:5000/api/send-active-beacons-to-mirth', {
        method: 'POST',
        headers: { 'X-User': username }
      });
      const data = await res.json();
      
      
      if (data.status === 'success') {
       
        setSentBeacons(prev => ({ ...prev, ...newlySentBeacons }));
        setMessage('✓ Successfully sent active beacons to Mirth');
        setMessageType('success');
      } else {
        setMessage('✗ Error sending beacons to Mirth');
        setMessageType('danger');
      }
      
      setTimeout(() => setMessage(''), 4000); 
    } catch (err) {
      
      setMessage('✗ Error sending beacons to Mirth');
      setMessageType('danger');
      console.error(err);
      setTimeout(() => setMessage(''), 4000);
    } finally {
      setLoading(false);
    }
  };

  
  return (
    <div className="card p-4 page-card">
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

      
      {(() => {
        const present = activeBeacons.filter(b => b.location_status !== 'desconhecida');
        const emTransicao = present.filter(b => b.location_status === 'em transição').length;
        return (
          <div className="mb-3 d-flex gap-4 flex-wrap">
            <span><strong>{present.length}</strong> beacons presentes agora</span>
            <span><strong>{emTransicao}</strong> em transição</span>
          </div>
        );
      })()}

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
              const isSent = sentBeacons[beaconKey];
              return (
                <tr key={b.mac} style={{ backgroundColor: isSent ? '#f0f0f0' : 'transparent' }}>
                  <td>{b.mac}</td>
                  <td>{b.room}</td>
                  <td>{b.rssi}</td>
                  <td>{b.time}</td>
                  <td><StatusBadge status={b.location_status} /></td>
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
