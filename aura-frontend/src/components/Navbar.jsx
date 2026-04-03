export default function Navbar({ onLogout }) {
  const handleLogout = () => {
    localStorage.removeItem("token");

    // ✅ Notify parent instead of forcing page redirect
    if (onLogout) onLogout();
  };

  return (
    <div style={styles.container}>
      <h2 style={styles.logo}>AURA AI</h2>

      <button style={styles.button} onClick={handleLogout}>
        Logout
      </button>
    </div>
  );
}

const styles = {
  container: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    padding: "12px 20px",
    background: "#020617",
    color: "#e2e8f0",
    borderBottom: "1px solid #1e293b",
  },
  logo: {
    margin: 0,
  },
  button: {
    padding: "8px 16px",
    background: "#dc2626",
    color: "white",
    border: "none",
    borderRadius: "6px",
    cursor: "pointer",
  },
};