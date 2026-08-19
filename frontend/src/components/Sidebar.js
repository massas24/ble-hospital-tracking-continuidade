import { Link, useLocation } from "react-router-dom";
import { FaTachometerAlt, FaListAlt, FaShieldAlt, FaSignal, FaMapMarkerAlt, FaHeartbeat, FaHistory } from "react-icons/fa";

const NAV_SECTIONS = [
  {
    label: "Dashboard",
    links: [
      { to: "/devices", icon: FaTachometerAlt, text: "Live Devices" },
    ],
  },
  {
    label: "Components",
    links: [
      { to: "/admin", icon: FaListAlt, text: "ESP Mapping" },
      { to: "/whitelist", icon: FaShieldAlt, text: "Whitelist" },
      { to: "/beacons", icon: FaSignal, text: "Mirth" },
      { to: "/node-status", icon: FaHeartbeat, text: "Estado dos Nós" },
      { to: "/history", icon: FaHistory, text: "Histórico" },
      { to: "/ground-truth", icon: FaMapMarkerAlt, text: "Ground Truth" },
    ],
  },
];

// `open`/`onNavigate` only matter on mobile (off-canvas drawer, see
// index.css's max-width:768px block) - on desktop the sidebar is always
// visible regardless of `open`, and onNavigate is harmless to call.
export default function Sidebar({ open, onNavigate }) {
  const location = useLocation();

  return (
    <aside className={`app-sidebar${open ? " open" : ""}`}>
      <div className="app-sidebar-brand">MENU</div>
      <nav>
        {NAV_SECTIONS.map(section => (
          <div key={section.label}>
            <div className="app-sidebar-section-label">{section.label}</div>
            {section.links.map(({ to, icon: Icon, text }) => (
              <Link
                key={to}
                to={to}
                onClick={onNavigate}
                className={`app-sidebar-link${location.pathname === to ? " active" : ""}`}
              >
                <Icon size={20} />
                {text}
              </Link>
            ))}
          </div>
        ))}
      </nav>
    </aside>
  );
}
