// File: aura-frontend/src/components/AuthPanel.jsx

import React, { useState } from "react";

const AuthPanel = () => {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");

  // ✅ central backend URL
  const backendUrl =
    process.env.REACT_APP_API_URL ||
    "https://aura-ai-core.onrender.com";

  const login = async () => {
    try {
      const response = await fetch(`${backendUrl}/auth/login`, {
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

      localStorage.setItem("token", data.access_token);
      alert("Login successful ✅");

      // optional reload
      window.location.reload();

    } catch (err) {
      console.error(err);
      alert(err.message);
    }
  };

  return (
    <div style={{ marginBottom: "20px" }}>
      <h2>Login</h2>

      <input
        placeholder="Username"
        value={username}
        onChange={(e) => setUsername(e.target.value)}
      />

      <input
        type="password"
        placeholder="Password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
      />

      <button onClick={login}>Login</button>
    </div>
  );
};

export default AuthPanel;