import React, { useEffect, useState } from "react";

export default function HistoryPanel({ onReuse }) {
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);

  const API = process.env.REACT_APP_API_URL;

  useEffect(() => {
    const fetchHistory = async () => {
      const token = localStorage.getItem("token");

      try {
        const res = await fetch(`${API}/lab/history`, {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });

        if (!res.ok) throw new Error("Failed to fetch history");

        const data = await res.json();
        setHistory(data);
      } catch (err) {
        console.error(err);
      }

      setLoading(false);
    };

    fetchHistory();
  }, [API]);

  return (
    <div style={styles.container}>
      <h2 style={styles.title}>📜 History</h2>

      {loading && <p>Loading...</p>}

      {!loading && history.length === 0 && (
        <p style={styles.empty}>No history yet.</p>
      )}

      {history.map((h, i) => (
        <div key={i} style={styles.card}>
          <div>
            <strong>{h.goal}</strong>
          </div>

          <div style={styles.actions}>
            <button
              onClick={() => {
                // Save for reuse in SimulationPanel
                localStorage.setItem(
                  "reuse_strategy",
                  JSON.stringify(h)
                );

                if (onReuse) onReuse();
              }}
            >
              Reuse
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}

const styles = {
  container: {
    marginTop: "30px",
    background: "#0f172a",
    padding: "15px",
    borderRadius: "10px",
    color: "#e2e8f0",
  },
  title: {
    marginBottom: "10px",
  },
  empty: {
    opacity: 0.6,
  },
  card: {
    background: "#1e293b",
    padding: "10px",
    marginBottom: "10px",
    borderRadius: "6px",
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
  },
  actions: {
    display: "flex",
    gap: "10px",
  },
};