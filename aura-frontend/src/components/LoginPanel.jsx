import React, { useState } from "react";

export default function LoginPage() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const backendUrl = "https://aura-ai.onrender.com"; // change if needed

  // Register user
  const handleRegister = async () => {
    setError("");
    setMessage("");

    try {
      const res = await fetch(`${backendUrl}/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });

      if (!res.ok) throw new Error(`Register failed: ${res.status}`);
      const data = await res.json();
      setMessage("Registration successful! You can now login.");
    } catch (err) {
      setError(err.message);
    }
  };

  // Login user
  const handleLogin = async () => {
    setError("");
    setMessage("");

    try {
      const res = await fetch(`${backendUrl}/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });

      if (!res.ok) throw new Error(`Login failed: ${res.status}`);
      const data = await res.json();
      localStorage.setItem("token", data.access_token);
      setMessage("Login successful!");
    } catch (err) {
      setError(err.message);
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