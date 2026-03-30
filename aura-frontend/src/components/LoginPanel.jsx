import React, { useState } from "react";

export default function LoginPanel() {
  const [isRegister, setIsRegister] = useState(false);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");

  const endpoint = isRegister ? "register" : "login";

  const handleSubmit = async (e) => {
    e.preventDefault();

    try {
      const response = await fetch(`http://aura-ai.onrender.com/${endpoint}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({ username, password })
      });

      const data = await response.json();

      if (!response.ok) {
        alert(data.detail || "Error");
        return;
      }

      // ✅ REGISTER → just switch to login
      if (isRegister) {
        alert("Account created. Please login.");
        setIsRegister(false);
        return;
      }

      // ✅ LOGIN → save token
      localStorage.setItem("token", data.access_token);

      // ✅ redirect
      window.location.href = "/";

    } catch (err) {
      console.error(err);
      alert("Server connection failed");
    }
  };

  return (
    <div style={{ padding: "40px", textAlign: "center" }}>
      <h2>{isRegister ? "Register" : "Login"}</h2>

      <form onSubmit={handleSubmit}>
        <input
          type="text"
          placeholder="Username"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
        />
        <br /><br />

        <input
          type="password"
          placeholder="Password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        <br /><br />

        <button type="submit">
          {isRegister ? "Create Account" : "Login"}
        </button>
      </form>

      <br />

      <button onClick={() => setIsRegister(!isRegister)}>
        {isRegister
          ? "Already have an account? Login"
          : "Create new account"}
      </button>
    </div>
  );
}