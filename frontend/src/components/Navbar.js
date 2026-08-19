import { Link, useNavigate } from "react-router-dom";
import { FaBars } from "react-icons/fa";

// onToggleSidebar is only wired to a visible control on mobile (the
// hamburger button below, shown via index.css's max-width:768px block) -
// harmless to always accept the prop.
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
        {/* btn-warning (not a bare .btn) - a plain .btn used to get forced
            to primary blue by a since-removed !important rule in
            index.css, which also silently overrode every .btn-danger/
            .btn-info button elsewhere in the app to the same blue. */}
        <button className="btn btn-warning" onClick={handleLogout}>Logout</button>
      </div>
    </nav>
  );
}
