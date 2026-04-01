// File: aura-frontend/src/pages/Login.jsx

import React, { useState } from "react";

const Login = () => {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");

  // ✅ single backend source
  const backendUrl =
    process.env.REACT_APP_API_URL ||
    "https://aura-ai-core.onrender.com";

  const handleLogin = async () => {
    try {
      const res = await fetch(`${backendUrl}/auth/login`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          username,
          password
        })
      });

      const data = await res.json();
      console.log("LOGIN RESPONSE:", data);

      if (!res.ok) {
        throw new Error(data.detail || "Login failed");
      }

      // ✅ SAVE TOKEN
      localStorage.setItem("token", data.access_token);

      alert("Login successful ✅");

      // optional: redirect instead of just staying
      window.location.href = "/";

    } catch (err) {
      console.error(err);
      alert(err.message || "Server error");
    }
  };

  return (
    <div>
      <h2>Login</h2>

      <input
        placeholder="Username"
        onChange={(e) => setUsername(e.target.value)}
      />

      <input
        type="password"
        placeholder="Password"
        onChange={(e) => setPassword(e.target.value)}
      />

      <button onClick={handleLogin}>Login</button>
    </div>
  );
};

export default Login;