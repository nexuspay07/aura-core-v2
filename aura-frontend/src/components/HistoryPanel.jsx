// File: aura-frontend/src/components/HistoryPanel.jsx

import React, { useEffect, useState } from "react";

export default function HistoryPanel() {
  const [history, setHistory] = useState([]);

  // ✅ Use environment variable
  const backendUrl = process.env.REACT_APP_API_URL || "https://aura-ai-core.onrender.com";

  useEffect(() => {
    const token = localStorage.getItem("token");

    fetch(`${backendUrl}/lab/history`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    })
      .then(res => {
        if (!res.ok) throw new Error("Failed to fetch history");
        return res.json();
      })
      .then(data => setHistory(data))
      .catch(err => console.error(err));
  }, [backendUrl]);

  return (
    <div style={{ marginTop: "30px" }}>
      <h2>📜 History</h2>

      {history.length === 0 && <p>No history yet.</p>}

      {history.map((h, i) => (
        <div key={i} style={{ marginBottom: "10px" }}>
          <strong>{h.goal}</strong>
        </div>
      ))}
    </div>
  );
}