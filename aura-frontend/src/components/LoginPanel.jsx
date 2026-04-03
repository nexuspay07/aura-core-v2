import React, { useState } from "react";

export default function LoginPanel({ onLogin }) {
  const [isLogin, setIsLogin] = useState(true);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);

  const API = process.env.REACT_APP_API_URL;

  const handleSubmit = async () => {
    if (!username || !password) {
      return setMessage("Enter username and password");
    }

    setLoading(true);
    setMessage("");

    const endpoint = isLogin ? "/auth/login" : "/auth/register";

    try {
      const res = await fetch(`${API}${endpoint}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ username, password }),
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail || "Something went wrong");
      }

      if (isLogin) {
        // ✅ store token
        localStorage.setItem("token", data.access_token);

        // ✅ notify app (no reload)
        if (onLogin) onLogin();
      } else {
        setMessage("Registered successfully. You can now log in.");
        setIsLogin(true);
      }
    } catch (err) {
      setMessage(err.message);
    }

    setLoading(false);
  };

  return (
    <div style={styles.container}>
      <h2 style={styles.title}>
        {isLogin ? "🔐 Login" : "🆕 Register"}
      </h2>

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

      <button style={styles.button} onClick={handleSubmit} disabled={loading}>
        {loading
          ? "Please wait..."
          : isLogin
          ? "Login"
          : "Register"}
      </button>

      {message && <p style={styles.message}>{message}</p>}

      <button
        style={styles.switch}
        onClick={() => {
          setIsLogin(!isLogin);
          setMessage("");
        }}
      >
        Switch to {isLogin ? "Register" : "Login"}
      </button>
    </div>
  );
}

const styles = {
  container: {
    maxWidth: "400px",
    margin: "100px auto",
    padding: "20px",
    background: "#0f172a",
    borderRadius: "10px",
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
  switch: {
    background: "transparent",
    border: "none",
    color: "#38bdf8",
    cursor: "pointer",
  },
  message: {
    fontSize: "14px",
    textAlign: "center",
  },
};