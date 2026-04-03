import React, { useState, useEffect } from "react";
import AgentPanel from "./AgentPanel";
import HistoryPanel from "./HistoryPanel";

export default function SimulationPanel() {
  const [scenario, setScenario] = useState("");
  const [logs, setLogs] = useState([]);
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [agents, setAgents] = useState([]);

  const [risk, setRisk] = useState(0.5);
  const [budget, setBudget] = useState(10000);
  const [market, setMarket] = useState("normal");

  const [pendingStep, setPendingStep] = useState(false);

  const API = process.env.REACT_APP_API_URL;

  // =============================
  // LOAD SAVED STRATEGY
  // =============================
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

    const res = await fetch(`${API}${endpoint}`, {
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
    try {
      await authFetch("/control/approve", { method: "POST" });
      setPendingStep(false);
    } catch {
      alert("Approve failed");
    }
  };

  const rejectStep = async () => {
    try {
      await authFetch("/control/reject", { method: "POST" });
      setPendingStep(false);
    } catch {
      alert("Reject failed");
    }
  };

  // =============================
  // NORMAL SIMULATION
  // =============================
  const runSimulation = async () => {
    if (!scenario.trim()) return alert("Enter a goal");

    setLoading(true);
    setResults(null);

    try {
      const res = await authFetch("/lab/simulate", {
        method: "POST",
        body: JSON.stringify({
          goal: scenario,
          risk_tolerance: risk,
          budget,
          market,
        }),
      });

      const data = await res.json();
      setResults(data);

      // Optional: extract agents if backend returns them
      if (data.agents) setAgents(data.agents);
    } catch (err) {
      console.error(err);
      alert("Simulation failed");
    }

    setLoading(false);
  };

  // =============================
  // LIVE SIMULATION (STREAM)
  // =============================
  const runLiveSimulation = async () => {
    if (!scenario.trim()) return alert("Enter a goal");

    setLogs([]);
    setAgents([]);
    setLoading(true);
    setPendingStep(false);

    try {
      const response = await authFetch("/system/run_stream", {
        method: "POST",
        body: JSON.stringify({
          goal: scenario,
          risk_tolerance: risk,
          budget,
          market,
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

        lines
          .map((l) => l.trim())
          .filter(Boolean)
          .forEach((line) => {
            // Detect approval step
            if (line.includes("⚠️ Waiting for human approval")) {
              setPendingStep(true);
            }

            // Extract agent logs (simple parser)
            if (line.includes("→")) {
              const [agent, message] = line.split("→");
              setAgents((prev) => [
                ...prev,
                { agent: agent.trim(), message: message.trim() },
              ]);
            }

            setLogs((prev) => [...prev, line]);
          });
      }
    } catch (err) {
      console.error(err);
      setLogs((prev) => [...prev, "❌ Stream error"]);
    }

    setLoading(false);
  };

  return (
    <div style={styles.container}>
      <h1 style={styles.title}>AURA Simulation Lab</h1>

      <button onClick={handleLogout}>Logout</button>

      <input
        placeholder="Enter scenario..."
        value={scenario}
        onChange={(e) => setScenario(e.target.value)}
        style={styles.input}
      />

      <div style={styles.controls}>
        <label>Risk: {risk}</label>
        <input
          type="range"
          min="0"
          max="1"
          step="0.1"
          value={risk}
          onChange={(e) => setRisk(parseFloat(e.target.value))}
        />

        <label>Budget</label>
        <input
          type="number"
          value={budget}
          onChange={(e) => setBudget(Number(e.target.value))}
        />

        <label>Market</label>
        <select value={market} onChange={(e) => setMarket(e.target.value)}>
          <option value="low">Low</option>
          <option value="normal">Normal</option>
          <option value="high">High</option>
        </select>
      </div>

      <div style={styles.buttons}>
        <button onClick={runSimulation} disabled={loading}>
          Simulate
        </button>
        <button onClick={runLiveSimulation} disabled={loading}>
          Live 🔥
        </button>
      </div>

      {loading && <p>Running...</p>}

      {pendingStep && (
        <div style={styles.approval}>
          <p>⚠️ Awaiting your decision</p>
          <button onClick={approveStep}>Approve</button>
          <button onClick={rejectStep}>Reject</button>
        </div>
      )}

      <AgentPanel agents={agents} />

      <h3>Logs</h3>
      <div style={styles.logs}>
        {logs.map((log, i) => (
          <div key={i}>{log}</div>
        ))}
      </div>

      <h3>Results</h3>
      <pre style={styles.results}>
        {results ? JSON.stringify(results, null, 2) : "No results"}
      </pre>
    </div>
  );
}

const styles = {
  container: {
    padding: "20px",
    fontFamily: "Arial",
    background: "#020617",
    color: "#e2e8f0",
    minHeight: "100vh",
  },
  title: {
    marginBottom: "10px",
  },
  input: {
    width: "100%",
    padding: "10px",
    margin: "10px 0",
  },
  controls: {
    display: "flex",
    flexDirection: "column",
    gap: "10px",
    marginBottom: "15px",
  },
  buttons: {
    display: "flex",
    gap: "10px",
    marginBottom: "15px",
  },
  approval: {
    background: "#7c2d12",
    padding: "10px",
    borderRadius: "6px",
    marginBottom: "15px",
  },
  logs: {
    background: "#000",
    color: "#0f0",
    padding: "10px",
    height: "200px",
    overflowY: "auto",
  },
  results: {
    background: "#111",
    padding: "10px",
  },
};
<HistoryPanel onReuse={() => window.location.reload()} />