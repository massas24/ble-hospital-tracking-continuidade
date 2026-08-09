import React from "react";
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
  return (
    <>
      <Sidebar />
      <div style={{ marginLeft: 220, background: "#f8f9fc", minHeight: "100vh" }}>
        <Navbar />
        <div style={{ padding: 30 }}>
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
