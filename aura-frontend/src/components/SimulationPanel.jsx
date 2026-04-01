// File: aura-frontend/src/components/SimulationPanel.jsx

import React, { useState, useEffect } from "react";

export default function SimulationPanel() {
  const [scenario, setScenario] = useState("");
  const [logs, setLogs] = useState([]);
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);

  const [risk, setRisk] = useState(0.5);
  const [budget, setBudget] = useState(10000);
  const [market, setMarket] = useState("normal");

  const [pendingStep, setPendingStep] = useState(null);

  // ✅ SINGLE SOURCE OF TRUTH
  const backendUrl =
    process.env.REACT_APP_API_URL ||
    "https://aura-ai-core.onrender.com";

  useEffect(() => {
    const saved = localStorage.getItem("reuse_strategy");

    if (saved) {
      const strategy = JSON.parse(saved);
      setScenario(strategy.goal || "");
      localStorage.removeItem("reuse_strategy");
    }
  }, []);

  // =============================
  // AUTH FETCH
  // =============================
  const authFetch = async (endpoint, options = {}) => {
    const token = localStorage.getItem("token");

    const res = await fetch(`${backendUrl}${endpoint}`, {
      ...options,
      headers: {
        ...(options.headers || {}),
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
    });

    if (!res.ok) {
      const text = await res.text();
      throw new Error(text || "Request failed");
    }

    return res;
  };

  // =============================
  // LOGOUT
  // =============================
  const handleLogout = () => {
    localStorage.removeItem("token");
    window.location.reload();
  };

  // =============================
  // APPROVE / REJECT
  // =============================
  const approveStep = async () => {
    await authFetch("/control/approve", { method: "POST" });
    setPendingStep(null);
  };

  const rejectStep = async () => {
    await authFetch("/control/reject", { method: "POST" });
    setPendingStep(null);
  };

  // =============================
  // NORMAL SIMULATION
  // =============================
  const runSimulation = async () => {
    if (!scenario.trim()) {
      alert("Enter a goal");
      return;
    }

    setLoading(true);
    setResults(null);

    try {
      const res = await authFetch("/lab/simulate", {
        method: "POST",
        body: JSON.stringify({
          goal: scenario,
          risk_tolerance: risk,
          budget: budget,
          market: market,
        }),
      });

      const data = await res.json();
      setResults(data);
    } catch (err) {
      console.error(err);
      alert("Simulation failed");
    }

    setLoading(false);
  };

  // =============================
  // SAVE STRATEGY
  // =============================
  const saveStrategy = async (strategy) => {
    try {
      const res = await authFetch("/marketplace/save", {
        method: "POST",
        body: JSON.stringify({
          name: strategy.name,
          goal: scenario,
          ...strategy,
        }),
      });

      const data = await res.json();
      alert(data.message || "Saved ✅");
    } catch (err) {
      console.error(err);
      alert("Save failed ❌");
    }
  };

  // =============================
  // LIVE SIMULATION
  // =============================
  const runLiveSimulation = async () => {
    if (!scenario.trim()) {
      alert("Enter a goal");
      return;
    }

    setLogs([]);
    setLoading(true);
    setPendingStep(null);

    try {
      const response = await authFetch("/system/run_stream", {
        method: "POST",
        body: JSON.stringify({
          goal: scenario,
          risk_tolerance: risk,
          budget: budget,
          market: market,
        }),
      });

      const reader = response.body.getReader();
      const decoder = new TextDecoder();

      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        const lines = buffer.split("\n");
        buffer = lines.pop();

        const cleanLines = lines
          .map(l => l.trim())
          .filter(l => l !== "")
          .map(line =>
            line.includes("Arbitration selected")
              ? line.replace(
                  "Arbitration selected",
                  "Arbitration suggestion (intermediate)"
                )
              : line
          );

        cleanLines.forEach(line => {
          if (line.includes("⚠️ Waiting for human approval")) {
            setPendingStep(true);
          }
        });

        setLogs(prev => [...prev, ...cleanLines]);
      }
    } catch (err) {
      console.error(err);
      setLogs(prev => [...prev, "❌ Stream error"]);
    }

    setLoading(false);
  };

  // =============================
  // UI
  // =============================
  return (
    <div style={{ padding: "20px", fontFamily: "Arial" }}>
      <h1>AURA Simulation Lab</h1>

      <button onClick={handleLogout}>Logout</button>

      <br /><br />

      <input
        type="text"
        placeholder="Enter scenario..."
        value={scenario}
        onChange={(e) => setScenario(e.target.value)}
        style={{ width: "300px", padding: "8px" }}
      />

      <br /><br />

      <label>Risk: {risk}</label>
      <input
        type="range"
        min="0"
        max="1"
        step="0.1"
        value={risk}
        onChange={(e) => setRisk(parseFloat(e.target.value))}
      />

      <br /><br />

      <label>Budget:</label>
      <input
        type="number"
        value={budget}
        onChange={(e) => setBudget(Number(e.target.value))}
      />

      <br /><br />

      <label>Market:</label>
      <select value={market} onChange={(e) => setMarket(e.target.value)}>
        <option value="low">Low</option>
        <option value="normal">Normal</option>
        <option value="high">High</option>
      </select>

      <br /><br />

      <button onClick={runSimulation} disabled={loading}>
        Run Simulation
      </button>

      <button onClick={runLiveSimulation} disabled={loading}>
        Run Live 🔥
      </button>

      {loading && <p>Running...</p>}

      <h2>Live Logs</h2>
      <div style={{
        background: "#111",
        color: "#0f0",
        padding: "10px",
        height: "250px",
        overflowY: "scroll"
      }}>
        {logs.map((log, i) => <div key={i}>{log}</div>)}
      </div>

      <h2>Results</h2>
      <pre>
        {results ? JSON.stringify(results, null, 2) : "No results"}
      </pre>
    </div>
  );
}