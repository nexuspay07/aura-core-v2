import React, { useState } from "react";

export default function LoginPanel() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const backendUrl = "https://aura-ai.onrender.com"; // Change if needed

  // ==========================
  // REGISTER USER
  // ==========================
  const handleRegister = async () => {
    setError("");
    setMessage("");

    if (!username || !password) {
      setError("Username and password are required");
      return;
    }

    try {
      const res = await fetch(`${backendUrl}/auth/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail || "Register failed");
      }

      setMessage("✅ Registration successful! You can now login.");
    } catch (err) {
      setError(err.message || "Something went wrong");
    }
  };

  // ==========================
  // LOGIN USER
  // ==========================
  const handleLogin = async () => {
    setError("");
    setMessage("");

    if (!username || !password) {
      setError("Username and password are required");
      return;
    }

    try {
      const res = await fetch(`${backendUrl}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail || "Login failed");
      }

      // Save token
      localStorage.setItem("token", data.access_token);
      setMessage("✅ Login successful!");
    } catch (err) {
      setError(err.message || "Something went wrong");
    }
  };

  return (
    <div style={{ maxWidth: "400px", margin: "50px auto", textAlign: "center" }}>
      <h2>Login / Register</h2>

      <input
        type="text"
        placeholder="Username"
        value={username}
        onChange={(e) => setUsername(e.target.value)}
        style={{ width: "100%", marginBottom: "10px", padding: "8px" }}
      />

      <input
        type="password"
        placeholder="Password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        style={{ width: "100%", marginBottom: "10px", padding: "8px" }}
      />

      <div>
        <button onClick={handleRegister} style={{ marginRight: "10px" }}>
          Register
        </button>
        <button onClick={handleLogin}>Login</button>
      </div>

      {error && <p style={{ color: "red" }}>{error}</p>}
      {message && <p style={{ color: "green" }}>{message}</p>}
    </div>
  );
}