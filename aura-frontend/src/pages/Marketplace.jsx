import React, { useEffect, useState } from "react";

export default function Marketplace() {
  const [strategies, setStrategies] = useState([]);
  const [myStrategies, setMyStrategies] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const API = process.env.REACT_APP_API_URL;
  const token = localStorage.getItem("token");

  // =============================
  // AUTH FETCH
  // =============================
  const authFetch = async (url) => {
    const res = await fetch(url, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });

    if (!res.ok) throw new Error("Request failed");

    return res.json();
  };

  // =============================
  // LOAD DATA
  // =============================
  const loadStrategies = async () => {
    try {
      const [all, mine] = await Promise.all([
        authFetch(`${API}/marketplace/all`),
        authFetch(`${API}/marketplace/mine`),
      ]);

      setStrategies(all || []);
      setMyStrategies(mine || []);
    } catch (err) {
      setError("Failed to load marketplace");
    }

    setLoading(false);
  };

  useEffect(() => {
    if (!token) return;
    loadStrategies();
  }, [token]);

  // =============================
  // REUSE
  // =============================
  const reuseStrategy = (strategy) => {
    localStorage.setItem("reuse_strategy", JSON.stringify(strategy));
    window.location.href = "/";
  };

  // =============================
  // DELETE
  // =============================
  const deleteStrategy = async (id) => {
    try {
      await fetch(`${API}/marketplace/${id}`, {
        method: "DELETE",
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      loadStrategies();
    } catch (err) {
      setError("Delete failed");
    }
  };

  if (!token) {
    return <p style={styles.center}>Please login first.</p>;
  }

  return (
    <div style={styles.container}>
      <h1 style={styles.title}>🌐 AURA Marketplace</h1>

      <button style={styles.backBtn} onClick={() => (window.location.href = "/")}>
        ⬅ Back to Lab
      </button>

      {loading && <p>Loading strategies...</p>}
      {error && <p style={styles.error}>{error}</p>}

      {/* MY STRATEGIES */}
      <div style={styles.section}>
        <h2>👤 My Strategies</h2>

        {myStrategies.length === 0 && <p>No strategies yet</p>}

        {myStrategies.map((s, i) => (
          <StrategyCard
            key={i}
            s={s}
            isMine={true}
            onReuse={reuseStrategy}
            onDelete={deleteStrategy}
          />
        ))}
      </div>

      {/* PUBLIC */}
      <div style={styles.section}>
        <h2>🌍 Public Strategies</h2>

        {strategies.length === 0 && <p>No public strategies</p>}

        {strategies.map((s, i) => (
          <StrategyCard
            key={i}
            s={s}
            isMine={false}
            onReuse={reuseStrategy}
          />
        ))}
      </div>
    </div>
  );
}

// =============================
// CARD COMPONENT
// =============================
const StrategyCard = ({ s, isMine, onReuse, onDelete }) => (
  <div style={styles.card}>
    <h3>{s.name}</h3>

    <p><b>Goal:</b> {s.goal}</p>

    <p>
      <b>Score:</b>{" "}
      {s.data?.final_score || s.data?.score || "N/A"}
    </p>

    <div style={styles.actions}>
      <button style={styles.useBtn} onClick={() => onReuse(s)}>
        🔁 Use
      </button>

      {isMine && (
        <button style={styles.deleteBtn} onClick={() => onDelete(s.id)}>
          🗑 Delete
        </button>
      )}
    </div>
  </div>
);

// =============================
// STYLES
// =============================
const styles = {
  container: {
    maxWidth: "1000px",
    margin: "40px auto",
    padding: "20px",
    color: "#e2e8f0",
  },
  title: {
    marginBottom: "10px",
  },
  center: {
    textAlign: "center",
    marginTop: "50px",
  },
  error: {
    color: "#f87171",
  },
  backBtn: {
    marginBottom: "20px",
    padding: "8px 12px",
    background: "#1e293b",
    color: "white",
    border: "none",
    borderRadius: "6px",
    cursor: "pointer",
  },
  section: {
    background: "#0f172a",
    padding: "20px",
    borderRadius: "10px",
    marginBottom: "20px",
  },
  card: {
    background: "#020617",
    padding: "15px",
    borderRadius: "10px",
    marginTop: "10px",
    border: "1px solid #1e293b",
  },
  actions: {
    marginTop: "10px",
    display: "flex",
    gap: "10px",
  },
  useBtn: {
    padding: "6px 12px",
    background: "#2563eb",
    color: "white",
    border: "none",
    borderRadius: "6px",
    cursor: "pointer",
  },
  deleteBtn: {
    padding: "6px 12px",
    background: "#dc2626",
    color: "white",
    border: "none",
    borderRadius: "6px",
    cursor: "pointer",
  },
};