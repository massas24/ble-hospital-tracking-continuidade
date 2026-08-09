import { Link, useLocation } from "react-router-dom";
import { FaTachometerAlt, FaListAlt, FaShieldAlt, FaSignal, FaMapMarkerAlt, FaHeartbeat, FaHistory } from "react-icons/fa";

const sidebarStyle = {
  width: "230px",
  minHeight: "100vh",
  background: "#232e3c",
  color: "#fff",
  position: "fixed",
  left: 0,
  top: 0,
  paddingTop: "32px",
  boxShadow: "2px 0 16px #0002",
  zIndex: 100,
};

const activeStyle = {
  background: "#1a2230",
  color: "#4e73df",
  fontWeight: "bold",
  borderLeft: "4px solid #4e73df",
  borderRadius: "6px 0 0 6px",
};

const linkStyle = {
  display: "flex",
  gap: "12px",
  alignItems: "center",
  color: "#fff",
  padding: "14px 28px",
  textDecoration: "none",
  marginBottom: "6px",
  borderLeft: "4px solid transparent",
  fontWeight: 500,
  fontSize: "1.08rem",
  borderRadius: "6px 0 0 6px",
  transition: "background 0.2s, color 0.2s",
};

export default function Sidebar() {
  const location = useLocation();

  return (
    <aside style={sidebarStyle}>
      <div
        style={{
          fontWeight: 700,
          fontSize: "1.15rem",
          padding: "0 28px 18px",
          letterSpacing: ".5px",
          color: "#fff",
          opacity: 0.85,
          borderBottom: "1px solid #2c3542",
          marginBottom: "18px",
        }}
      >
        MENU
      </div>
      <nav>
        <div
          style={{
            fontSize: "0.95rem",
            fontWeight: 600,
            color: "#bfc8d6",
            padding: "0 28px 6px",
            letterSpacing: ".2px",
          }}
        >
          Dashboard
        </div>

        <Link
          to="/devices"
          style={{
            ...linkStyle,
            ...(location.pathname === "/devices" ? activeStyle : {}),
          }}
        >
          <FaTachometerAlt size={20} />
          Live Devices
        </Link>

        <div
          style={{
            fontSize: "0.95rem",
            fontWeight: 600,
            color: "#bfc8d6",
            padding: "12px 28px 6px",
            letterSpacing: ".2px",
          }}
        >
          Components
        </div>

        <Link
          to="/admin"
          style={{
            ...linkStyle,
            ...(location.pathname === "/admin" ? activeStyle : {}),
          }}
        >
          <FaListAlt size={20} />
          ESP Mapping
        </Link>

        <Link
          to="/whitelist"
          style={{
            ...linkStyle,
            ...(location.pathname === "/whitelist" ? activeStyle : {}),
          }}
        >
          <FaShieldAlt size={20} />
          Whitelist
        </Link>

        <Link
          to="/beacons"
          style={{
            ...linkStyle,
            ...(location.pathname === "/beacons" ? activeStyle : {}),
          }}
        >
          <FaSignal size={20} />
          Mirth
        </Link>

        <Link
          to="/node-status"
          style={{
            ...linkStyle,
            ...(location.pathname === "/node-status" ? activeStyle : {}),
          }}
        >
          <FaHeartbeat size={20} />
          Estado dos Nós
        </Link>

        <Link
          to="/history"
          style={{
            ...linkStyle,
            ...(location.pathname === "/history" ? activeStyle : {}),
          }}
        >
          <FaHistory size={20} />
          Histórico
        </Link>

        <Link
          to="/ground-truth"
          style={{
            ...linkStyle,
            ...(location.pathname === "/ground-truth" ? activeStyle : {}),
          }}
        >
          <FaMapMarkerAlt size={20} />
          Ground Truth
        </Link>
      </nav>
    </aside>
  );
}
