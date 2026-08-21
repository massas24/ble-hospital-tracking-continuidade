import React, { useState } from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import Sidebar from "./Sidebar";
import Navbar from "./Navbar";
import Devices from "./Devices";
import AdminPanel from "./AdminPanel";
import WhitelistAdmin from "./WhitelistAdmin";
import BeaconManagement from "./BeaconManagement";
import NodeStatus from "./NodeStatus";
import DetectionHistory from "./DetectionHistory";
import RequireAuth from "./RequireAuth";

function DashboardLayout() {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <>
      <Sidebar open={sidebarOpen} onNavigate={() => setSidebarOpen(false)} />
      {sidebarOpen && (
        <div className="app-sidebar-backdrop" onClick={() => setSidebarOpen(false)} />
      )}
      <div className="app-content">
        <Navbar onToggleSidebar={() => setSidebarOpen(o => !o)} />
        <div className="app-content-inner">
          <Routes>
            <Route
              path="/devices"
              element={
                <RequireAuth>
                  <Devices />
                </RequireAuth>
              }
            />
            <Route
              path="/admin"
              element={
                <RequireAuth>
                  <AdminPanel />
                </RequireAuth>
              }
            />
            <Route
              path="/whitelist"
              element={
                <RequireAuth>
                  <WhitelistAdmin />
                </RequireAuth>
              }
            />
            <Route
              path="/beacons"
              element={
                <RequireAuth>
                  <BeaconManagement />
                </RequireAuth>
              }
            />
            <Route
              path="/node-status"
              element={
                <RequireAuth>
                  <NodeStatus />
                </RequireAuth>
              }
            />
            <Route
              path="/history"
              element={
                <RequireAuth>
                  <DetectionHistory />
                </RequireAuth>
              }
            />
            {/* Catch-all route redirecting to devices */}
            <Route path="*" element={<Navigate to="/devices" />} />
          </Routes>
        </div>
      </div>
    </>
  );
}

export default DashboardLayout;
