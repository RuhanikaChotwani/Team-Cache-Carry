import React, { useState, useEffect, useRef } from "react";
import * as api from "../api";
import {
  UserRound, Upload, Check, X, RefreshCw, Trash2,
  ShieldCheck, Car, UserCheck, ShieldAlert, Plus, AlertCircle, Camera, Layers
} from "lucide-react";

export default function WatchlistTab({ user }) {
  const [activeSection, setActiveSection] = useState("watchlist"); // "watchlist" or "authorized"
  const [authorizedSubSection, setAuthorizedSubSection] = useState("personnel"); // "personnel" or "vehicles"

  // Persons of Interest state
  const [watchlist, setWatchlist] = useState([]);
  const [poiName, setPoiName] = useState("");
  const [poiCategory, setPoiCategory] = useState("Person of Interest");
  const [poiImage, setPoiImage] = useState(null);
  const [poiLeftImage, setPoiLeftImage] = useState(null);
  const [poiRightImage, setPoiRightImage] = useState(null);
  const [poiUploading, setPoiUploading] = useState(false);
  const [poiMessage, setPoiMessage] = useState(null);
  const poiFileRef = useRef(null);
  const poiLeftFileRef = useRef(null);
  const poiRightFileRef = useRef(null);

  // Registered Personnel state
  const [personnelList, setPersonnelList] = useState([]);
  const [personName, setPersonName] = useState("");
  const [personRole, setPersonRole] = useState("Security Officer");
  const [personBadge, setPersonBadge] = useState("");
  const [personDept, setPersonDept] = useState("Border Security Force");
  const [personMessage, setPersonMessage] = useState(null);
  const [personUploading, setPersonUploading] = useState(false);

  // Authorized Personnel Face Biometrics state
  const [authFaces, setAuthFaces] = useState([]);
  const [authFrontImage, setAuthFrontImage] = useState(null);
  const [authLeftImage, setAuthLeftImage] = useState(null);
  const [authRightImage, setAuthRightImage] = useState(null);
  const authFrontFileRef = useRef(null);
  const authLeftFileRef = useRef(null);
  const authRightFileRef = useRef(null);

  // Update Face Profile modal state
  const [updatingPerson, setUpdatingPerson] = useState(null);
  const [updateFrontImage, setUpdateFrontImage] = useState(null);
  const [updateLeftImage, setUpdateLeftImage] = useState(null);
  const [updateRightImage, setUpdateRightImage] = useState(null);
  const [updateUploading, setUpdateUploading] = useState(false);
  const [updateMessage, setUpdateMessage] = useState(null);
  const updateFrontFileRef = useRef(null);
  const updateLeftFileRef = useRef(null);
  const updateRightFileRef = useRef(null);

  // Authorized Vehicles state
  const [vehiclesList, setVehiclesList] = useState([]);
  const [vehiclePlate, setVehiclePlate] = useState("");
  const [vehicleType, setVehicleType] = useState("Patrol SUV");
  const [vehicleOwner, setVehicleOwner] = useState("");
  const [vehicleAuthBy, setVehicleAuthBy] = useState("Sector Command");
  const [vehicleMessage, setVehicleMessage] = useState(null);

  const loadAll = () => {
    api.getWatchlist().then((w) => Array.isArray(w) && setWatchlist(w));
    api.getAuthorizedPersonnel().then((p) => Array.isArray(p) && setPersonnelList(p));
    api.getAuthorizedVehicles().then((v) => Array.isArray(v) && setVehiclesList(v));
    api.getAuthorizedFaces().then((f) => Array.isArray(f) && setAuthFaces(f));
  };

  useEffect(() => {
    loadAll();
  }, []);

  // --- Handlers for Persons of Interest ---
  const handleEnrollPoi = async (e) => {
    e.preventDefault();
    if (!poiName.trim() || !poiImage) {
      setPoiMessage({ type: "error", text: "Target name and front-facing photo (Required) are needed." });
      return;
    }

    setPoiUploading(true);
    setPoiMessage(null);

    try {
      const res = await api.enrollFace(poiName.trim(), poiImage, poiLeftImage, poiRightImage);
      const angleCount = res.embedding_count || 1;
      setPoiMessage({
        type: "success",
        text: `Target "${res.name}" enrolled on Watchlist (${angleCount} reference angle${angleCount > 1 ? "s" : ""}). Confidence: ${Math.round(res.confidence * 100)}%`
      });
      setPoiName("");
      setPoiImage(null);
      setPoiLeftImage(null);
      setPoiRightImage(null);
      if (poiFileRef.current) poiFileRef.current.value = "";
      if (poiLeftFileRef.current) poiLeftFileRef.current.value = "";
      if (poiRightFileRef.current) poiRightFileRef.current.value = "";
      loadAll();
    } catch (err) {
      setPoiMessage({ type: "error", text: err.message || "Failed to enroll face to watchlist." });
    }
    setPoiUploading(false);
  };

  const handleDeletePoi = async (faceId) => {
    if (confirm("Remove this individual from Persons of Interest?")) {
      try {
        await api.deleteWatchlistFace(faceId);
        loadAll();
      } catch (err) {
        alert(err.message || "Failed to remove person.");
      }
    }
  };

  // --- Handlers for Authorized Personnel Registration (Metadata + Face Enrollment) ---
  const handleRegisterPersonnel = async (e) => {
    e.preventDefault();
    if (!personName.trim()) {
      setPersonMessage({ type: "error", text: "Personnel Full Name & Rank is required." });
      return;
    }
    if (!personRole.trim()) {
      setPersonMessage({ type: "error", text: "Role / Duty Type is required." });
      return;
    }
    if (!personBadge.trim()) {
      setPersonMessage({ type: "error", text: "Badge / Service ID is required." });
      return;
    }
    if (!personDept.trim()) {
      setPersonMessage({ type: "error", text: "Department / Battalion is required." });
      return;
    }
    if (!authFrontImage) {
      setPersonMessage({ type: "error", text: "Front Face Photo (Required) is mandatory for face enrollment." });
      return;
    }

    setPersonUploading(true);
    setPersonMessage(null);

    try {
      const res = await api.enrollAuthorizedFace(
        {
          name: personName.trim(),
          role_type: personRole.trim(),
          badge_id: personBadge.trim(),
          department: personDept.trim(),
        },
        authFrontImage,
        authLeftImage,
        authRightImage
      );

      const angleCount = res.embedding_count || 1;
      setPersonMessage({
        type: "success",
        text: `Authorized personnel "${res.name}" registered and enrolled with face profile (${angleCount} reference angle${angleCount > 1 ? "s" : ""}). Recognized as Authorized Person.`
      });
      setPersonName("");
      setPersonBadge("");
      setPersonRole("Security Officer");
      setPersonDept("Border Security Force");
      setAuthFrontImage(null);
      setAuthLeftImage(null);
      setAuthRightImage(null);
      if (authFrontFileRef.current) authFrontFileRef.current.value = "";
      if (authLeftFileRef.current) authLeftFileRef.current.value = "";
      if (authRightFileRef.current) authRightFileRef.current.value = "";
      loadAll();
    } catch (err) {
      setPersonMessage({ type: "error", text: err.message || "Failed to register authorized personnel." });
    }
    setPersonUploading(false);
  };

  // --- Handlers for Updating Existing Personnel Face Profile ---
  const handleOpenUpdateFace = (person) => {
    setUpdatingPerson(person);
    setUpdateFrontImage(null);
    setUpdateLeftImage(null);
    setUpdateRightImage(null);
    setUpdateMessage(null);
  };

  const handleCloseUpdateFace = () => {
    setUpdatingPerson(null);
    setUpdateFrontImage(null);
    setUpdateLeftImage(null);
    setUpdateRightImage(null);
    setUpdateMessage(null);
    if (updateFrontFileRef.current) updateFrontFileRef.current.value = "";
    if (updateLeftFileRef.current) updateLeftFileRef.current.value = "";
    if (updateRightFileRef.current) updateRightFileRef.current.value = "";
  };

  const handleUpdateFaceSubmit = async (e) => {
    e.preventDefault();
    if (!updatingPerson) return;
    if (!updateFrontImage) {
      setUpdateMessage({ type: "error", text: "Front Face Photo (Required) is mandatory to update face profile." });
      return;
    }

    setUpdateUploading(true);
    setUpdateMessage(null);

    try {
      const res = await api.updateAuthorizedFace(
        updatingPerson.id,
        updateFrontImage,
        updateLeftImage,
        updateRightImage
      );
      const angleCount = res.embedding_count || 1;
      setPersonMessage({
        type: "success",
        text: `Face profile updated for "${updatingPerson.name}" (${angleCount} reference angle${angleCount > 1 ? "s" : ""}).`,
      });
      handleCloseUpdateFace();
      loadAll();
    } catch (err) {
      setUpdateMessage({ type: "error", text: err.message || "Failed to update face profile." });
    }
    setUpdateUploading(false);
  };

  const handleDeleteAuthFace = async (faceId) => {
    if (confirm("Remove biometric face record for this authorized person?")) {
      try {
        await api.deleteAuthorizedFace(faceId);
        loadAll();
      } catch (err) {
        alert(err.message || "Failed to delete authorized face record.");
      }
    }
  };

  const handleDeletePersonnel = async (personId) => {
    if (confirm("Revoke authorization for this personnel?")) {
      try {
        await api.deleteAuthorizedPersonnel(personId);
        loadAll();
      } catch (err) {
        alert(err.message || "Failed to delete personnel.");
      }
    }
  };

  // --- Handlers for Authorized Vehicles ---
  const handleAddVehicle = async (e) => {
    e.preventDefault();
    const cleanPlate = vehiclePlate.trim().toUpperCase().replace(/[^A-Z0-9]/g, "");
    if (!cleanPlate) {
      setVehicleMessage({ type: "error", text: "Valid license plate number is required." });
      return;
    }
    setVehicleMessage(null);

    try {
      await api.addAuthorizedVehicle({
        plate_number: cleanPlate,
        vehicle_type: vehicleType,
        owner_name: vehicleOwner.trim() || "Station Depot / Border Patrol",
        authorized_by: vehicleAuthBy.trim() || "Sector Command",
      });
      setVehicleMessage({ type: "success", text: `Vehicle "${cleanPlate}" added to authorized registry.` });
      setVehiclePlate("");
      setVehicleOwner("");
      loadAll();
    } catch (err) {
      setVehicleMessage({ type: "error", text: err.message || "Failed to authorize vehicle." });
    }
  };

  const handleDeleteVehicle = async (plateNumber) => {
    if (confirm(`Remove vehicle plate ${plateNumber} from authorized registry?`)) {
      try {
        await api.deleteAuthorizedVehicle(plateNumber);
        loadAll();
      } catch (err) {
        alert(err.message || "Failed to delete vehicle.");
      }
    }
  };

  return (
    <div>
      {/* Top Header & Two-Concept Section Toggle */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "20px", flexWrap: "wrap", gap: "16px" }}>
        <div>
          <h2 style={{ margin: "0 0 4px 0", fontSize: "1.35rem", letterSpacing: "0.5px" }}>
            Identity & Authorization Registry
          </h2>
          <p style={{ margin: 0, fontSize: "12px", color: "var(--muted)" }}>
            Segregated management of Persons of Interest (Watchlist) vs Registered Personnel & Authorized Vehicles.
          </p>
        </div>

        {/* PRIMARY TWO-CONCEPT TABS */}
        <div style={{
          display: "flex", background: "#04192c", padding: "4px", borderRadius: "8px",
          border: "1px solid var(--border)", gap: "4px"
        }}>
          <button
            type="button"
            onClick={() => setActiveSection("watchlist")}
            style={{
              padding: "8px 18px", fontSize: "12px", fontWeight: "700", borderRadius: "6px", cursor: "pointer",
              display: "flex", alignItems: "center", gap: "8px", border: "none",
              background: activeSection === "watchlist" ? "rgba(239,75,95,0.25)" : "transparent",
              color: activeSection === "watchlist" ? "var(--red)" : "var(--muted)",
              borderBottom: activeSection === "watchlist" ? "2px solid var(--red)" : "none",
            }}
          >
            <ShieldAlert size={14} /> Persons of Interest ({watchlist.length})
          </button>
          <button
            type="button"
            onClick={() => setActiveSection("authorized")}
            style={{
              padding: "8px 18px", fontSize: "12px", fontWeight: "700", borderRadius: "6px", cursor: "pointer",
              display: "flex", alignItems: "center", gap: "8px", border: "none",
              background: activeSection === "authorized" ? "rgba(25,211,155,0.2)" : "transparent",
              color: activeSection === "authorized" ? "var(--green)" : "var(--muted)",
              borderBottom: activeSection === "authorized" ? "2px solid var(--green)" : "none",
            }}
          >
            <ShieldCheck size={14} /> Registered / Authorized ({personnelList.length + vehiclesList.length})
          </button>
        </div>
      </div>

      {/* ========================================================================= */}
      {/* CONCEPT A: PERSONS OF INTEREST / WATCHLIST */}
      {/* ========================================================================= */}
      {activeSection === "watchlist" && (
        <div>
          <div style={{
            background: "rgba(239,75,95,0.08)", border: "1px solid rgba(239,75,95,0.25)", borderRadius: "8px",
            padding: "12px 16px", marginBottom: "20px", display: "flex", alignItems: "center", gap: "10px", fontSize: "12px", color: "#f87171"
          }}>
            <ShieldAlert size={18} />
            <span>
              <strong>Persons of Interest Watchlist:</strong> Matches against this list trigger high-priority security alerts,
              lock first-entry evidence, and generate tamper-proof blockchain incident records.
            </span>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1.6fr", gap: "20px" }}>
            {/* ENROLL POI FORM */}
            <section style={{ background: "#04192c", border: "1px solid var(--border)", borderRadius: "8px", padding: "20px" }}>
              <h3 style={{ margin: "0 0 14px 0", fontSize: "14px", display: "flex", alignItems: "center", gap: "8px" }}>
                <Plus size={15} color="var(--red)" /> Enroll Person of Interest
              </h3>

              {poiMessage && (
                <div style={{
                  padding: "10px 14px", borderRadius: "6px", marginBottom: "16px", fontSize: "12px",
                  display: "flex", alignItems: "center", gap: "8px",
                  background: poiMessage.type === "success" ? "rgba(25,211,155,0.15)" : "rgba(239,75,95,0.15)",
                  border: `1px solid ${poiMessage.type === "success" ? "var(--green)" : "var(--red)"}`,
                  color: poiMessage.type === "success" ? "var(--green)" : "var(--red)"
                }}>
                  {poiMessage.type === "success" ? <Check size={16} /> : <X size={16} />}
                  <span>{poiMessage.text}</span>
                </div>
              )}

              <form onSubmit={handleEnrollPoi} style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
                <div>
                  <label style={{ fontSize: "12px", color: "#b5cde4", display: "block", marginBottom: "6px" }}>
                    Full Name / Alias:
                  </label>
                  <input
                    type="text"
                    placeholder="e.g. Tariq Mehmood, Subject #304"
                    value={poiName}
                    onChange={(e) => setPoiName(e.target.value)}
                    required
                    style={{
                      width: "100%", padding: "10px 12px", background: "#020e1a", border: "1px solid var(--border)",
                      borderRadius: "6px", color: "#fff", fontSize: "13px"
                    }}
                  />
                </div>

                <div>
                  <label style={{ fontSize: "12px", color: "#b5cde4", display: "block", marginBottom: "6px" }}>
                    Watchlist Classification:
                  </label>
                  <select
                    value={poiCategory}
                    onChange={(e) => setPoiCategory(e.target.value)}
                    style={{
                      width: "100%", padding: "10px 12px", background: "#020e1a", border: "1px solid var(--border)",
                      borderRadius: "6px", color: "#fff", fontSize: "13px"
                    }}
                  >
                    <option value="Person of Interest">Person of Interest</option>
                    <option value="Watchlisted Person">Watchlisted Individual</option>
                    <option value="Potential Threat">Potential Threat / Infiltrator</option>
                  </select>
                </div>

                <div>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "6px" }}>
                    <label style={{ fontSize: "12px", color: "#b5cde4" }}>
                      Front-Facing Photo (JPG/PNG):
                    </label>
                    <span style={{ fontSize: "10px", fontWeight: "700", padding: "1px 6px", borderRadius: "3px", background: "rgba(239,75,95,0.2)", color: "var(--red)" }}>
                      REQUIRED
                    </span>
                  </div>
                  <input
                    type="file"
                    accept="image/*"
                    ref={poiFileRef}
                    onChange={(e) => setPoiImage(e.target.files[0])}
                    required
                    style={{
                      width: "100%", padding: "8px", background: "#020e1a", border: "1px solid var(--border)",
                      borderRadius: "6px", color: "#b5cde4", fontSize: "12px"
                    }}
                  />
                </div>

                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px" }}>
                  <div>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "6px" }}>
                      <label style={{ fontSize: "11px", color: "#b5cde4" }}>
                        Left Profile:
                      </label>
                      <span style={{ fontSize: "9px", fontWeight: "600", padding: "1px 5px", borderRadius: "3px", background: "rgba(22,185,201,0.15)", color: "var(--cyan)" }}>
                        OPTIONAL
                      </span>
                    </div>
                    <input
                      type="file"
                      accept="image/*"
                      ref={poiLeftFileRef}
                      onChange={(e) => setPoiLeftImage(e.target.files[0])}
                      style={{
                        width: "100%", padding: "6px", background: "#020e1a", border: "1px solid var(--border)",
                        borderRadius: "6px", color: "#b5cde4", fontSize: "11px"
                      }}
                    />
                  </div>

                  <div>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "6px" }}>
                      <label style={{ fontSize: "11px", color: "#b5cde4" }}>
                        Right Profile:
                      </label>
                      <span style={{ fontSize: "9px", fontWeight: "600", padding: "1px 5px", borderRadius: "3px", background: "rgba(22,185,201,0.15)", color: "var(--cyan)" }}>
                        OPTIONAL
                      </span>
                    </div>
                    <input
                      type="file"
                      accept="image/*"
                      ref={poiRightFileRef}
                      onChange={(e) => setPoiRightImage(e.target.files[0])}
                      style={{
                        width: "100%", padding: "6px", background: "#020e1a", border: "1px solid var(--border)",
                        borderRadius: "6px", color: "#b5cde4", fontSize: "11px"
                      }}
                    />
                  </div>
                </div>
                <span style={{ fontSize: "11px", color: "var(--muted)", marginTop: "2px", display: "block" }}>
                  Front-facing photo is required. Left and right profiles are optional pose references to improve recognition across varying camera angles.
                </span>

                <button
                  type="submit"
                  disabled={poiUploading}
                  style={{
                    padding: "10px 16px", background: "var(--red)", color: "#fff", border: "none",
                    borderRadius: "6px", fontWeight: "700", fontSize: "13px", cursor: "pointer",
                    display: "flex", alignItems: "center", justifyContent: "center", gap: "8px"
                  }}
                >
                  <Upload size={16} />
                  {poiUploading ? "Enrolling Biometric Signature..." : "Enroll to Watchlist"}
                </button>
              </form>
            </section>

            {/* ENROLLED WATCHLIST TABLE */}
            <section style={{ background: "#04192c", border: "1px solid var(--border)", borderRadius: "8px", padding: "20px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
                <h3 style={{ margin: 0, fontSize: "14px" }}>Monitored Individuals ({watchlist.length})</h3>
                <button onClick={loadAll} style={{ background: "transparent", border: "none", color: "var(--cyan)", cursor: "pointer", fontSize: "11px" }}>
                  <RefreshCw size={11} /> Refresh
                </button>
              </div>

              {watchlist.length === 0 ? (
                <div style={{ textAlign: "center", padding: "50px 20px", color: "var(--muted)" }}>
                  <UserRound size={36} style={{ opacity: 0.3, marginBottom: "10px" }} />
                  <p style={{ margin: 0, fontSize: "13px" }}>No Persons of Interest enrolled.</p>
                  <span style={{ fontSize: "11px" }}>Upload a photograph to begin active biometric tracking.</span>
                </div>
              ) : (
                <div style={{ maxHeight: "420px", overflowY: "auto" }}>
                  <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "12px" }}>
                    <thead>
                      <tr style={{ borderBottom: "1px solid var(--border)", textAlign: "left", color: "var(--muted)" }}>
                        <th style={{ padding: "8px" }}>PHOTO</th>
                        <th style={{ padding: "8px" }}>TARGET NAME</th>
                        <th style={{ padding: "8px" }}>CLASSIFICATION</th>
                        <th style={{ padding: "8px" }}>POSES</th>
                        <th style={{ padding: "8px" }}>FACE ID</th>
                        <th style={{ padding: "8px" }}>DATE</th>
                        <th style={{ padding: "8px" }}>ACTION</th>
                      </tr>
                    </thead>
                    <tbody>
                      {watchlist.map((person) => {
                        const poseCount = person.embeddings?.length || person.embedding_count || 1;
                        return (
                        <tr key={person.id} style={{ borderBottom: "1px solid rgba(18,60,96,0.5)" }}>
                          <td style={{ padding: "8px" }}>
                            {person.thumbnail ? (
                              <img
                                src={`data:image/jpeg;base64,${person.thumbnail}`}
                                alt={person.name}
                                style={{ width: "36px", height: "36px", borderRadius: "4px", objectFit: "cover" }}
                              />
                            ) : (
                              <div style={{ width: "36px", height: "36px", borderRadius: "4px", background: "#020e1a", display: "grid", placeItems: "center" }}>
                                <UserRound size={16} />
                              </div>
                            )}
                          </td>
                          <td style={{ padding: "8px" }}>
                            <strong style={{ color: "#fff" }}>{person.name}</strong>
                          </td>
                          <td style={{ padding: "8px" }}>
                            <span style={{
                              padding: "2px 6px", borderRadius: "4px", fontSize: "10px", fontWeight: "700",
                              background: "rgba(239,75,95,0.15)", color: "var(--red)", border: "1px solid rgba(239,75,95,0.4)"
                            }}>
                              WATCHLIST
                            </span>
                          </td>
                          <td style={{ padding: "8px" }}>
                            <span style={{
                              padding: "2px 6px", borderRadius: "4px", fontSize: "10px", fontWeight: "600",
                              background: poseCount > 1 ? "rgba(22,185,201,0.15)" : "rgba(120,160,190,0.15)",
                              color: poseCount > 1 ? "var(--cyan)" : "var(--muted)"
                            }}>
                              {poseCount > 1 ? `${poseCount} Angles` : "Front"}
                            </span>
                          </td>
                          <td style={{ padding: "8px", fontFamily: "monospace", color: "var(--cyan)" }}>
                            {person.id}
                          </td>
                          <td style={{ padding: "8px", color: "var(--muted)" }}>
                            {(person.created_at || "").slice(0, 10)}
                          </td>
                          <td style={{ padding: "8px" }}>
                            <button
                              onClick={() => handleDeletePoi(person.id)}
                              style={{ background: "transparent", border: "none", color: "var(--red)", cursor: "pointer" }}
                              title="Remove from Watchlist"
                            >
                              <Trash2 size={15} />
                            </button>
                          </td>
                        </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </section>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* CONCEPT B: REGISTERED / AUTHORIZED PERSONNEL & VEHICLES */}
      {/* ========================================================================= */}
      {activeSection === "authorized" && (
        <div>
          {/* Sub-navigation: Personnel vs Vehicles */}
          <div style={{ display: "flex", gap: "10px", marginBottom: "20px" }}>
            <button
              type="button"
              onClick={() => setAuthorizedSubSection("personnel")}
              style={{
                padding: "8px 16px", fontSize: "12px", fontWeight: "700", borderRadius: "6px", cursor: "pointer",
                display: "flex", alignItems: "center", gap: "6px",
                background: authorizedSubSection === "personnel" ? "var(--cyan)" : "#04192c",
                color: authorizedSubSection === "personnel" ? "#020e1a" : "var(--muted)",
                border: "1px solid var(--border)",
              }}
            >
              <UserCheck size={14} /> Registered Personnel ({personnelList.length})
            </button>
            <button
              type="button"
              onClick={() => setAuthorizedSubSection("vehicles")}
              style={{
                padding: "8px 16px", fontSize: "12px", fontWeight: "700", borderRadius: "6px", cursor: "pointer",
                display: "flex", alignItems: "center", gap: "6px",
                background: authorizedSubSection === "vehicles" ? "var(--cyan)" : "#04192c",
                color: authorizedSubSection === "vehicles" ? "#020e1a" : "var(--muted)",
                border: "1px solid var(--border)",
              }}
            >
              <Car size={14} /> Authorized Vehicles ({vehiclesList.length})
            </button>
          </div>

          {/* 1. REGISTERED PERSONNEL SECTION */}
          {authorizedSubSection === "personnel" && (
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1.6fr", gap: "20px" }}>
              <section style={{ background: "#04192c", border: "1px solid var(--border)", borderRadius: "8px", padding: "20px" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "14px" }}>
                  <h3 style={{ margin: 0, fontSize: "14px", display: "flex", alignItems: "center", gap: "8px" }}>
                    <Plus size={15} color="var(--green)" /> Register Authorized Personnel
                  </h3>
                  <span style={{ fontSize: "11px", color: "var(--muted)", background: "rgba(25,211,155,0.1)", padding: "2px 8px", borderRadius: "4px", border: "1px solid rgba(25,211,155,0.25)" }}>
                    Biometric Face Enrollment
                  </span>
                </div>

                {personMessage && (
                  <div style={{
                    padding: "10px 14px", borderRadius: "6px", marginBottom: "16px", fontSize: "12px",
                    display: "flex", alignItems: "center", gap: "8px",
                    background: personMessage.type === "success" ? "rgba(25,211,155,0.15)" : "rgba(239,75,95,0.15)",
                    border: `1px solid ${personMessage.type === "success" ? "var(--green)" : "var(--red)"}`,
                    color: personMessage.type === "success" ? "var(--green)" : "var(--red)"
                  }}>
                    {personMessage.type === "success" ? <Check size={16} /> : <X size={16} />}
                    <span>{personMessage.text}</span>
                  </div>
                )}

                <form onSubmit={handleRegisterPersonnel} style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
                  <div>
                    <label style={{ fontSize: "12px", color: "#b5cde4", display: "block", marginBottom: "6px" }}>
                      Personnel Full Name &amp; Rank:
                    </label>
                    <input
                      type="text"
                      placeholder="e.g. Captain Vikram Singh, Officer Rohan"
                      value={personName}
                      onChange={(e) => setPersonName(e.target.value)}
                      required
                      style={{
                        width: "100%", padding: "10px 12px", background: "#020e1a", border: "1px solid var(--border)",
                        borderRadius: "6px", color: "#fff", fontSize: "13px"
                      }}
                    />
                  </div>

                  <div>
                    <label style={{ fontSize: "12px", color: "#b5cde4", display: "block", marginBottom: "6px" }}>
                      Role / Duty Type:
                    </label>
                    <select
                      value={personRole}
                      onChange={(e) => setPersonRole(e.target.value)}
                      required
                      style={{
                        width: "100%", padding: "10px 12px", background: "#020e1a", border: "1px solid var(--border)",
                        borderRadius: "6px", color: "#fff", fontSize: "13px"
                      }}
                    >
                      <option value="Security Officer">Security Officer</option>
                      <option value="Army Special Forces">Army Special Forces</option>
                      <option value="Border Patrol">Border Patrol Guard</option>
                      <option value="Authorized Inspector">Authorized Inspector</option>
                      <option value="Base Commander">Base Commander</option>
                    </select>
                  </div>

                  <div>
                    <label style={{ fontSize: "12px", color: "#b5cde4", display: "block", marginBottom: "6px" }}>
                      Badge / Service ID:
                    </label>
                    <input
                      type="text"
                      placeholder="e.g. BSF-SEC-4421"
                      value={personBadge}
                      onChange={(e) => setPersonBadge(e.target.value)}
                      required
                      style={{
                        width: "100%", padding: "10px 12px", background: "#020e1a", border: "1px solid var(--border)",
                        borderRadius: "6px", color: "#fff", fontSize: "13px"
                      }}
                    />
                  </div>

                  <div>
                    <label style={{ fontSize: "12px", color: "#b5cde4", display: "block", marginBottom: "6px" }}>
                      Department / Battalion:
                    </label>
                    <input
                      type="text"
                      placeholder="e.g. Border Security Force Sector 4"
                      value={personDept}
                      onChange={(e) => setPersonDept(e.target.value)}
                      required
                      style={{
                        width: "100%", padding: "10px 12px", background: "#020e1a", border: "1px solid var(--border)",
                        borderRadius: "6px", color: "#fff", fontSize: "13px"
                      }}
                    />
                  </div>

                  {/* FACE RECOGNITION PROFILE SECTION */}
                  <div style={{ borderTop: "1px solid var(--border)", paddingTop: "14px", marginTop: "4px" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
                      <span style={{ fontSize: "11px", fontWeight: "700", color: "var(--green)", letterSpacing: "0.5px" }}>
                        FACE RECOGNITION PROFILE
                      </span>
                      <span style={{ fontSize: "10px", color: "var(--muted)" }}>
                        JPG / PNG accepted
                      </span>
                    </div>

                    <div style={{ marginBottom: "12px" }}>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "6px" }}>
                        <label style={{ fontSize: "12px", color: "#b5cde4" }}>
                          Front Face Photo (Required)
                        </label>
                        <span style={{ fontSize: "10px", fontWeight: "700", padding: "1px 6px", borderRadius: "3px", background: "rgba(25,211,155,0.2)", color: "var(--green)" }}>
                          REQUIRED
                        </span>
                      </div>
                      <input
                        type="file"
                        accept=".jpg,.jpeg,.png,image/jpeg,image/png"
                        ref={authFrontFileRef}
                        onChange={(e) => setAuthFrontImage(e.target.files[0])}
                        required
                        style={{
                          width: "100%", padding: "8px", background: "#020e1a", border: "1px solid var(--border)",
                          borderRadius: "6px", color: "#b5cde4", fontSize: "12px"
                        }}
                      />
                    </div>

                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px", marginBottom: "8px" }}>
                      <div>
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "6px" }}>
                          <label style={{ fontSize: "11px", color: "#b5cde4" }}>
                            Left Profile Photo (Optional)
                          </label>
                          <span style={{ fontSize: "9px", fontWeight: "600", padding: "1px 5px", borderRadius: "3px", background: "rgba(22,185,201,0.15)", color: "var(--cyan)" }}>
                            OPTIONAL
                          </span>
                        </div>
                        <input
                          type="file"
                          accept=".jpg,.jpeg,.png,image/jpeg,image/png"
                          ref={authLeftFileRef}
                          onChange={(e) => setAuthLeftImage(e.target.files[0])}
                          style={{
                            width: "100%", padding: "6px", background: "#020e1a", border: "1px solid var(--border)",
                            borderRadius: "6px", color: "#b5cde4", fontSize: "11px"
                          }}
                        />
                      </div>

                      <div>
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "6px" }}>
                          <label style={{ fontSize: "11px", color: "#b5cde4" }}>
                            Right Profile Photo (Optional)
                          </label>
                          <span style={{ fontSize: "9px", fontWeight: "600", padding: "1px 5px", borderRadius: "3px", background: "rgba(22,185,201,0.15)", color: "var(--cyan)" }}>
                            OPTIONAL
                          </span>
                        </div>
                        <input
                          type="file"
                          accept=".jpg,.jpeg,.png,image/jpeg,image/png"
                          ref={authRightFileRef}
                          onChange={(e) => setAuthRightImage(e.target.files[0])}
                          style={{
                            width: "100%", padding: "6px", background: "#020e1a", border: "1px solid var(--border)",
                            borderRadius: "6px", color: "#b5cde4", fontSize: "11px"
                          }}
                        />
                      </div>
                    </div>
                    <span style={{ fontSize: "11px", color: "var(--muted)", marginTop: "2px", display: "block" }}>
                      Enrolling front and side profile images generates 128-d biometric embeddings so live CCTV cameras independently recognize this person as an Authorized Person.
                    </span>
                  </div>

                  <button
                    type="submit"
                    disabled={personUploading}
                    style={{
                      padding: "11px 16px", background: "var(--green)", color: "#020e1a", border: "none",
                      borderRadius: "6px", fontWeight: "700", fontSize: "13px", cursor: "pointer",
                      display: "flex", alignItems: "center", justifyContent: "center", gap: "8px", marginTop: "4px"
                    }}
                  >
                    <UserCheck size={16} />
                    {personUploading ? "Enrolling Biometrics & Registering..." : "Register Authorized Personnel"}
                  </button>
                </form>
              </section>

              <section style={{ background: "#04192c", border: "1px solid var(--border)", borderRadius: "8px", padding: "20px" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
                  <div>
                    <h3 style={{ margin: "0 0 2px 0", fontSize: "14px" }}>
                      Authorized Personnel ({personnelList.length}) | Biometric Faces ({authFaces.length})
                    </h3>
                    <span style={{ fontSize: "11px", color: "var(--muted)" }}>
                      Independent authorized registry compared separately from Persons of Interest.
                    </span>
                  </div>
                  <button onClick={loadAll} style={{ background: "transparent", border: "none", color: "var(--cyan)", cursor: "pointer", fontSize: "11px" }}>
                    <RefreshCw size={11} /> Refresh
                  </button>
                </div>

                <div style={{ maxHeight: "420px", overflowY: "auto" }}>
                  <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "12px" }}>
                    <thead>
                      <tr style={{ borderBottom: "1px solid var(--border)", textAlign: "left", color: "var(--muted)" }}>
                        <th style={{ padding: "8px" }}>PHOTO</th>
                        <th style={{ padding: "8px" }}>NAME &amp; RANK</th>
                        <th style={{ padding: "8px" }}>ROLE</th>
                        <th style={{ padding: "8px" }}>BADGE ID</th>
                        <th style={{ padding: "8px" }}>BIOMETRICS</th>
                        <th style={{ padding: "8px" }}>STATUS</th>
                        <th style={{ padding: "8px" }}>ACTION</th>
                      </tr>
                    </thead>
                    <tbody>
                      {personnelList.map((p) => {
                        const matchedFace = authFaces.find((f) =>
                          (f.name && f.name.toLowerCase() === p.name.toLowerCase()) ||
                          (f.id && p.face_id && f.id === p.face_id)
                        );
                        return (
                        <tr key={p.id} style={{ borderBottom: "1px solid rgba(18,60,96,0.5)" }}>
                          <td style={{ padding: "8px" }}>
                            {matchedFace?.thumbnail ? (
                              <img
                                src={`data:image/jpeg;base64,${matchedFace.thumbnail}`}
                                alt={p.name}
                                style={{ width: "36px", height: "36px", borderRadius: "4px", objectFit: "cover" }}
                              />
                            ) : (
                              <div style={{ width: "36px", height: "36px", borderRadius: "4px", background: "#020e1a", display: "grid", placeItems: "center", color: "var(--muted)" }}>
                                <UserRound size={16} />
                              </div>
                            )}
                          </td>
                          <td style={{ padding: "8px" }}>
                            <strong style={{ color: "#fff" }}>{p.name}</strong>
                          </td>
                          <td style={{ padding: "8px", color: "var(--cyan)" }}>
                            {p.role_type}
                          </td>
                          <td style={{ padding: "8px", fontFamily: "monospace" }}>
                            {p.badge_id || "-"}
                          </td>
                          <td style={{ padding: "8px" }}>
                            {matchedFace ? (
                              <span style={{
                                padding: "2px 6px", borderRadius: "4px", fontSize: "10px", fontWeight: "700",
                                background: "rgba(25,211,155,0.2)", color: "var(--green)", border: "1px solid rgba(25,211,155,0.4)"
                              }}>
                                ACTIVE ({matchedFace.embedding_count || 1} ANGLE{matchedFace.embedding_count > 1 ? "S" : ""})
                              </span>
                            ) : (
                              <span style={{
                                padding: "2px 6px", borderRadius: "4px", fontSize: "10px", fontWeight: "600",
                                background: "rgba(22,185,201,0.1)", color: "var(--muted)"
                              }}>
                                ROSTER ONLY
                              </span>
                            )}
                          </td>
                          <td style={{ padding: "8px" }}>
                            <span style={{
                              padding: "2px 6px", borderRadius: "4px", fontSize: "10px", fontWeight: "700",
                              background: "rgba(25,211,155,0.15)", color: "var(--green)", border: "1px solid rgba(25,211,155,0.4)"
                            }}>
                              AUTHORIZED
                            </span>
                          </td>
                          <td style={{ padding: "8px" }}>
                            <div style={{ display: "flex", gap: "6px", alignItems: "center" }}>
                              <button
                                type="button"
                                onClick={() => handleOpenUpdateFace(p)}
                                style={{
                                  background: "rgba(25,211,155,0.15)",
                                  border: "1px solid rgba(25,211,155,0.35)",
                                  color: "var(--green)",
                                  borderRadius: "4px",
                                  padding: "4px 8px",
                                  fontSize: "11px",
                                  fontWeight: "600",
                                  cursor: "pointer",
                                  display: "flex",
                                  alignItems: "center",
                                  gap: "4px"
                                }}
                                title="Update Face Profile (Front, Left, Right)"
                              >
                                <Camera size={13} /> Update Face Profile
                              </button>
                              {matchedFace && (
                                <button
                                  type="button"
                                  onClick={() => handleDeleteAuthFace(matchedFace.id)}
                                  style={{ background: "transparent", border: "none", color: "var(--orange)", cursor: "pointer", padding: "4px" }}
                                  title="Delete Biometric Face Record"
                                >
                                  <Camera size={14} />
                                </button>
                              )}
                              <button
                                type="button"
                                onClick={() => handleDeletePersonnel(p.id)}
                                style={{ background: "transparent", border: "none", color: "var(--red)", cursor: "pointer", padding: "4px" }}
                                title="Revoke Authorization"
                              >
                                <Trash2 size={15} />
                              </button>
                            </div>
                          </td>
                        </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </section>

              {/* UPDATE FACE PROFILE MODAL */}
              {updatingPerson && (
                <div style={{
                  position: "fixed",
                  top: 0,
                  left: 0,
                  right: 0,
                  bottom: 0,
                  background: "rgba(0, 0, 0, 0.75)",
                  backdropFilter: "blur(4px)",
                  zIndex: 9999,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  padding: "20px"
                }}>
                  <div style={{
                    background: "#04192c",
                    border: "1px solid var(--border)",
                    borderRadius: "10px",
                    width: "100%",
                    maxWidth: "500px",
                    boxShadow: "0 12px 40px rgba(0,0,0,0.7)",
                    overflow: "hidden"
                  }}>
                    <div style={{
                      padding: "16px 20px",
                      borderBottom: "1px solid var(--border)",
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      background: "rgba(25,211,155,0.08)"
                    }}>
                      <div>
                        <h3 style={{ margin: 0, fontSize: "15px", display: "flex", alignItems: "center", gap: "8px", color: "#fff" }}>
                          <Camera size={18} color="var(--green)" /> Update Face Profile
                        </h3>
                        <span style={{ fontSize: "12px", color: "var(--muted)" }}>
                          Enroll / update face biometrics for <strong>{updatingPerson.name}</strong>
                        </span>
                      </div>
                      <button
                        type="button"
                        onClick={handleCloseUpdateFace}
                        style={{ background: "transparent", border: "none", color: "var(--muted)", cursor: "pointer" }}
                      >
                        <X size={18} />
                      </button>
                    </div>

                    <div style={{
                      padding: "10px 20px",
                      background: "#020e1a",
                      borderBottom: "1px solid var(--border)",
                      display: "flex",
                      gap: "16px",
                      fontSize: "11px",
                      color: "#b5cde4"
                    }}>
                      <div><strong>Role:</strong> {updatingPerson.role_type}</div>
                      <div><strong>Badge:</strong> {updatingPerson.badge_id || "-"}</div>
                      <div><strong>Dept:</strong> {updatingPerson.department}</div>
                    </div>

                    <form onSubmit={handleUpdateFaceSubmit} style={{ padding: "20px", display: "flex", flexDirection: "column", gap: "14px" }}>
                      {updateMessage && (
                        <div style={{
                          padding: "8px 12px",
                          borderRadius: "6px",
                          fontSize: "12px",
                          display: "flex",
                          alignItems: "center",
                          gap: "8px",
                          background: updateMessage.type === "success" ? "rgba(25,211,155,0.15)" : "rgba(239,75,95,0.15)",
                          border: `1px solid ${updateMessage.type === "success" ? "var(--green)" : "var(--red)"}`,
                          color: updateMessage.type === "success" ? "var(--green)" : "var(--red)"
                        }}>
                          {updateMessage.type === "success" ? <Check size={16} /> : <X size={16} />}
                          <span>{updateMessage.text}</span>
                        </div>
                      )}

                      <div>
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "6px" }}>
                          <label style={{ fontSize: "12px", color: "#b5cde4", fontWeight: "600" }}>
                            Front Face Photo (Required)
                          </label>
                          <span style={{ fontSize: "10px", fontWeight: "700", padding: "1px 6px", borderRadius: "3px", background: "rgba(25,211,155,0.2)", color: "var(--green)" }}>
                            REQUIRED
                          </span>
                        </div>
                        <input
                          type="file"
                          accept=".jpg,.jpeg,.png,image/jpeg,image/png"
                          ref={updateFrontFileRef}
                          onChange={(e) => setUpdateFrontImage(e.target.files[0])}
                          required
                          style={{
                            width: "100%", padding: "8px", background: "#020e1a", border: "1px solid var(--border)",
                            borderRadius: "6px", color: "#b5cde4", fontSize: "12px"
                          }}
                        />
                      </div>

                      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px" }}>
                        <div>
                          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "6px" }}>
                            <label style={{ fontSize: "11px", color: "#b5cde4" }}>
                              Left Profile Photo (Optional)
                            </label>
                            <span style={{ fontSize: "9px", fontWeight: "600", padding: "1px 5px", borderRadius: "3px", background: "rgba(22,185,201,0.15)", color: "var(--cyan)" }}>
                              OPTIONAL
                            </span>
                          </div>
                          <input
                            type="file"
                            accept=".jpg,.jpeg,.png,image/jpeg,image/png"
                            ref={updateLeftFileRef}
                            onChange={(e) => setUpdateLeftImage(e.target.files[0])}
                            style={{
                              width: "100%", padding: "6px", background: "#020e1a", border: "1px solid var(--border)",
                              borderRadius: "6px", color: "#b5cde4", fontSize: "11px"
                            }}
                          />
                        </div>

                        <div>
                          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "6px" }}>
                            <label style={{ fontSize: "11px", color: "#b5cde4" }}>
                              Right Profile Photo (Optional)
                            </label>
                            <span style={{ fontSize: "9px", fontWeight: "600", padding: "1px 5px", borderRadius: "3px", background: "rgba(22,185,201,0.15)", color: "var(--cyan)" }}>
                              OPTIONAL
                            </span>
                          </div>
                          <input
                            type="file"
                            accept=".jpg,.jpeg,.png,image/jpeg,image/png"
                            ref={updateRightFileRef}
                            onChange={(e) => setUpdateRightImage(e.target.files[0])}
                            style={{
                              width: "100%", padding: "6px", background: "#020e1a", border: "1px solid var(--border)",
                              borderRadius: "6px", color: "#b5cde4", fontSize: "11px"
                            }}
                          />
                        </div>
                      </div>

                      <span style={{ fontSize: "11px", color: "var(--muted)" }}>
                        Accepted formats: JPG, PNG. Updating face profile stores fresh 128-d embeddings for live camera recognition.
                      </span>

                      <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px", marginTop: "6px" }}>
                        <button
                          type="button"
                          onClick={handleCloseUpdateFace}
                          style={{
                            padding: "8px 14px",
                            background: "transparent",
                            border: "1px solid var(--border)",
                            borderRadius: "6px",
                            color: "var(--muted)",
                            fontSize: "12px",
                            cursor: "pointer"
                          }}
                        >
                          Cancel
                        </button>
                        <button
                          type="submit"
                          disabled={updateUploading}
                          style={{
                            padding: "8px 16px",
                            background: "var(--green)",
                            color: "#020e1a",
                            border: "none",
                            borderRadius: "6px",
                            fontWeight: "700",
                            fontSize: "12px",
                            cursor: "pointer",
                            display: "flex",
                            alignItems: "center",
                            gap: "6px"
                          }}
                        >
                          <Camera size={14} />
                          {updateUploading ? "Updating Face..." : "Save Face Profile"}
                        </button>
                      </div>
                    </form>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* 2. AUTHORIZED VEHICLES SECTION */}
          {authorizedSubSection === "vehicles" && (
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1.6fr", gap: "20px" }}>
              <section style={{ background: "#04192c", border: "1px solid var(--border)", borderRadius: "8px", padding: "20px" }}>
                <h3 style={{ margin: "0 0 14px 0", fontSize: "14px", display: "flex", alignItems: "center", gap: "8px" }}>
                  <Plus size={15} color="var(--cyan)" /> Register Authorized Vehicle
                </h3>

                {vehicleMessage && (
                  <div style={{
                    padding: "10px 14px", borderRadius: "6px", marginBottom: "16px", fontSize: "12px",
                    display: "flex", alignItems: "center", gap: "8px",
                    background: vehicleMessage.type === "success" ? "rgba(25,211,155,0.15)" : "rgba(239,75,95,0.15)",
                    border: `1px solid ${vehicleMessage.type === "success" ? "var(--green)" : "var(--red)"}`,
                    color: vehicleMessage.type === "success" ? "var(--green)" : "var(--red)"
                  }}>
                    {vehicleMessage.type === "success" ? <Check size={16} /> : <X size={16} />}
                    <span>{vehicleMessage.text}</span>
                  </div>
                )}

                <form onSubmit={handleAddVehicle} style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
                  <div>
                    <label style={{ fontSize: "12px", color: "#b5cde4", display: "block", marginBottom: "6px" }}>
                      License Plate Number:
                    </label>
                    <input
                      type="text"
                      placeholder="e.g. RJ14AB1234, SY14OAH"
                      value={vehiclePlate}
                      onChange={(e) => setVehiclePlate(e.target.value)}
                      required
                      style={{
                        width: "100%", padding: "10px 12px", background: "#020e1a", border: "1px solid var(--border)",
                        borderRadius: "6px", color: "#fff", fontSize: "14px", letterSpacing: "1px", fontWeight: "700"
                      }}
                    />
                    <span style={{ fontSize: "11px", color: "var(--muted)", marginTop: "4px", display: "block" }}>
                      FastALPR OCR matches detected plates against this registry.
                    </span>
                  </div>

                  <div>
                    <label style={{ fontSize: "12px", color: "#b5cde4", display: "block", marginBottom: "6px" }}>
                      Vehicle Classification:
                    </label>
                    <select
                      value={vehicleType}
                      onChange={(e) => setVehicleType(e.target.value)}
                      style={{
                        width: "100%", padding: "10px 12px", background: "#020e1a", border: "1px solid var(--border)",
                        borderRadius: "6px", color: "#fff", fontSize: "13px"
                      }}
                    >
                      <option value="Patrol SUV">Patrol SUV (QRT)</option>
                      <option value="Supply Truck">Supply & Logistics Truck</option>
                      <option value="Command Vehicle">Command Staff Vehicle</option>
                      <option value="VIP Escort">VIP Escort Vehicle</option>
                      <option value="Service Transport">Tactical Service Transport</option>
                    </select>
                  </div>

                  <div>
                    <label style={{ fontSize: "12px", color: "#b5cde4", display: "block", marginBottom: "6px" }}>
                      Assigned Unit / Owner:
                    </label>
                    <input
                      type="text"
                      placeholder="e.g. Sector Quick Reaction Team"
                      value={vehicleOwner}
                      onChange={(e) => setVehicleOwner(e.target.value)}
                      style={{
                        width: "100%", padding: "10px 12px", background: "#020e1a", border: "1px solid var(--border)",
                        borderRadius: "6px", color: "#fff", fontSize: "13px"
                      }}
                    />
                  </div>

                  <div>
                    <label style={{ fontSize: "12px", color: "#b5cde4", display: "block", marginBottom: "6px" }}>
                      Authorizing Authority:
                    </label>
                    <input
                      type="text"
                      placeholder="e.g. Sector Command"
                      value={vehicleAuthBy}
                      onChange={(e) => setVehicleAuthBy(e.target.value)}
                      style={{
                        width: "100%", padding: "10px 12px", background: "#020e1a", border: "1px solid var(--border)",
                        borderRadius: "6px", color: "#fff", fontSize: "13px"
                      }}
                    />
                  </div>

                  <button
                    type="submit"
                    style={{
                      padding: "10px 16px", background: "var(--cyan)", color: "#020e1a", border: "none",
                      borderRadius: "6px", fontWeight: "700", fontSize: "13px", cursor: "pointer",
                      display: "flex", alignItems: "center", justifyContent: "center", gap: "8px"
                    }}
                  >
                    <Car size={16} /> Register Authorized Vehicle
                  </button>
                </form>
              </section>

              <section style={{ background: "#04192c", border: "1px solid var(--border)", borderRadius: "8px", padding: "20px" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
                  <h3 style={{ margin: 0, fontSize: "14px" }}>Authorized Vehicles Registry ({vehiclesList.length})</h3>
                  <button onClick={loadAll} style={{ background: "transparent", border: "none", color: "var(--cyan)", cursor: "pointer", fontSize: "11px" }}>
                    <RefreshCw size={11} /> Refresh
                  </button>
                </div>

                <div style={{ maxHeight: "420px", overflowY: "auto" }}>
                  <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "12px" }}>
                    <thead>
                      <tr style={{ borderBottom: "1px solid var(--border)", textAlign: "left", color: "var(--muted)" }}>
                        <th style={{ padding: "8px" }}>PLATE NUMBER</th>
                        <th style={{ padding: "8px" }}>VEHICLE TYPE</th>
                        <th style={{ padding: "8px" }}>ASSIGNED UNIT</th>
                        <th style={{ padding: "8px" }}>AUTHORIZED BY</th>
                        <th style={{ padding: "8px" }}>STATUS</th>
                        <th style={{ padding: "8px" }}>ACTION</th>
                      </tr>
                    </thead>
                    <tbody>
                      {vehiclesList.map((v) => (
                        <tr key={v.id || v.plate_number} style={{ borderBottom: "1px solid rgba(18,60,96,0.5)" }}>
                          <td style={{ padding: "8px" }}>
                            <strong style={{ color: "var(--cyan)", fontFamily: "monospace", letterSpacing: "1px", fontSize: "13px" }}>
                              {v.plate_number}
                            </strong>
                          </td>
                          <td style={{ padding: "8px" }}>
                            {v.vehicle_type}
                          </td>
                          <td style={{ padding: "8px", color: "var(--muted)" }}>
                            {v.owner_name || "-"}
                          </td>
                          <td style={{ padding: "8px", color: "var(--muted)" }}>
                            {v.authorized_by}
                          </td>
                          <td style={{ padding: "8px" }}>
                            <span style={{
                              padding: "2px 6px", borderRadius: "4px", fontSize: "10px", fontWeight: "700",
                              background: "rgba(22,185,201,0.15)", color: "var(--cyan)", border: "1px solid rgba(22,185,201,0.4)"
                            }}>
                              ACTIVE
                            </span>
                          </td>
                          <td style={{ padding: "8px" }}>
                            <button
                              onClick={() => handleDeleteVehicle(v.plate_number)}
                              style={{ background: "transparent", border: "none", color: "var(--red)", cursor: "pointer" }}
                              title="Revoke Vehicle Authorization"
                            >
                              <Trash2 size={15} />
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </section>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
