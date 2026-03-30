import React, { useEffect, useState } from "react";

export default function HistoryPanel() {
  const [history, setHistory] = useState([]);

  useEffect(() => {
    const token = localStorage.getItem("token");

    fetch("http://aura-ai.onrender.com/lab/history", {
      headers: {
        Authorization: `Bearer ${token}`
      }
    })
      .then(res => res.json())
      .then(data => setHistory(data))
      .catch(err => console.error(err));
  }, []);

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