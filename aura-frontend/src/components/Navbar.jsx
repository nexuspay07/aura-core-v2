const Navbar = () => {
  return (
    <div style={{
      display: "flex",
      justifyContent: "space-between",
      padding: "10px 20px",
      background: "#111",
      color: "#fff"
    }}>
      <h2>AURA AI</h2>

      <button
        onClick={() => {
          localStorage.removeItem("token")
          window.location.href = "/login"
        }}
        style={{
          padding: "8px 16px",
          background: "red",
          color: "white",
          border: "none",
          borderRadius: "5px",
          cursor: "pointer"
        }}
      >
        Logout
      </button>
    </div>
  )
}

export default Navbar