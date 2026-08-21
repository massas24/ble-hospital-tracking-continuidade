import { Link, useNavigate } from "react-router-dom";
import { FaBars } from "react-icons/fa";


export default function Navbar({ onToggleSidebar }) {
  const navigate = useNavigate();

  const handleLogout = () => {
    localStorage.removeItem("username");
    navigate("/login");
  };

  return (
    <nav className="app-navbar">
      <button
        type="button"
        className="navbar-toggle"
        onClick={onToggleSidebar}
        aria-label="Abrir menu"
      >
        <FaBars size={20} />
      </button>

      <Link className="navbar-brand" to="/devices">Hospital BLE Tracking Dashboard</Link>

      <div className="app-navbar-actions">
        <button className="btn btn-warning" onClick={handleLogout}>Logout</button>
      </div>
    </nav>
  );
}
