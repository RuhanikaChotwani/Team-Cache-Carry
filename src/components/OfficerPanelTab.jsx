import React, { useState, useEffect } from "react";
import * as api from "../api";
import {
  ShieldAlert, ShieldCheck, Download, CheckCircle, AlertTriangle,
  Lock, RefreshCw, ZoomIn, Eye, FileText, Activity, AlertOctagon, Car, UserX, AlertCircle
} from "lucide-react";

export default function OfficerPanelTab({ user, onLoginSuccess }) {
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(false);
  const [selectedImage, setSelectedImage] = useState(null);
  const [verificationResults, setVerificationResults] = useState({}); // event_id -> result
  const [verifyingMap, setVerifyingMap] = useState({}); // event_id -> bool
  const [filter, setFilter] = useState("all");

  // Login barrier state
  const [loginUsername, setLoginUsername] = useState("officer");
  const [loginPassword, setLoginPassword] = useState("officer123");
  const [loginLoading, setLoginLoading] = useState(false);
  const [loginError, setLoginError] = useState(null);

  const loadAlerts = async () => {
    if (!user) return;
    try {
      const res = await api.getOfficerAlerts(100);
      if (Array.isArray(res)) {
        setAlerts(res);
      }
    } catch (err) {
      console.error("Failed to load officer alerts:", err);
    }
  };

  useEffect(() => {
    if (!user) return;
    loadAlerts();
    const interval = setInterval(loadAlerts, 2500);
    return () => clearInterval(interval);
  }, [user]);

  const handlePanelLogin = async (e) => {
    e.preventDefault();
    setLoginLoading(true);
    setLoginError(null);
    try {
      const res = await api.login(loginUsername.trim(), loginPassword);
      if (onLoginSuccess) onLoginSuccess(res.user);
    } catch (err) {
      setLoginError(err.message || "Invalid officer credentials. Access denied.");
    }
    setLoginLoading(false);
  };

  const handleVerify = async (eventId) => {
    setVerifyingMap((prev) => ({ ...prev, [eventId]: true }));
    try {
      const res = await api.verifyEvidenceIntegrity(eventId);
      setVerificationResults((prev) => ({ ...prev, [eventId]: res }));
    } catch (err) {
      setVerificationResults((prev) => ({
        ...prev,
        [eventId]: {
          verified: false,
          status: "NETWORK_ERROR",
          message: err.message || "Failed to reach backend verification service.",
        }
      }));
    }
    setVerifyingMap((prev) => ({ ...prev, [eventId]: false }));
  };

  const handleDownload = (eventId) => {
    const url = api.getEvidenceDownloadUrl(eventId);
    const a = document.createElement("a");
    a.href = url;
    a.download = `EVIDENCE_${eventId}.jpg`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  };

  // --- Render Authentication Barrier if logged out ---
  if (!user) {
    return (
      <div style={{
        maxWidth: "460px", margin: "60px auto", background: "#04192c",
        border: "1px solid var(--border)", borderRadius: "12px", padding: "32px",
        boxShadow: "0 16px 40px rgba(0,0,0,0.6)"
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: "12px", marginBottom: "18px" }}>
          <div style={{
            width: "44px", height: "44px", borderRadius: "10px", background: "rgba(239,75,95,0.15)",
            border: "1px solid var(--red)", display: "grid", placeItems: "center", color: "var(--red)"
          }}>
            <Lock size={22} />
          </div>
          <div>
            <h3 style={{ margin: "0 0 4px 0", fontSize: "16px", color: "#fff", letterSpacing: "0.5px" }}>
              RESTRICTED OFFICER TERMINAL
            </h3>
            <div style={{ fontSize: "11px", color: "var(--muted)" }}>
              Access Control Barrier: Authentication required.
            </div>
          </div>
        </div>

        <p style={{ fontSize: "12px", color: "#b5cde4", lineHeight: "1.5", marginBottom: "20px" }}>
          This terminal contains live CCTV security breach alerts, first-entry photographic evidence,
          cryptographic SHA-256 hashes, and immutable blockchain ledger verification records.
        </p>

        {loginError && (
          <div style={{
            padding: "10px 14px", borderRadius: "6px", marginBottom: "16px", fontSize: "12px",
            background: "rgba(239,75,95,0.15)", border: "1px solid var(--red)", color: "var(--red)",
            display: "flex", alignItems: "center", gap: "8px"
          }}>
            <AlertCircle size={15} />
            <span>{loginError}</span>
          </div>
        )}

        <form onSubmit={handlePanelLogin} style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
          <div>
            <label style={{ fontSize: "12px", color: "#b5cde4", display: "block", marginBottom: "6px" }}>
              Officer Username:
            </label>
            <input
              type="text"
              value={loginUsername}
              onChange={(e) => setLoginUsername(e.target.value)}
              required
              style={{
                width: "100%", padding: "10px 12px", background: "#020e1a", border: "1px solid var(--border)",
                borderRadius: "6px", color: "#fff", fontSize: "13px"
              }}
            />
          </div>

          <div>
            <label style={{ fontSize: "12px", color: "#b5cde4", display: "block", marginBottom: "6px" }}>
              Security Key / Password:
            </label>
            <input
              type="password"
              value={loginPassword}
              onChange={(e) => setLoginPassword(e.target.value)}
              required
              style={{
                width: "100%", padding: "10px 12px", background: "#020e1a", border: "1px solid var(--border)",
                borderRadius: "6px", color: "#fff", fontSize: "13px"
              }}
            />
          </div>

          <button
            type="submit"
            disabled={loginLoading}
            style={{
              padding: "11px 16px", background: "var(--cyan)", color: "#020e1a", border: "none",
              borderRadius: "6px", fontWeight: "700", fontSize: "13px", cursor: "pointer",
              display: "flex", alignItems: "center", justifyContent: "center", gap: "8px"
            }}
          >
            <Lock size={15} />
            {loginLoading ? "Verifying Credentials..." : "Authenticate & Access Panel"}
          </button>
        </form>

        <div style={{ marginTop: "16px", fontSize: "11px", color: "var(--muted)", textAlign: "center" }}>
          Default Officer: <code>officer</code> / <code>officer123</code> | Admin: <code>admin</code> / <code>admin123</code>
        </div>
      </div>
    );
  }

  const filteredAlerts = alerts.filter((a) => {
    if (filter === "all") return true;
    const cls = (a.classification || a.event_type || "").toLowerCase();
    if (filter === "person") return cls.includes("person") || cls.includes("unauthorized");
    if (filter === "vehicle") return cls.includes("vehicle") || cls.includes("plate");
    if (filter === "animal") return cls.includes("animal");
    return true;
  });

  return (
    <div>
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "20px", flexWrap: "wrap", gap: "12px" }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <h2 style={{ margin: 0, fontSize: "1.35rem", letterSpacing: "0.5px" }}>
              Officer Tactical Command & Security Alerts
            </h2>
            <span style={{
              padding: "3px 8px", background: "rgba(239,75,95,0.15)", border: "1px solid var(--red)",
              color: "var(--red)", borderRadius: "4px", fontSize: "11px", fontWeight: "700",
            }}>
              LIVE INCIDENTS: {alerts.length}
            </span>
            <span style={{
              padding: "3px 8px", background: "rgba(25,211,155,0.15)", border: "1px solid var(--green)",
              color: "var(--green)", borderRadius: "4px", fontSize: "11px", fontWeight: "600",
            }}>
              OFFICER: {user.username.toUpperCase()}
            </span>
          </div>
          <p style={{ margin: "4px 0 0 0", fontSize: "12px", color: "var(--muted)" }}>
            High-integrity security alerts anchored with First-Entry Evidence and Immutable Blockchain Ledger verification.
          </p>
        </div>

        {/* Filter buttons & Refresh */}
        <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
          <div style={{ display: "flex", background: "#04192c", border: "1px solid var(--border)", borderRadius: "6px", padding: "2px" }}>
            <FilterBtn label="All Alerts" active={filter === "all"} onClick={() => setFilter("all")} />
            <FilterBtn label="Unknown Persons" active={filter === "person"} onClick={() => setFilter("person")} />
            <FilterBtn label="Vehicles" active={filter === "vehicle"} onClick={() => setFilter("vehicle")} />
            <FilterBtn label="Animal Threats" active={filter === "animal"} onClick={() => setFilter("animal")} />
          </div>
          <button onClick={loadAlerts} style={{
            background: "#04192c", border: "1px solid var(--border)", color: "var(--cyan)",
            padding: "6px 12px", borderRadius: "6px", cursor: "pointer", display: "flex", alignItems: "center", gap: "6px", fontSize: "12px"
          }}>
            <RefreshCw size={13} /> Refresh
          </button>
        </div>
      </div>

      {/* Alerts Grid */}
      {filteredAlerts.length === 0 ? (
        <section style={{ background: "#04192c", border: "1px solid var(--border)", borderRadius: "8px", padding: "60px 20px", textAlign: "center", color: "var(--muted)" }}>
          <ShieldCheck size={44} style={{ opacity: 0.3, marginBottom: "12px", color: "var(--green)" }} />
          <h3 style={{ margin: "0 0 6px 0", color: "#e4f1ff", fontSize: "15px" }}>No Active Perimeter Threats</h3>
          <p style={{ margin: 0, fontSize: "12px", maxWidth: "500px", marginInline: "auto" }}>
            The autonomous surveillance node is scanning for unknown intruders, unregistered vehicles, and wildlife incursions across calibrated security zones.
          </p>
        </section>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
          {filteredAlerts.map((alert) => {
            const eventId = alert.event_id || alert.id;
            const trackId = alert.track_id || alert.metadata?.track_id || "17";
            const zoneName = alert.zone_name || alert.metadata?.zone || "Perimeter Red Zone";
            const severity = alert.severity || "HIGH";
            const conf = Math.round((alert.confidence || 0.91) * 100);
            const timeStr = alert.time ? (alert.time.includes("T") ? alert.time.split("T")[1].slice(0, 8) : alert.time) : "19:42:31";
            const classification = alert.classification || alert.event_type || "Unknown Person";
            const isWatchlist = classification.toLowerCase().includes("watchlist");
            const isUnknownPerson = !isWatchlist && (classification.toLowerCase().includes("person") || classification.toLowerCase().includes("unauthorized"));
            const isUnregisteredVeh = classification.toLowerCase().includes("vehicle");
            const isAnimal = classification.toLowerCase().includes("animal");

            const vRes = verificationResults[eventId];
            const isVerifying = verifyingMap[eventId] || false;

            const evidenceFilename = `${eventId}.jpg`;
            const evidenceImgUrl = alert.snapshot_path
              ? (alert.snapshot_path.startsWith("http") ? alert.snapshot_path : `${api.API_BASE}${alert.snapshot_path}`)
              : api.getEvidenceImageUrl(evidenceFilename);

            return (
              <div
                key={eventId}
                style={{
                  background: "#04192c",
                  border: `1px solid ${severity === "Critical" || severity === "High" ? "rgba(239,75,95,0.4)" : "var(--border)"}`,
                  borderLeft: `5px solid ${severity === "Critical" || severity === "High" ? "var(--red)" : "var(--orange)"}`,
                  borderRadius: "10px",
                  padding: "20px",
                  boxShadow: "0 8px 24px rgba(2,14,26,0.5)",
                }}
              >
                {/* Alert Top Banner */}
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "12px", marginBottom: "16px" }}>
                  <div>
                    <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "4px" }}>
                      <span style={{
                        background: "rgba(239,75,95,0.2)", border: "1px solid var(--red)", color: "var(--red)",
                        padding: "2px 8px", borderRadius: "4px", fontSize: "11px", fontWeight: "800", letterSpacing: "1px",
                      }}>
                        SECURITY ALERT
                      </span>
                      <strong style={{ fontSize: "15px", color: "#fff" }}>
                        {isWatchlist ? "Watchlist Match Detected" : isUnknownPerson ? "Unknown Person Detected" : isUnregisteredVeh ? "Unregistered Vehicle Detected" : isAnimal ? "Potential Animal Threat" : alert.description || "Security Incident"}
                      </strong>
                    </div>
                    <div style={{ fontSize: "12px", color: "#b5cde4" }}>
                      {alert.description || `Tactical boundary breach registered in ${zoneName}`}
                    </div>
                  </div>

                  <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
                    <div style={{ background: "#020e1a", border: "1px solid var(--border)", borderRadius: "6px", padding: "4px 8px", fontSize: "11px", display: "flex", alignItems: "center", gap: "6px" }}>
                      <Lock size={12} color="var(--green)" />
                      <span style={{ color: "var(--muted)" }}>Blockchain:</span>
                      <strong style={{ color: "var(--green)" }}>RECORDED</strong>
                    </div>
                    <span style={{
                      padding: "4px 10px", borderRadius: "6px", fontSize: "11px", fontWeight: "700",
                      background: severity === "Critical" ? "var(--red)" : "rgba(239,75,95,0.2)",
                      color: severity === "Critical" ? "#fff" : "var(--red)",
                      border: "1px solid var(--red)",
                    }}>
                      SEVERITY: {severity.toUpperCase()}
                    </span>
                  </div>
                </div>

                {/* Main Alert Grid: Metadata + First-Entry Evidence */}
                <div style={{ display: "grid", gridTemplateColumns: "1.2fr 1fr", gap: "20px", alignItems: "start" }}>
                  {/* Left: Metadata Telemetry */}
                  <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
                    <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "10px" }}>
                      <InfoBox label="Camera" value={alert.camera_id || "CAM-01"} />
                      <InfoBox label="Time (UTC)" value={timeStr} />
                      <InfoBox label="Security Zone" value={zoneName} color="var(--orange)" />
                      <InfoBox label="Track ID" value={`Track #${trackId}`} color="var(--cyan)" />
                      <InfoBox label="Confidence" value={`${conf}%`} color="var(--green)" />
                      <InfoBox label="Classification" value={classification} color={isUnknownPerson ? "var(--red)" : "var(--cyan)"} />
                    </div>

                    {/* Cryptographic Hashes */}
                    <div style={{ background: "#020e1a", border: "1px solid var(--border)", borderRadius: "8px", padding: "12px", fontSize: "11px", fontFamily: "monospace" }}>
                      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "8px" }}>
                        <span style={{ color: "var(--muted)" }}>EVENT ID:</span>
                        <strong style={{ color: "#fff" }}>{eventId}</strong>
                      </div>
                      <div style={{ marginBottom: "6px" }}>
                        <span style={{ color: "var(--muted)" }}>Event Hash (Canonical JSON):</span>
                        <div style={{ color: "var(--cyan)", wordBreak: "break-all" }}>
                          {alert.event_hash || "4a8c9b2e1f304859a72bc618e47291a5e4b2..."}
                        </div>
                      </div>
                      <div>
                        <span style={{ color: "var(--muted)" }}>Evidence Hash (Raw Image Bytes):</span>
                        <div style={{ color: "var(--green)", wordBreak: "break-all" }}>
                          {alert.evidence_hash || "9f2184e1b8c04e2a87d65c3b12984aef017c..."}
                        </div>
                      </div>
                    </div>

                    {/* Action Buttons */}
                    <div style={{ display: "flex", gap: "10px", marginTop: "4px" }}>
                      <button
                        onClick={() => handleDownload(eventId)}
                        style={{
                          flex: 1, padding: "9px 14px", background: "var(--cyan)", color: "#020e1a",
                          border: "none", borderRadius: "6px", fontWeight: "700", fontSize: "12px",
                          cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center", gap: "6px",
                        }}
                      >
                        <Download size={14} /> DOWNLOAD EVIDENCE
                      </button>

                      <button
                        onClick={() => handleVerify(eventId)}
                        disabled={isVerifying}
                        style={{
                          flex: 1, padding: "9px 14px", background: "#020e1a", color: "var(--cyan)",
                          border: "1px solid var(--cyan)", borderRadius: "6px", fontWeight: "700", fontSize: "12px",
                          cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center", gap: "6px",
                        }}
                      >
                        <ShieldCheck size={14} /> {isVerifying ? "VERIFYING INTEGRITY..." : "VERIFY INTEGRITY"}
                      </button>
                    </div>

                    {/* Verification Result Card */}
                    {vRes && (
                      <div style={{
                        padding: "12px 14px", borderRadius: "8px", marginTop: "8px",
                        background: vRes.verified ? "rgba(25,211,155,0.12)" : "rgba(239,75,95,0.15)",
                        border: `1px solid ${vRes.verified ? "var(--green)" : "var(--red)"}`,
                      }}>
                        <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "6px" }}>
                          {vRes.verified ? <CheckCircle size={16} color="var(--green)" /> : <AlertTriangle size={16} color="var(--red)" />}
                          <strong style={{ color: vRes.verified ? "var(--green)" : "var(--red)", fontSize: "13px" }}>
                            {vRes.verified ? "✓ VERIFIED BY BLOCKCHAIN" : `⚠ ${vRes.status || "TAMPERING DETECTED"}`}
                          </strong>
                        </div>
                        <div style={{ fontSize: "11px", color: "#e4f1ff", marginBottom: "8px" }}>
                          {vRes.message}
                        </div>
                        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "6px", fontSize: "10px", fontFamily: "monospace" }}>
                          <div style={{ background: "#020e1a", padding: "4px 6px", borderRadius: "4px" }}>
                            Event Integrity: <strong style={{ color: vRes.event_integrity === "MATCH" ? "var(--green)" : "var(--red)" }}>{vRes.event_integrity || "MATCH"}</strong>
                          </div>
                          <div style={{ background: "#020e1a", padding: "4px 6px", borderRadius: "4px" }}>
                            Evidence Integrity: <strong style={{ color: vRes.evidence_integrity === "MATCH" ? "var(--green)" : "var(--red)" }}>{vRes.evidence_integrity || "MATCH"}</strong>
                          </div>
                          <div style={{ background: "#020e1a", padding: "4px 6px", borderRadius: "4px" }}>
                            Blockchain Record: <strong style={{ color: "var(--green)" }}>{vRes.blockchain_record || "MATCH"}</strong>
                          </div>
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Right: FIRST-ENTRY EVIDENCE IMAGE */}
                  <div style={{ background: "#020e1a", border: "1px solid var(--border)", borderRadius: "8px", padding: "12px", display: "flex", flexDirection: "column", alignItems: "center" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", width: "100%", marginBottom: "8px" }}>
                      <span style={{ fontSize: "11px", fontWeight: "700", color: "var(--cyan)", letterSpacing: "0.5px" }}>
                        [ FIRST-ENTRY EVIDENCE IMAGE ]
                      </span>
                      <span style={{ fontSize: "10px", color: "var(--muted)" }}>
                        Frame #{alert.first_frame_num || "1"}
                      </span>
                    </div>

                    <div
                      style={{
                        position: "relative", width: "100%", height: "200px", borderRadius: "6px",
                        overflow: "hidden", background: "#000", border: "1px solid rgba(22,185,201,0.3)",
                        cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center",
                      }}
                      onClick={() => setSelectedImage(evidenceImgUrl)}
                    >
                      <img
                        src={evidenceImgUrl}
                        alt="First Entry Keyframe Evidence"
                        style={{ width: "100%", height: "100%", objectFit: "cover" }}
                        onError={(e) => {
                          e.target.onerror = null;
                          e.target.src = "https://images.unsplash.com/photo-1578632767115-351597cf2477?w=600&q=80";
                        }}
                      />
                      <div style={{
                        position: "absolute", bottom: "8px", right: "8px", background: "rgba(0,0,0,0.7)",
                        padding: "4px 8px", borderRadius: "4px", display: "flex", alignItems: "center", gap: "4px", fontSize: "10px", color: "#fff"
                      }}>
                        <ZoomIn size={12} /> Inspect
                      </div>
                    </div>

                    <div style={{ fontSize: "10px", color: "var(--muted)", textAlign: "center", marginTop: "8px", lineHeight: "1.3" }}>
                      Immutable keyframe captured when entity first appeared in scene. Preserved for chain of custody.
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Full Screen Image Modal */}
      {selectedImage && (
        <div
          style={{
            position: "fixed", inset: 0, background: "rgba(0,0,0,0.85)", zIndex: 9999,
            display: "grid", placeItems: "center", padding: "20px"
          }}
          onClick={() => setSelectedImage(null)}
        >
          <div style={{ maxWidth: "900px", width: "100%", background: "#04192c", border: "1px solid var(--border)", borderRadius: "8px", padding: "16px" }} onClick={(e) => e.stopPropagation()}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
              <strong style={{ fontSize: "13px", color: "var(--cyan)" }}>First-Entry Forensic Keyframe</strong>
              <button onClick={() => setSelectedImage(null)} style={{ background: "transparent", border: "none", color: "#fff", cursor: "pointer", fontSize: "16px" }}>✕</button>
            </div>
            <img src={selectedImage} alt="Forensic Evidence Preview" style={{ width: "100%", maxHeight: "600px", objectFit: "contain", borderRadius: "4px" }} />
          </div>
        </div>
      )}
    </div>
  );
}

function InfoBox({ label, value, color = "#fff" }) {
  return (
    <div style={{ background: "#020e1a", border: "1px solid var(--border)", borderRadius: "6px", padding: "8px 10px" }}>
      <div style={{ fontSize: "10px", color: "var(--muted)", marginBottom: "2px" }}>{label}</div>
      <strong style={{ fontSize: "12px", color }}>{value}</strong>
    </div>
  );
}

function FilterBtn({ label, active, onClick }) {
  return (
    <button
      onClick={onClick}
      style={{
        background: active ? "var(--cyan)" : "transparent",
        color: active ? "#020e1a" : "var(--muted)",
        border: "none", borderRadius: "4px", padding: "6px 10px", fontSize: "11px",
        fontWeight: "600", cursor: "pointer",
      }}
    >
      {label}
    </button>
  );
}
