import React from "react";
import {
  BrowserRouter as Router,
  Routes,
  Route,
  Navigate,
  useLocation
} from "react-router-dom";

import SimulationPanel from "./components/SimulationPanel";
import Marketplace from "./pages/Marketplace";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import Navbar from "./components/Navbar";

// =============================
// 🔒 PROTECTED ROUTE
// =============================
function ProtectedRoute({ children }) {
  const token = localStorage.getItem("token");
  return token ? children : <Navigate to="/login" />;
}

// =============================
// 🧠 APP LAYOUT (WITH NAVBAR)
// =============================
function AppLayout({ children }) {
  const location = useLocation();

  // hide navbar on login page
  const hideNavbar = location.pathname === "/login";

  return (
    <>
      {!hideNavbar && <Navbar />}
      {children}
    </>
  );
}

// =============================
// 🚀 APP
// =============================
function App() {
  return (
    <Router>
      <AppLayout>
        <Routes>

          {/* PUBLIC */}
          <Route path="/login" element={<Login />} />

          {/* PROTECTED */}
          <Route
            path="/"
            element={
              <ProtectedRoute>
                <SimulationPanel />
              </ProtectedRoute>
            }
          />

          <Route
            path="/dashboard"
            element={
              <ProtectedRoute>
                <Dashboard />
              </ProtectedRoute>
            }
          />

          <Route
            path="/marketplace"
            element={
              <ProtectedRoute>
                <Marketplace />
              </ProtectedRoute>
            }
          />

          {/* DEFAULT */}
          <Route path="*" element={<Navigate to="/" />} />

        </Routes>
      </AppLayout>
    </Router>
  );
}

export default App;