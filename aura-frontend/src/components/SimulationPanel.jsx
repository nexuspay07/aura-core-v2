// src/components/SimulationPanel.jsx

import React, { useState } from "react";
import { useEffect } from "react";
export default function SimulationPanel() {
  const [scenario, setScenario] = useState("");
  const [logs, setLogs] = useState([]);
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);

  const [risk, setRisk] = useState(0.5);
  const [budget, setBudget] = useState(10000);
  const [market, setMarket] = useState("normal");

  const [pendingStep, setPendingStep] = useState(null);

  useEffect(() => {
  const saved = localStorage.getItem("reuse_strategy");

  if (saved) {
    const strategy = JSON.parse(saved);

    setScenario(strategy.goal || "");
    localStorage.removeItem("reuse_strategy");
  }
}, []);

  // =============================
  // AUTH FETCH (SAFE)
  // =============================
  const authFetch = async (url, options = {}) => {
    const token = localStorage.getItem("token");

    const res = await fetch(url, {
      ...options,
      headers: {
        ...(options.headers || {}),
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json"
      }
    });

    if (!res.ok) {
      throw new Error("Request failed");
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
    await authFetch("http://aura-ai.onrender.com/control/approve", {
      method: "POST"
    });
    setPendingStep(null);
  };

  const rejectStep = async () => {
    await authFetch("http://aura-ai.onrender.com/control/reject", {
      method: "POST"
    });
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
      const res = await authFetch("https://aura-ai.onrender.com/lab/simulate", {
        method: "POST",
        body: JSON.stringify({
          goal: scenario,
          risk_tolerance: risk,
          budget: budget,
          market: market
        })
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
  // ✅ SAVE STRATEGY (FIXED)
  // =============================
  const saveStrategy = async (strategy) => {
    try {
      const res = await authFetch("http://aura-ai.onrender.com/marketplace/save", {
        method: "POST",
        body: JSON.stringify({
          name: strategy.name,
          goal: scenario,
          ...strategy
        })
      });

      const data = await res.json();
      alert(data.message || "Saved to marketplace ✅");

    } catch (err) {
      console.error(err);
      alert("Failed to save strategy ❌");
    }
  };

  // =============================
  // LIVE SIMULATION (WITH UX FIX)
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
      const response = await authFetch("http://aura-ai.onrender.com/system/run_stream", {
        method: "POST",
        body: JSON.stringify({
          goal: scenario,
          risk_tolerance: risk,
          budget: budget,
          market: market
        })
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
          .map(line => {
            // 🔥 UX FIX HERE
            if (line.includes("Arbitration selected")) {
              return line.replace(
                "Arbitration selected",
                "Arbitration suggestion (intermediate)"
              );
            }
            return line;
          });

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

      {/* CONTROLS */}
      <div>
        <label>Risk: {risk}</label>
        <br />
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
        <br />
        <input
          type="number"
          value={budget}
          onChange={(e) => setBudget(Number(e.target.value))}
        />

        <br /><br />

        <label>Market:</label>
        <br />
        <select value={market} onChange={(e) => setMarket(e.target.value)}>
          <option value="low">Low</option>
          <option value="normal">Normal</option>
          <option value="high">High</option>
        </select>
      </div>

      <br />

      <button onClick={runSimulation} disabled={loading}>
        Run Simulation
      </button>

      <button
        onClick={runLiveSimulation}
        disabled={loading}
        style={{ marginLeft: "10px" }}
      >
        Run Live Simulation 🔥
      </button>

      <button
        onClick={() => window.location.href = "/marketplace"}
        style={{ marginLeft: "10px" }}
      >
        Open Marketplace
      </button>

      {loading && <p>Running simulation...</p>}

      {/* HUMAN CONTROL */}
      {pendingStep && (
        <div style={{
          marginTop: "20px",
          padding: "15px",
          border: "2px solid orange",
          borderRadius: "10px"
        }}>
          <h3>⚠️ AI Waiting for Approval</h3>

          <button onClick={approveStep} style={{ marginRight: "10px" }}>
            ✅ Approve
          </button>

          <button onClick={rejectStep}>
            ❌ Reject
          </button>
        </div>
      )}

      {/* LIVE LOGS */}
      <h2>Live Logs</h2>
      <div style={{
        background: "#111",
        color: "#0f0",
        padding: "10px",
        height: "250px",
        overflowY: "scroll",
        whiteSpace: "pre-line"
      }}>
        {logs.map((log, i) => (
          <div key={i}>{log}</div>
        ))}
      </div>

      {/* RESULTS */}
      <h2>Results</h2>

      {results && results.results && (
        <div>
          {results.results.map((strategy, i) => (
            <div key={i} style={{
              border: "1px solid gray",
              padding: "10px",
              marginBottom: "10px"
            }}>
              <p><b>{strategy.name}</b></p>
              <p>Score: {strategy.final_score || strategy.score}</p>

              <button onClick={() => saveStrategy(strategy)}>
                💾 Save Strategy
              </button>
            </div>
          ))}
        </div>
      )}

      <pre style={{
        background: "#f4f4f4",
        padding: "10px",
        borderRadius: "5px",
        maxHeight: "300px",
        overflowY: "scroll"
      }}>
        {results ? JSON.stringify(results, null, 2) : "No results yet"}
      </pre>
    </div>
  );
}