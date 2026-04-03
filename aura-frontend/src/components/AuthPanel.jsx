import React, { useState } from "react";

export default function AuthPanel({ onLogin }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);

  const API = process.env.REACT_APP_API_URL;

  const login = async () => {
    if (!username || !password) {
      return alert("Enter username and password");
    }

    setLoading(true);

    try {
      const response = await fetch(`${API}/auth/login`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          username,
          password,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Login failed");
      }

      // ✅ store token
      localStorage.setItem("token", data.access_token);

      // ✅ notify parent instead of reload
      if (onLogin) onLogin();

    } catch (err) {
      console.error(err);
      alert(err.message);
    }

    setLoading(false);
  };

  return (
    <div style={styles.container}>
      <h2 style={styles.title}>🔐 AURA Login</h2>

      <input
        style={styles.input}
        placeholder="Username"
        value={username}
        onChange={(e) => setUsername(e.target.value)}
      />

      <input
        style={styles.input}
        type="password"
        placeholder="Password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
      />

      <button style={styles.button} onClick={login} disabled={loading}>
        {loading ? "Logging in..." : "Login"}
      </button>
    </div>
  );
}

const styles = {
  container: {
    background: "#0f172a",
    padding: "20px",
    borderRadius: "10px",
    maxWidth: "300px",
    margin: "20px auto",
    display: "flex",
    flexDirection: "column",
    gap: "10px",
    color: "#e2e8f0",
  },
  title: {
    textAlign: "center",
  },
  input: {
    padding: "10px",
    borderRadius: "6px",
    border: "none",
  },
  button: {
    padding: "10px",
    borderRadius: "6px",
    background: "#2563eb",
    color: "white",
    border: "none",
    cursor: "pointer",
  },
};