// ==============================================================
// App entry - routing setup
// ==============================================================
// React and routing imports
import React from "react";
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";

// Top-level application components
import DashboardLayout from "./components/DashboardLayout";
import LoginSignupForm from "./components/LoginSignupForm";
import GroundTruthMarker from "./components/GroundTruthMarker";
import RequireAuth from "./components/RequireAuth";

// Main application component
// - Sets up client-side routes used by the frontend
function App() {
  return (
    <Router>
      {/* Route for login page (uses same form component for login/signup) */}
      <Routes>
        <Route path="/login" element={<LoginSignupForm />} />
        <Route path="/signup" element={<LoginSignupForm />} />

        {/* Mobile-friendly ground-truth marking page - kept outside
            DashboardLayout on purpose, since that layout assumes a fixed
            desktop sidebar with no responsive behavior */}
        <Route path="/ground-truth" element={<RequireAuth><GroundTruthMarker /></RequireAuth>} />

        {/* All other routes handled by the dashboard layout (protected UI) */}
        <Route path="/*" element={<DashboardLayout />} />
      </Routes>
    </Router>
  );
}

// Export the root App component
export default App;
