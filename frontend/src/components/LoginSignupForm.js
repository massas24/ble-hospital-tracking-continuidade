import React, { useState } from "react";
import axios from "axios";
import "./LoginSignupForm.css";

function LoginSignupForm() {
  const [mode, setMode] = useState("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [msg, setMsg] = useState("");
  const [showRecovery, setShowRecovery] = useState(false);
  const [recoveryInput, setRecoveryInput] = useState("");
  const [recoveryMsg, setRecoveryMsg] = useState("");

  function handleSubmit(e) {
    e.preventDefault();
    setMsg("");
    const route = mode === "signup" ? "/api/signup" : "/api/login";
    axios.post(route, { username: email, password })
      .then(res => {
        if (mode === "login" && res.data.status === "ok") {
          localStorage.setItem("username", email);
          window.location.href = "/devices";
        } else if (mode === "signup" && res.data.status === "ok") {
          setMsg("Signup successful! Please login.");
          setMode("login");
        } else {
          setMsg(res.data.error || "Error");
        }
      })
      .catch(err => setMsg(err.response?.data?.error || "Request failed"));
  }

  function handleRecovery(e) {
    e.preventDefault();
    setRecoveryMsg("");
    axios.post("/api/forgot-password", { username: recoveryInput })
      .then(() => setRecoveryMsg("If that user exists, a reset link will be sent."))
      .catch(() => setRecoveryMsg("Request failed"));
  }

  return (
    <div className="form-bg">
      <div className="center-card">
        <form className="auth-form" onSubmit={showRecovery ? handleRecovery : handleSubmit}>
          <h2 style={{ fontSize: "2.1rem", fontWeight: 400, letterSpacing: "1px", marginBottom: "24px" }}>
            {mode === "login" ? "ADMIN LOGIN" : "ADMIN SIGNUP"}
          </h2>
          {msg && <div className="msg">{msg}</div>}
          {!showRecovery ? (
            <>
              <div className="input-group">
                <input
                  className="form-input"
                  type="text"
                  placeholder="Username"
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  required
                />
                <span className="input-icon"><i className="fa fa-user" /></span>
              </div>
              <div className="input-group">
                <input
                  className="form-input"
                  type="password"
                  placeholder="Password"
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  required
                />
                <span className="input-icon"><i className="fa fa-lock" /></span>
              </div>
              {mode === "login" && (
                <a href="#" className="forgot-link" onClick={() => setShowRecovery(true)}>Lost Password?</a>
              )}
              <button className="main-btn" type="submit" style={{ marginTop: "18px", fontSize: "1.15rem", borderRadius: "8px" }}>
                {mode === "login" ? "Login" : "Signup"}
              </button>
            </>
          ) : (
            <div style={{ marginTop: 15 }}>
              <input
                type="text"
                placeholder="Username"
                value={recoveryInput}
                onChange={e => setRecoveryInput(e.target.value)}
                className="form-input"
                style={{ width: "90%", marginBottom: 10 }}
                required
              />
              <button type="submit" className="main-btn" style={{ width: "100%" }}>Recover</button>
              <div style={{ color: "#abf", marginTop: 12 }}>{recoveryMsg}</div>
              <a href="#" style={{ fontSize: 13, marginTop: 9, display: "inline-block" }} onClick={() => setShowRecovery(false)}>Go back to login</a>
            </div>
          )}
        </form>
        {!showRecovery && <div className="switch-link">
          {mode === "login"
            ? <>Create an account <span className="link-btn" onClick={() => setMode("signup")}>Signup now</span></>
            : <>Already have an account? <span className="link-btn" onClick={() => setMode("login")}>Log in</span></>
          }
        </div>}
      </div>
    </div>
  );
}

export default LoginSignupForm;
