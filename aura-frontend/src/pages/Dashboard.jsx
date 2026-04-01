import React, { useEffect, useState } from "react";

export default function Dashboard() {
  const [history, setHistory] = useState([]);
  const [totalRuns, setTotalRuns] = useState(0);
  const [avgScore, setAvgScore] = useState(0);
  const [error, setError] = useState("");

  const backendUrl = "https://aura-ai-core.onrender.com";

  const token = localStorage.getItem("token");

  useEffect(() => {
    if (!token) return;

    const fetchDashboard = async () => {
      try {
        const res = await fetch(`${backendUrl}/dashboard`, {
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
        });

        const data = await res.json();

        if (!res.ok) throw new Error(data.detail || "Failed to fetch");

        setHistory(data.history);
        setTotalRuns(data.total_runs);
        setAvgScore(data.average_score);
      } catch (err) {
        setError(err.message || "Something went wrong");
      }
    };

    fetchDashboard();
  }, [token]);

  if (!token) return <p>Please login first.</p>;

  return (
    <div style={{ maxWidth: "800px", margin: "50px auto" }}>
      <h2>Dashboard</h2>
      {error && <p style={{ color: "red" }}>{error}</p>}

      <p>Total Runs: {totalRuns}</p>
      <p>Average Score: {avgScore.toFixed(2)}</p>

      <h3>History</h3>
      {history.length === 0 && <p>No simulations yet.</p>}
      <ul>
        {history.map((sim, idx) => (
          <li key={idx}>
            <strong>Goal:</strong> {sim.goal} |{" "}
            <strong>Best Strategy:</strong>{" "}
            {sim.result?.best_strategy?.name || "N/A"} |{" "}
            <strong>Score:</strong>{" "}
            {sim.result?.best_strategy?.final_score ?? "N/A"}
          </li>
        ))}
      </ul>
    </div>
  );
}