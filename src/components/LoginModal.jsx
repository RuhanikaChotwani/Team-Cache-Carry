import React, { useState, useEffect } from "react";
import * as api from "../api";
import { Lock, Shield, User, LogOut, Check, AlertCircle } from "lucide-react";

export default function LoginModal({ user, onLoginSuccess, onLogout }) {
  const [currentUser, setCurrentUser] = useState(user || null);
  const [isOpen, setIsOpen] = useState(false);
  const [username, setUsername] = useState("officer");
  const [password, setPassword] = useState("officer123");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    setCurrentUser(user || null);
  }, [user]);

  useEffect(() => {
    // Check existing auth token on mount
    if (api.getAuthToken()) {
      api.getAuthProfile()
        .then((u) => {
          if (u) {
            setCurrentUser(u);
            if (onLoginSuccess) onLoginSuccess(u);
          } else {
            api.setAuthToken("");
            setCurrentUser(null);
            if (onLogout) onLogout();
          }
        })
        .catch(() => {
          api.setAuthToken("");
          setCurrentUser(null);
          if (onLogout) onLogout();
        });
    }
  }, []);

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const res = await api.login(username.trim(), password);
      setCurrentUser(res.user);
      setIsOpen(false);
      if (onLoginSuccess) onLoginSuccess(res.user);
    } catch (err) {
      setError(err.message || "Invalid credentials. Access denied.");
    }
    setLoading(false);
  };

  const handleLogout = async () => {
    await api.logout();
    setCurrentUser(null);
    if (onLogout) onLogout();
  };

  return (
    <div>
      {/* Navbar User Status / Login Button */}
      {currentUser ? (
        <div style={{ display: "flex", alignItems: "center", gap: "8px", background: "#03172a", border: "1px solid var(--border)", borderRadius: "6px", padding: "4px 8px", fontSize: "11px" }}>
          <Shield size={13} color="var(--cyan)" />
          <span>
            <strong style={{ color: "#fff" }}>{currentUser.username.toUpperCase()}</strong> ({currentUser.role})
          </span>
          <button
            onClick={handleLogout}
            title="Logout"
            style={{ background: "transparent", border: "none", color: "var(--red)", cursor: "pointer", display: "flex", alignItems: "center", padding: "0 2px" }}
          >
            <LogOut size={12} />
          </button>
        </div>
      ) : (
        <button
          onClick={() => setIsOpen(true)}
          style={{
            background: "rgba(22,185,201,0.15)", border: "1px solid var(--cyan)", color: "var(--cyan)",
            borderRadius: "6px", padding: "5px 10px", fontSize: "11px", fontWeight: "600",
            cursor: "pointer", display: "flex", alignItems: "center", gap: "5px"
          }}
        >
          <Lock size={12} /> Officer Login
        </button>
      )}

      {/* Login Dialog */}
      {isOpen && (
        <div
          style={{
            position: "fixed", inset: 0, background: "rgba(0,0,0,0.8)", zIndex: 9999,
            display: "grid", placeItems: "center", padding: "20px"
          }}
          onClick={() => setIsOpen(false)}
        >
          <div
            style={{
              width: "100%", maxWidth: "420px", background: "#04192c",
              border: "1px solid var(--border)", borderRadius: "10px", padding: "24px",
              boxShadow: "0 12px 35px rgba(2,14,26,0.8)",
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "16px" }}>
              <div style={{ width: "36px", height: "36px", borderRadius: "8px", background: "rgba(22,185,201,0.15)", display: "grid", placeItems: "center", color: "var(--cyan)" }}>
                <Lock size={18} />
              </div>
              <div>
                <h3 style={{ margin: 0, fontSize: "15px" }}>Officer & Command Authentication</h3>
                <span style={{ fontSize: "11px", color: "var(--muted)" }}>IBVAP Restricted Operational Access</span>
              </div>
            </div>

            {error && (
              <div style={{ padding: "8px 12px", background: "rgba(239,75,95,0.15)", border: "1px solid var(--red)", color: "var(--red)", borderRadius: "6px", fontSize: "12px", marginBottom: "14px", display: "flex", alignItems: "center", gap: "6px" }}>
                <AlertCircle size={14} /> {error}
              </div>
            )}

            <form onSubmit={handleLogin} style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
              <div>
                <label style={{ fontSize: "11px", color: "#b5cde4", display: "block", marginBottom: "4px" }}>
                  Officer Username / Call-Sign
                </label>
                <input
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  required
                  style={{ width: "100%", padding: "8px 12px", background: "#020e1a", border: "1px solid var(--border)", borderRadius: "6px", color: "#fff", fontSize: "12px" }}
                />
              </div>

              <div>
                <label style={{ fontSize: "11px", color: "#b5cde4", display: "block", marginBottom: "4px" }}>
                  Secure Password
                </label>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  style={{ width: "100%", padding: "8px 12px", background: "#020e1a", border: "1px solid var(--border)", borderRadius: "6px", color: "#fff", fontSize: "12px" }}
                />
              </div>

              <div style={{ background: "#020e1a", border: "1px solid var(--border)", borderRadius: "6px", padding: "8px 10px", fontSize: "10px", color: "var(--muted)" }}>
                Tactical Roles: <strong style={{ color: "var(--cyan)" }}>admin</strong> (admin123) or <strong style={{ color: "var(--cyan)" }}>officer</strong> (officer123).
              </div>

              <div style={{ display: "flex", gap: "8px", marginTop: "6px" }}>
                <button
                  type="button"
                  onClick={() => setIsOpen(false)}
                  style={{ flex: 1, padding: "8px", background: "transparent", border: "1px solid var(--border)", color: "var(--muted)", borderRadius: "6px", fontSize: "12px", cursor: "pointer" }}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={loading}
                  style={{ flex: 1, padding: "8px", background: "var(--cyan)", border: "none", color: "#020e1a", borderRadius: "6px", fontSize: "12px", fontWeight: "700", cursor: "pointer" }}
                >
                  {loading ? "Verifying..." : "Authenticate"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
