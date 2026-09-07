import React, { useState, useEffect, useRef } from "react";
import * as api from "../api";
import {
  Camera, Film, Upload, Play, Square, RefreshCw, Eye, Layers, Activity,
  AlertTriangle, CheckCircle, FileVideo, X, Car, AlertCircle, Loader2
} from "lucide-react";

export default function LiveFeedTab({ onNavigateToWatchlist }) {
  const [streamType, setStreamType] = useState("ai");
  const [camStatus, setCamStatus] = useState(null);
  const [detections, setDetections] = useState(null);
  const [loading, setLoading] = useState(false);
  const [feedReady, setFeedReady] = useState(false);
  const [feedError, setFeedError] = useState(null);
  const [streamSessionId, setStreamSessionId] = useState(Date.now());
  const [streamKey, setStreamKey] = useState(Date.now());

  const [selectedSourceType, setSelectedSourceType] = useState("webcam");
  const [demoVideos, setDemoVideos] = useState([]);
  const [selectedDemoId, setSelectedDemoId] = useState("");
  const [demoMessage, setDemoMessage] = useState("");
  const [loopEnabled, setLoopEnabled] = useState(true);

  const [uploadedVideo, setUploadedVideo] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState(null);
  const fileInputRef = useRef(null);

  const refreshState = async () => {
    try {
      const s = await api.getWebcamStatus();
      if (s) setCamStatus(s);
      const d = await api.getDetections();
      if (d) setDetections(d);
    } catch {
      // Ignore poll errors
    }
  };

  const loadDemoVideos = async () => {
    try {
      const res = await api.getVideoSources();
      const vids = res.videos || [];
      setDemoVideos(vids);
      setDemoMessage(res.message || "");
      if (vids.length > 0 && !selectedDemoId) {
        setSelectedDemoId(vids[0].id);
      }
    } catch (err) {
      setDemoMessage("Could not fetch demo videos.");
    }
  };

  useEffect(() => {
    refreshState();
    loadDemoVideos();
    const interval = setInterval(refreshState, 1000);
    return () => clearInterval(interval);
  }, []);

  const handleStartStream = async () => {
    setLoading(true);
    setUploadError(null);
    setFeedReady(false);
    setFeedError(null);

    const newSession = Date.now();
    setStreamSessionId(newSession);
    setStreamKey(newSession);

    try {
      if (selectedSourceType === "webcam") {
        await api.startWebcam(0);
      } else if (selectedSourceType === "demo_video") {
        if (!selectedDemoId) {
          setUploadError("Please select a demo video from the dropdown.");
          setLoading(false);
          return;
        }
        await api.startStream({
          source_type: "demo_video",
          source_id: selectedDemoId,
          loop: loopEnabled,
        });
      } else if (selectedSourceType === "uploaded_video") {
        if (!uploadedVideo || !uploadedVideo.id) {
          setUploadError("No uploaded video selected. Upload an MP4/AVI file first.");
          setLoading(false);
          return;
        }
        await api.startStream({
          source_type: "uploaded_video",
          source_id: uploadedVideo.id,
          source_name: uploadedVideo.name,
          loop: loopEnabled,
        });
      }
      await refreshState();
    } catch (e) {
      setUploadError(`Could not start stream: ${e.message}`);
      setFeedError(e.message);
    }
    setLoading(false);
  };

  const handleStopStream = async () => {
    setLoading(true);
    setFeedReady(false);
    setFeedError(null);
    try {
      await api.stopWebcam();
      await refreshState();
    } catch (e) {
      setUploadError(`Stop error: ${e.message}`);
    }
    setLoading(false);
  };

  const handleSourceTabChange = (type) => {
    setSelectedSourceType(type);
    setUploadError(null);
    if (type === "demo_video" && demoVideos.length === 0) {
      loadDemoVideos();
    }
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (file.size > 100 * 1024 * 1024) {
      setUploadError("File exceeds the maximum 100 MB limit.");
      return;
    }
    setUploading(true);
    setUploadError(null);
    try {
      const res = await api.uploadVideo(file);
      setUploadedVideo(res);
      setSelectedSourceType("uploaded_video");
    } catch (err) {
      setUploadError(err.message || "Failed to upload video.");
    }
    setUploading(false);
  };

  const handleClearUpload = () => {
    setUploadedVideo(null);
    setUploadError(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
    if (selectedSourceType === "uploaded_video") {
      setSelectedSourceType("webcam");
    }
  };

  const isFeedActive = camStatus?.feed_active || camStatus?.running || false;
  const isFinished = camStatus?.source_finished || false;
  const cameraError = camStatus?.camera_error || feedError || uploadError;
  const displayedFps = isFeedActive ? (camStatus?.displayed_fps || 0) : 0;

  const faces = detections?.faces || [];
  const confirmedPlates = detections?.plates || [];
  const watchlistMatches = faces.filter((f) => f.is_watchlist || f.classification === "Watchlist Match");

  const activeSession = camStatus?.session_id || streamSessionId;
  const currentStreamUrl =
    streamType === "ai"
      ? `${api.getAiStreamUrl()}?session=${activeSession}&t=${streamKey}`
      : streamType === "raw"
      ? `${api.getRawStreamUrl()}?session=${activeSession}&t=${streamKey}`
      : `${api.API_BASE}/api/webcam/debug-face-frame.jpg?session=${activeSession}&t=${Date.now()}`;

  const currentSourceName =
    selectedSourceType === "demo_video"
      ? (demoVideos.find((v) => v.id === selectedDemoId)?.name || "Demo Video")
      : selectedSourceType === "uploaded_video"
      ? (uploadedVideo?.name || "Uploaded Video")
      : "Laptop Webcam 0";

  return (
    <div>
      {/* SOURCE SELECTION */}
      <section style={{
        background: "#04192c",
        border: "1px solid var(--border)",
        borderRadius: "8px",
        padding: "16px 20px",
        marginBottom: "20px",
      }}>
        <div style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: "14px",
        }}>
          <div>
            <div style={{ fontSize: "11px", color: "var(--muted)", marginBottom: "6px", fontWeight: "600" }}>
              VIDEO SOURCE:
            </div>
            <div style={{
              display: "flex",
              background: "#020e1a",
              padding: "3px",
              borderRadius: "6px",
              border: "1px solid var(--border)",
            }}>
              {[
                { id: "webcam", label: "Laptop Webcam", icon: <Camera size={14} /> },
                { id: "demo_video", label: "Demo Video", icon: <Film size={14} /> },
                { id: "uploaded_video", label: "Upload Video", icon: <Upload size={14} /> },
              ].map((s) => (
                <button
                  key={s.id}
                  type="button"
                  onClick={() => handleSourceTabChange(s.id)}
                  style={{
                    padding: "6px 14px",
                    fontSize: "12px",
                    fontWeight: "600",
                    borderRadius: "4px",
                    border: "none",
                    background: selectedSourceType === s.id ? "var(--cyan)" : "transparent",
                    color: selectedSourceType === s.id ? "#020e1a" : "var(--muted)",
                    cursor: "pointer",
                    display: "flex",
                    alignItems: "center",
                    gap: "6px",
                  }}
                >
                  {s.icon} {s.label}
                </button>
              ))}
            </div>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: "14px", flexWrap: "wrap" }}>
            {selectedSourceType === "demo_video" && (
              <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                {demoVideos.length === 0 ? (
                  <span style={{ fontSize: "12px", color: "var(--orange)" }}>
                    {demoMessage || "No demo videos found."}
                  </span>
                ) : (
                  <select
                    value={selectedDemoId}
                    onChange={(e) => setSelectedDemoId(e.target.value)}
                    style={{
                      padding: "6px 10px",
                      background: "#020e1a",
                      border: "1px solid var(--border)",
                      borderRadius: "6px",
                      color: "#fff",
                      fontSize: "12px",
                    }}
                  >
                    {demoVideos.map((v) => (
                      <option key={v.id} value={v.id}>
                        {v.name} ({v.size_mb} MB)
                      </option>
                    ))}
                  </select>
                )}
              </div>
            )}

            {selectedSourceType === "uploaded_video" && (
              <div style={{ display: "flex", alignItems: "center", gap: "10px", flexWrap: "wrap" }}>
                <input
                  type="file"
                  accept=".mp4,.avi,.mov,.mkv"
                  ref={fileInputRef}
                  onChange={handleFileUpload}
                  style={{ display: "none" }}
                />
                <button
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  disabled={uploading}
                  style={{
                    padding: "6px 12px",
                    background: "#020e1a",
                    border: "1px solid var(--border)",
                    borderRadius: "6px",
                    color: "var(--cyan)",
                    fontSize: "12px",
                    cursor: "pointer",
                    display: "flex",
                    alignItems: "center",
                    gap: "6px",
                  }}
                >
                  <FileVideo size={14} /> {uploading ? "Uploading..." : uploadedVideo ? "Choose Another" : "Select Video"}
                </button>
                {uploadedVideo && (
                  <div style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "6px",
                    fontSize: "12px",
                    background: "#020e1a",
                    padding: "4px 8px",
                    borderRadius: "4px",
                    border: "1px solid var(--border)",
                  }}>
                    <span style={{ color: "var(--green)" }}>
                      Selected: <strong>{uploadedVideo.name}</strong>
                    </span>
                    <button
                      type="button"
                      onClick={handleClearUpload}
                      style={{
                        background: "transparent",
                        border: "none",
                        color: "var(--red)",
                        cursor: "pointer",
                        padding: "0 2px",
                      }}
                      title="Clear uploaded video"
                    >
                      <X size={14} />
                    </button>
                  </div>
                )}
              </div>
            )}

            {selectedSourceType !== "webcam" && (
              <label style={{ display: "flex", alignItems: "center", gap: "5px", fontSize: "11px", color: "#b5cde4", cursor: "pointer" }}>
                <input
                  type="checkbox"
                  checked={loopEnabled}
                  onChange={(e) => setLoopEnabled(e.target.checked)}
                /> Loop
              </label>
            )}

            {isFeedActive ? (
              <button
                type="button"
                onClick={handleStopStream}
                disabled={loading}
                style={{
                  padding: "8px 16px",
                  fontSize: "12px",
                  fontWeight: "600",
                  borderRadius: "6px",
                  border: "1px solid var(--red)",
                  background: "rgba(239,75,95,0.15)",
                  color: "var(--red)",
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                  gap: "6px",
                }}
              >
                <Square size={13} /> Stop
              </button>
            ) : (
              <button
                type="button"
                onClick={handleStartStream}
                disabled={loading || uploading}
                style={{
                  padding: "8px 18px",
                  fontSize: "12px",
                  fontWeight: "600",
                  borderRadius: "6px",
                  border: "none",
                  background: "var(--cyan)",
                  color: "#020e1a",
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                  gap: "6px",
                }}
              >
                {loading ? <Loader2 size={13} className="spin" /> : <Play size={13} />} Start
              </button>
            )}
          </div>
        </div>
        {uploadError && (
          <div style={{ marginTop: "10px", fontSize: "12px", color: "var(--red)", display: "flex", alignItems: "center", gap: "6px" }}>
            <AlertCircle size={14} /> Error: {uploadError}
          </div>
        )}
      </section>

      {/* STREAM VIEW TOGGLES */}
      <div style={{
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        marginBottom: "16px",
        flexWrap: "wrap",
        gap: "12px",
      }}>
        <div>
          <h2 style={{ margin: "0 0 4px 0", fontSize: "1.2rem" }}>Live Surveillance Display</h2>
          <p style={{ margin: 0, fontSize: "12px", color: "var(--muted)" }}>
            Real-time YuNet face detection, SFace watchlist matching, and FastALPR plate recognition.
          </p>
        </div>
        <div style={{ display: "flex", background: "#04192c", padding: "3px", borderRadius: "6px", border: "1px solid var(--border)" }}>
          {[
            { id: "ai", label: "AI Overlay", icon: <Layers size={13} /> },
            { id: "raw", label: "Raw Feed", icon: <Eye size={13} /> },
            { id: "debug", label: "Diagnostic", icon: <Activity size={13} /> },
          ].map((v) => (
            <button
              key={v.id}
              type="button"
              onClick={() => setStreamType(v.id)}
              style={{
                padding: "6px 12px",
                fontSize: "11px",
                fontWeight: "600",
                borderRadius: "4px",
                border: "none",
                background: streamType === v.id ? (v.id === "debug" ? "var(--orange)" : "var(--cyan)") : "transparent",
                color: streamType === v.id ? "#020e1a" : "var(--muted)",
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                gap: "4px",
              }}
            >
              {v.icon} {v.label}
            </button>
          ))}
        </div>
      </div>

      {/* WATCHLIST MATCH ALERT */}
      {watchlistMatches.length > 0 && (
        <div style={{
          background: "rgba(239,75,95,0.18)",
          border: "1px solid var(--red)",
          borderRadius: "8px",
          padding: "14px 18px",
          marginBottom: "20px",
          display: "flex",
          alignItems: "center",
          gap: "14px",
        }}>
          <AlertTriangle size={26} color="var(--red)" />
          <div>
            <strong style={{ color: "var(--red)", fontSize: "14px" }}>⚠ WATCHLIST MATCH DETECTED</strong>
            <div style={{ fontSize: "12px", color: "#ffcdd2", marginTop: "2px" }}>
              Target: <strong>{watchlistMatches.map((m) => m.identity).join(", ")}</strong>
              {" "}| Severity: <strong>HIGH</strong>
            </div>
          </div>
        </div>
      )}

      {/* DUAL GRID */}
      <div style={{ display: "grid", gridTemplateColumns: "1.2fr 0.8fr", gap: "20px" }}>
        {/* Video Screen */}
        <section style={{
          background: "#04192c",
          border: "1px solid var(--border)",
          borderRadius: "8px",
          overflow: "hidden",
          display: "flex",
          flexDirection: "column",
        }}>
          <div style={{
            padding: "12px 16px",
            borderBottom: "1px solid var(--border)",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}>
            <span style={{ fontSize: "12px", fontWeight: "700" }}>
              SOURCE: {camStatus?.source_name || currentSourceName}
            </span>
            <span style={{
              fontSize: "11px",
              color: isFeedActive ? "var(--green)" : cameraError ? "var(--red)" : "var(--muted)",
            }}>
              {isFeedActive
                ? `FEED ACTIVE (${displayedFps} FPS)`
                : cameraError
                ? "SOURCE ERROR"
                : isFinished
                ? "PLAYBACK FINISHED"
                : "STANDBY"}
            </span>
          </div>

          <div style={{
            position: "relative",
            background: "#020e1a",
            width: "100%",
            height: "480px",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            overflow: "hidden",
          }}>
            {/* Stream Image */}
            {(isFeedActive || loading) && (
              <img
                key={`feed-${streamSessionId}-${streamType}`}
                src={currentStreamUrl}
                alt="Surveillance Feed"
                onLoad={() => {
                  setFeedReady(true);
                  setFeedError(null);
                }}
                onError={() => {
                  setFeedError("Stream disconnected or failed to render image.");
                }}
                style={{
                  width: "100%",
                  height: "100%",
                  objectFit: "contain",
                  display: feedReady ? "block" : "none",
                }}
              />
            )}

            {/* Connecting State */}
            {((loading || (isFeedActive && !feedReady)) && !cameraError) && (
              <div style={{
                position: "absolute",
                inset: 0,
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                justifyContent: "center",
                background: "#020e1a",
                color: "#b5cde4",
              }}>
                <Loader2 size={36} className="spin" style={{ color: "var(--cyan)", marginBottom: "12px" }} />
                <strong style={{ fontSize: "14px" }}>Connecting to {currentSourceName}...</strong>
                <span style={{ fontSize: "12px", color: "var(--muted)", marginTop: "4px" }}>
                  Initializing optical sensor and AI models
                </span>
              </div>
            )}

            {/* Error State */}
            {cameraError && !feedReady && (
              <div style={{ textAlign: "center", padding: "60px 20px", color: "var(--red)" }}>
                <AlertCircle size={48} style={{ marginBottom: "12px" }} />
                <h4 style={{ margin: "0 0 8px 0" }}>Source Error</h4>
                <p style={{ margin: 0, fontSize: "13px", color: "#ffcdd2" }}>{cameraError}</p>
                <button
                  onClick={handleStartStream}
                  style={{
                    marginTop: "16px",
                    padding: "6px 14px",
                    background: "var(--cyan)",
                    border: "none",
                    borderRadius: "4px",
                    color: "#020e1a",
                    fontWeight: "600",
                    cursor: "pointer",
                  }}
                >
                  Retry Connection
                </button>
              </div>
            )}

            {/* Finished State */}
            {isFinished && !isFeedActive && !loading && (
              <div style={{ textAlign: "center", padding: "60px 20px", color: "var(--muted)" }}>
                <CheckCircle size={48} style={{ opacity: 0.4, color: "var(--cyan)", marginBottom: "12px" }} />
                <h4 style={{ margin: "0 0 8px 0", color: "#b5cde4" }}>Playback Completed</h4>
                <p style={{ margin: 0, fontSize: "13px" }}>Click Start to replay or select another video source.</p>
              </div>
            )}

            {/* Standby State */}
            {!isFeedActive && !isFinished && !loading && !cameraError && (
              <div style={{ textAlign: "center", padding: "60px 20px", color: "var(--muted)" }}>
                <Camera size={48} style={{ opacity: 0.3, marginBottom: "12px" }} />
                <h4 style={{ margin: "0 0 8px 0", color: "#b5cde4" }}>Surveillance Source Standby</h4>
                <p style={{ margin: 0, fontSize: "13px" }}>Select a video source above and click Start.</p>
              </div>
            )}
          </div>
        </section>

        {/* Detections Panel */}
        <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
          <section style={{
            background: "#04192c",
            border: "1px solid var(--border)",
            borderRadius: "8px",
            padding: "16px",
            flex: 1,
          }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "14px" }}>
              <strong style={{ fontSize: "12px" }}>
                DETECTIONS (Faces: {faces.length} | Plates: {confirmedPlates.length})
              </strong>
              <button
                onClick={refreshState}
                style={{
                  background: "transparent",
                  border: "none",
                  color: "var(--cyan)",
                  cursor: "pointer",
                  fontSize: "11px",
                  display: "flex",
                  alignItems: "center",
                  gap: "4px",
                }}
              >
                <RefreshCw size={11} /> Refresh
              </button>
            </div>

            {faces.length === 0 && confirmedPlates.length === 0 ? (
              <div style={{ textAlign: "center", padding: "40px 20px", color: "var(--muted)" }}>
                <Activity size={32} style={{ opacity: 0.25, marginBottom: "8px" }} />
                <p style={{ margin: 0, fontSize: "13px" }}>
                  {isFeedActive ? "No faces or confirmed plates in view." : "Stream is stopped."}
                </p>
              </div>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: "10px", maxHeight: "300px", overflowY: "auto" }}>
                {faces.map((f) => {
                  const isWatchlist = f.is_watchlist || f.classification === "Watchlist Match";
                  const isAuthorized = f.classification === "Authorized Person";
                  const cardBg = isWatchlist ? "rgba(239,75,95,0.15)" : isAuthorized ? "rgba(25,211,155,0.08)" : "rgba(22,185,201,0.08)";
                  const cardBorder = isWatchlist ? "var(--red)" : isAuthorized ? "var(--green)" : "var(--border)";
                  const dotColor = isWatchlist ? "var(--red)" : isAuthorized ? "var(--green)" : "var(--orange)";
                  const nameColor = isWatchlist ? "var(--red)" : isAuthorized ? "var(--green)" : "#fff";
                  const badgeBg = isWatchlist ? "var(--red)" : isAuthorized ? "rgba(25,211,155,0.2)" : "rgba(245,158,11,0.2)";
                  const badgeColor = isWatchlist ? "#fff" : isAuthorized ? "var(--green)" : "var(--orange)";
                  const badgeText = isWatchlist ? "HIGH ALERT" : isAuthorized ? "CLEAR" : "UNKNOWN";
                  const labelText = isWatchlist
                    ? `⚠ Watchlist Match: ${f.identity}`
                    : isAuthorized
                    ? `Authorized: ${f.identity}`
                    : f.identity === "Unknown" ? "Unknown Face" : `Detected: ${f.identity}`;

                  return (
                  <div
                    key={f.id}
                    style={{
                      background: cardBg,
                      border: `1px solid ${cardBorder}`,
                      borderRadius: "6px",
                      padding: "8px 12px",
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                    }}
                  >
                    <div>
                      <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                        <span style={{
                          width: "8px",
                          height: "8px",
                          borderRadius: "50%",
                          background: dotColor,
                        }} />
                        <strong style={{ fontSize: "12px", color: nameColor }}>
                          {labelText}
                        </strong>
                      </div>
                      <div style={{ fontSize: "11px", color: "var(--muted)", marginTop: "2px" }}>
                        Conf: {Math.round(f.confidence * 100)}%{f.match_score ? ` | Match: ${Math.round(f.match_score * 100)}%` : ""}
                      </div>
                    </div>
                    <span style={{
                      padding: "2px 6px",
                      borderRadius: "4px",
                      fontSize: "10px",
                      fontWeight: "bold",
                      background: badgeBg,
                      color: badgeColor,
                    }}>
                      {badgeText}
                    </span>
                  </div>
                  );
                })}

                {confirmedPlates.map((p, idx) => (
                  <div
                    key={`plate-${idx}`}
                    style={{
                      background: "rgba(25,211,155,0.12)",
                      border: "1px solid var(--green)",
                      borderRadius: "6px",
                      padding: "8px 12px",
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                    }}
                  >
                    <div>
                      <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                        <Car size={14} color="var(--green)" />
                        <strong style={{ fontSize: "13px", color: "var(--green)", fontFamily: "monospace" }}>
                          {p.plate_text || "Unreadable"}
                        </strong>
                      </div>
                      <div style={{ fontSize: "11px", color: "var(--muted)", marginTop: "2px" }}>
                        OCR: {Math.round((p.ocr_confidence || 0) * 100)}% | Det: {Math.round(p.confidence * 100)}%
                      </div>
                    </div>
                    <span style={{
                      padding: "2px 6px",
                      borderRadius: "4px",
                      fontSize: "10px",
                      fontWeight: "bold",
                      background: "rgba(25,211,155,0.25)",
                      color: "var(--green)",
                    }}>
                      CONFIRMED
                    </span>
                  </div>
                ))}
              </div>
            )}
          </section>

          <section style={{ background: "#04192c", border: "1px solid var(--border)", borderRadius: "8px", padding: "16px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "10px" }}>
              <strong style={{ fontSize: "12px" }}>FCR WATCHLIST</strong>
              <button
                onClick={onNavigateToWatchlist}
                style={{
                  background: "transparent",
                  border: "none",
                  color: "var(--cyan)",
                  fontSize: "11px",
                  cursor: "pointer",
                  fontWeight: "600",
                }}
              >
                + Manage
              </button>
            </div>
            <p style={{ margin: 0, fontSize: "12px", color: "#b5cde4" }}>
              Enrolled: <strong>{camStatus?.watchlist_count || 0} targets</strong>
            </p>
          </section>
        </div>
      </div>
    </div>
  );
}
