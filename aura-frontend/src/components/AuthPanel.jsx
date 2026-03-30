import React, { useState } from "react";
const AuthPanel = () => {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");

  const login = async () => {
    const formData = new URLSearchParams();
    formData.append("username", username);
    formData.append("password", password);

    const response = await fetch("http://aura-ai.onrender.com/auth/login", {
      method: "POST",
      body: formData
    });

    const data = await response.json();

    if (data.access_token) {
      localStorage.setItem("token", data.access_token);
      alert("Login successful");
    } else {
      alert("Login failed");
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