import React, { useEffect, useState } from "react";

export default function Marketplace() {
  const [strategies, setStrategies] = useState([]);
  const [myStrategies, setMyStrategies] = useState([]);
  const [loading, setLoading] = useState(true);

  // =============================
  // AUTH FETCH
  // =============================
  const authFetch = async (url) => {
    const token = localStorage.getItem("token");

    const res = await fetch(url, {
      headers: {
        Authorization: `Bearer ${token}`
      }
    });

    if (!res.ok) throw new Error("Failed request");

    return res.json();
  };

  // =============================
  // LOAD DATA
  // =============================
  const loadStrategies = async () => {
    try {
      const [all, mine] = await Promise.all([
        authFetch("http://aura-ai.onrender.com/marketplace/all"),
        authFetch("http://aura-ai.onrender.com/marketplace/mine")
      ]);

      setStrategies(all);
      setMyStrategies(mine);
    } catch (err) {
      console.error(err);
      alert("Failed to load marketplace");
    }

    setLoading(false);
  };

  useEffect(() => {
    loadStrategies();
  }, []);

  // =============================
  // REUSE STRATEGY
  // =============================
  const reuseStrategy = (strategy) => {
    localStorage.setItem("reuse_strategy", JSON.stringify(strategy));
    window.location.href = "/";
  };

  // =============================
  // DELETE (ONLY YOURS)
  // =============================
  const deleteStrategy = async (id) => {
    try {
      await fetch(`http://aura-ai.onrender.com/marketplace/${id}`, {
        method: "DELETE",
        headers: {
          Authorization: `Bearer ${localStorage.getItem("token")}`
        }
      });

      alert("Deleted");
      loadStrategies();

    } catch (err) {
      console.error(err);
      alert("Delete failed");
    }
  };

  // =============================
  // UI CARD
  // =============================
  const StrategyCard = ({ s, isMine }) => (
    <div style={{
      border: "1px solid #ccc",
      borderRadius: "10px",
      padding: "15px",
      marginBottom: "10px",
      background: "#fff"
    }}>
      <h3>{s.name}</h3>
      <p><b>Goal:</b> {s.goal}</p>

      <p>
        <b>Score:</b>{" "}
        {s.data?.final_score || s.data?.score || "N/A"}
      </p>

      <button onClick={() => reuseStrategy(s)}>
        🔁 Use Strategy
      </button>

      {isMine && (
        <button
          onClick={() => deleteStrategy(s.id)}
          style={{ marginLeft: "10px", color: "red" }}
        >
          🗑 Delete
        </button>
      )}
    </div>
  );

  // =============================
  // RENDER
  // =============================
  return (
    <div style={{ padding: "20px", fontFamily: "Arial" }}>
      <h1>🌐 AURA Marketplace</h1>

      <button onClick={() => window.location.href = "/"}>
        ⬅ Back to Lab
      </button>

      {loading && <p>Loading...</p>}

      {/* MY STRATEGIES */}
      <h2>👤 My Strategies</h2>
      {myStrategies.length === 0 && <p>No strategies yet</p>}

      {myStrategies.map((s, i) => (
        <StrategyCard key={i} s={s} isMine={true} />
      ))}

      {/* PUBLIC */}
      <h2>🌍 Public Strategies</h2>
      {strategies.length === 0 && <p>No public strategies</p>}

      {strategies.map((s, i) => (
        <StrategyCard key={i} s={s} isMine={false} />
      ))}
    </div>
  );
}