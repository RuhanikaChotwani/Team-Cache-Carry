import React, { useRef, useEffect, useState } from "react";
import * as api from "../api";
import { Box, Camera, RefreshCw, Shield, AlertTriangle } from "lucide-react";

/**
 * 2.5D Tactical Scene Projection using HTML5 Canvas.
 * Renders perspective ground plane, security zones, and real classified entity markers:
 * - Authorized Person (Green)
 * - Unknown Person (Red Alert)
 * - Authorized Vehicle (Cyan)
 * - Unregistered Vehicle (Amber Alert)
 * - Animal (Yellow)
 * - Potential Animal Threat (Crimson Alert)
 */
export default function SceneTab() {
  const canvasRef = useRef(null);
  const [detections, setDetections] = useState(null);
  const [camStatus, setCamStatus] = useState(null);
  const [zones, setZones] = useState([]);

  const pollData = () => {
    api.getDetections().then((d) => d && setDetections(d));
    api.getWebcamStatus().then((s) => s && setCamStatus(s));
    api.getZones().then((z) => z && setZones(z));
  };

  useEffect(() => {
    pollData();
    const interval = setInterval(pollData, 1500);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const W = canvas.width;
    const H = canvas.height;
    const CX = W / 2;
    const CY = H * 0.85;

    // Clear background
    ctx.fillStyle = "#020e1a";
    ctx.fillRect(0, 0, W, H);

    // Draw ground grid (2.5D perspective)
    ctx.strokeStyle = "rgba(22, 60, 96, 0.35)";
    ctx.lineWidth = 1;

    const gridRows = 12;
    const gridCols = 16;
    const horizonY = H * 0.18;

    for (let r = 0; r <= gridRows; r++) {
      const t = r / gridRows;
      const y = horizonY + (CY - horizonY) * t;
      const spread = 0.3 + 0.7 * t;
      const x1 = CX - (W / 2) * spread;
      const x2 = CX + (W / 2) * spread;
      ctx.beginPath();
      ctx.moveTo(x1, y);
      ctx.lineTo(x2, y);
      ctx.stroke();
    }

    for (let c = 0; c <= gridCols; c++) {
      const frac = (c / gridCols - 0.5) * 2;
      const topX = CX + frac * (W * 0.15);
      const botX = CX + frac * (W * 0.5);
      ctx.beginPath();
      ctx.moveTo(topX, horizonY);
      ctx.lineTo(botX, CY);
      ctx.stroke();
    }

    // Horizon line
    ctx.strokeStyle = "rgba(22, 185, 201, 0.25)";
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(0, horizonY);
    ctx.lineTo(W, horizonY);
    ctx.stroke();

    // Frame dimensions for normalization
    const frameW = camStatus?.current_frame_width || 640;
    const frameH = camStatus?.current_frame_height || 480;

    // Project 2D frame coordinate to 2.5D scene position
    function projectToScene(bboxCenterX, bboxBottomY) {
      const normX = bboxCenterX / frameW;
      const normY = bboxBottomY / frameH;
      const depth = Math.max(0.05, Math.min(1.0, normY));
      const sceneY = horizonY + (CY - horizonY) * depth;
      const spread = 0.3 + 0.7 * depth;
      const sceneX = CX + (normX - 0.5) * W * spread;
      return { x: sceneX, y: sceneY, depth: depth };
    }

    // Draw Restricted Zones projected on 2.5D Ground
    for (const z of zones) {
      let pts = z.points || [];
      if (typeof pts === "string") {
        try { pts = JSON.parse(pts); } catch { pts = []; }
      }
      if (pts.length >= 3) {
        ctx.beginPath();
        const first = projectToScene(pts[0][0], pts[0][1]);
        ctx.moveTo(first.x, first.y);
        for (let i = 1; i < pts.length; i++) {
          const pt = projectToScene(pts[i][0], pts[i][1]);
          ctx.lineTo(pt.x, pt.y);
        }
        ctx.closePath();
        ctx.fillStyle = z.severity === "Critical" ? "rgba(239, 75, 95, 0.12)" : "rgba(255, 159, 67, 0.12)";
        ctx.fill();
        ctx.strokeStyle = z.severity === "Critical" ? "rgba(239, 75, 95, 0.4)" : "rgba(255, 159, 67, 0.4)";
        ctx.lineWidth = 1.5;
        ctx.stroke();

        // Zone Label
        const centerPt = projectToScene((pts[0][0] + pts[1][0]) / 2, (pts[0][1] + pts[2][1]) / 2);
        ctx.fillStyle = z.severity === "Critical" ? "rgba(239, 75, 95, 0.7)" : "rgba(255, 159, 67, 0.7)";
        ctx.font = "9px Inter, sans-serif";
        ctx.textAlign = "center";
        ctx.fillText(`ZONE: ${z.name.toUpperCase()}`, centerPt.x, centerPt.y);
      }
    }

    // Camera origin marker
    ctx.fillStyle = "rgba(22, 185, 201, 0.8)";
    ctx.beginPath();
    ctx.arc(CX, CY, 8, 0, Math.PI * 2);
    ctx.fill();
    ctx.strokeStyle = "rgba(22, 185, 201, 0.5)";
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.arc(CX, CY, 14, 0, Math.PI * 2);
    ctx.stroke();

    ctx.fillStyle = "#b5cde4";
    ctx.font = "11px Inter, sans-serif";
    ctx.textAlign = "center";
    ctx.fillText("CAM-01 ORIGIN", CX, CY + 28);

    // Title HUD
    ctx.fillStyle = "rgba(22, 185, 201, 0.9)";
    ctx.font = "bold 13px Inter, sans-serif";
    ctx.textAlign = "left";
    ctx.fillText("2.5D TACTICAL SCENE PROJECTION", 16, 24);

    ctx.fillStyle = "#8aa2bc";
    ctx.font = "11px Inter, sans-serif";
    ctx.fillText("Perspective coordinates with multi-class security classification", 16, 40);

    const entities = detections?.entities || [];
    const faces = detections?.faces || [];
    const plates = detections?.plates || [];

    const drawnLabels = [];

    // Prioritize rendering full classified entities if available
    const targetsToDraw = entities.length > 0 ? entities : [
      ...faces.map((f) => ({
        bbox: f.bbox,
        classification: f.classification || (f.is_watchlist ? "Watchlist Match" : f.is_authorized ? "Authorized Person" : "Unknown Person"),
        identity: f.identity || "Unknown",
        track_id: f.id,
      })),
      ...plates.map((p) => ({
        bbox: p.bbox,
        classification: p.classification || (p.is_authorized ? "Authorized Vehicle" : "Unregistered Vehicle"),
        identity: p.plate_text || "Vehicle",
        track_id: p.id,
      }))
    ];

    for (const ent of targetsToDraw) {
      if (!ent || !ent.bbox || !Array.isArray(ent.bbox) || ent.bbox.length < 4) continue;
      const [x1, y1, x2, y2] = ent.bbox;
      if (isNaN(x1) || isNaN(y1) || isNaN(x2) || isNaN(y2)) continue;
      const cx = (Number(x1) + Number(x2)) / 2;
      const by = Number(y2);
      const { x, y, depth } = projectToScene(cx, by);
      if (isNaN(x) || isNaN(y)) continue;

      const cls = ent.classification || "Unknown Person";
      const ident = ent.identity || "Subject";
      const markerSize = Math.max(5, 5 + depth * 7);

      let color = "rgba(239, 75, 95, 0.9)"; // default red
      let label = `UNKNOWN: ${ident}`;
      let isVehicle = false;

      if (cls === "Watchlist Match") {
        color = "rgba(255, 30, 90, 0.95)";
        label = `⚠ WATCHLIST: ${ident.toUpperCase()}`;
      } else if (cls === "Authorized Person") {
        color = "rgba(25, 211, 155, 0.95)";
        label = `AUTHORIZED: ${ident}`;
      } else if (cls === "Unknown Person") {
        color = "rgba(239, 75, 95, 0.95)";
        label = `UNKNOWN PERSON #${ent.track_id || ""}`;
      } else if (cls === "Authorized Vehicle") {
        color = "rgba(0, 220, 255, 0.95)";
        label = `AUTH VEHICLE: ${ident}`;
        isVehicle = true;
      } else if (cls === "Unregistered Vehicle") {
        color = "rgba(255, 159, 67, 0.95)";
        label = `UNREG VEHICLE: ${ident}`;
        isVehicle = true;
      } else if (cls === "Potential Animal Threat") {
        color = "rgba(255, 75, 75, 0.95)";
        label = `ANIMAL THREAT: ${(ident || ent.class || "THREAT").toUpperCase()}`;
      } else if (cls === "Animal") {
        color = "rgba(255, 215, 0, 0.95)";
        label = `ANIMAL: ${(ident || ent.class || "").toUpperCase()}`;
      }

      if (isVehicle) {
        // Diamond marker for vehicles
        ctx.fillStyle = color;
        ctx.beginPath();
        ctx.moveTo(x, y - markerSize);
        ctx.lineTo(x + markerSize, y);
        ctx.lineTo(x, y + markerSize);
        ctx.lineTo(x - markerSize, y);
        ctx.closePath();
        ctx.fill();

        ctx.strokeStyle = color;
        ctx.lineWidth = 1.5;
        ctx.stroke();
      } else {
        // Circle marker
        ctx.fillStyle = color;
        ctx.beginPath();
        ctx.arc(x, y, markerSize, 0, Math.PI * 2);
        ctx.fill();

        // Pulsing alert ring for watchlist matches, unknown persons, and animal threats
        if (cls === "Watchlist Match" || cls === "Unknown Person" || cls === "Potential Animal Threat" || cls === "Unregistered Vehicle") {
          ctx.strokeStyle = color;
          ctx.lineWidth = 1.5;
          ctx.beginPath();
          ctx.arc(x, y, markerSize + 5, 0, Math.PI * 2);
          ctx.stroke();
        }
      }

      // Label with collision avoidance
      let labelY = y - markerSize - 8;
      for (const prev of drawnLabels) {
        if (Math.abs(prev.x - x) < 70 && Math.abs(prev.y - labelY) < 14) {
          labelY -= 16;
        }
      }

      ctx.fillStyle = color;
      ctx.font = `bold 10px Inter, sans-serif`;
      ctx.textAlign = "center";
      ctx.fillText(label, x, labelY);
      drawnLabels.push({ x, y: labelY });
    }

    // Bottom Status HUD
    const isLive = camStatus?.running || false;
    ctx.fillStyle = isLive ? "rgba(25, 211, 155, 0.8)" : "rgba(120, 160, 190, 0.5)";
    ctx.font = "10px Inter, sans-serif";
    ctx.textAlign = "right";
    ctx.fillText(
      isLive
        ? `LIVE CCTV | Targets: ${targetsToDraw.length} | Zones: ${zones.length} | Projection: 2.5D Ground Grid`
        : "STANDBY - Activate optical feed to project active radar coordinates",
      W - 16,
      H - 14,
    );

  }, [detections, camStatus, zones]);

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "20px", flexWrap: "wrap", gap: "12px" }}>
        <div>
          <h2 style={{ margin: "0 0 4px 0", fontSize: "1.3rem" }}>2.5D Tactical Scene Projection</h2>
          <p style={{ margin: 0, fontSize: "12px", color: "var(--muted)" }}>
            Perspective scene view derived from confirmed detection coordinates with multi-target security classifications.
          </p>
        </div>

        {/* Legend */}
        <div style={{ display: "flex", gap: "12px", alignItems: "center", background: "#04192c", border: "1px solid var(--border)", borderRadius: "6px", padding: "6px 12px", fontSize: "11px", flexWrap: "wrap" }}>
          <LegendItem color="rgba(255, 30, 90, 0.95)" label="Watchlist Match" />
          <LegendItem color="var(--green)" label="Authorized Person" />
          <LegendItem color="var(--red)" label="Unknown Person" />
          <LegendItem color="var(--cyan)" label="Authorized Vehicle" />
          <LegendItem color="var(--orange)" label="Unregistered Vehicle" />
          <LegendItem color="#ffd700" label="Animal" />
          <LegendItem color="#ff3333" label="Animal Threat" />
        </div>
      </div>

      <section style={{
        background: "#04192c", border: "1px solid var(--border)", borderRadius: "8px",
        overflow: "hidden", display: "flex", justifyContent: "center", position: "relative",
      }}>
        <canvas ref={canvasRef} width={960} height={540} style={{ display: "block", width: "100%", maxHeight: "540px" }} />
      </section>
    </div>
  );
}

function LegendItem({ color, label }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: "5px" }}>
      <span style={{ width: "8px", height: "8px", borderRadius: "50%", background: color, display: "inline-block" }} />
      <span style={{ color: "#b5cde4" }}>{label}</span>
    </div>
  );
}
