// File location: aura-frontend/src/components/LoginPanel.jsx
import React, { useState } from "react";

export default function LoginPanel() {
  const [isLogin, setIsLogin] = useState(true);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState("");

  // ✅ Use environment variable for backend URL
  const backendUrl = process.env.REACT_APP_API_URL || "https://aura-ai-core.onrender.com";

  const handleSubmit = async () => {
    const endpoint = isLogin ? "/auth/login" : "/auth/register";

    try {
      const res = await fetch(`${backendUrl}${endpoint}`, {
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
        // Store token for future requests
        localStorage.setItem("token", data.access_token);
        setMessage("Login successful");
        window.location.reload();
      } else {
        setMessage("Registered successfully, please login");
        setIsLogin(true);
      }
    } catch (err) {
      setMessage(err.message);
    }
  };

  return (
    <div style={{ maxWidth: "400px", margin: "100px auto" }}>
      <h2>{isLogin ? "Login" : "Register"}</h2>

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

      <button onClick={handleSubmit}>
        {isLogin ? "Login" : "Register"}
      </button>

      <p>{message}</p>

      <button onClick={() => setIsLogin(!isLogin)}>
        Switch to {isLogin ? "Register" : "Login"}
      </button>
    </div>
  );
}