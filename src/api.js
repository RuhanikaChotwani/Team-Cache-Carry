/**
 * IBVAP Frontend API Helper
 * Base URL configurable via VITE_API_BASE, defaults to http://127.0.0.1:8000
 */

export const API_BASE = import.meta.env.VITE_API_BASE || "http://127.0.0.1:8000";

let authToken = localStorage.getItem("ibvap_auth_token") || "";

export function setAuthToken(token) {
  authToken = token || "";
  if (token) {
    localStorage.setItem("ibvap_auth_token", token);
  } else {
    localStorage.removeItem("ibvap_auth_token");
  }
}

export function getAuthToken() {
  return authToken;
}

async function apiFetch(path, options = {}) {
  try {
    const headers = options.body instanceof FormData ? {} : { "Content-Type": "application/json", ...options.headers };
    if (authToken) {
      headers["Authorization"] = `Bearer ${authToken}`;
    }

    const res = await fetch(`${API_BASE}${path}`, {
      ...options,
      headers,
    });
    if (!res.ok) {
      const errData = await res.json().catch(() => ({}));
      throw new Error(errData.detail || `API error: ${res.status}`);
    }
    return await res.json();
  } catch (err) {
    console.warn(`API call failed: ${path}`, err.message);
    throw err;
  }
}

// --- Authentication ---
export async function login(username, password) {
  const res = await apiFetch("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });
  if (res.access_token) {
    setAuthToken(res.access_token);
  }
  return res;
}

export function getAuthProfile() {
  return apiFetch("/api/auth/me").catch(() => null);
}

export function logout() {
  setAuthToken("");
  return apiFetch("/api/auth/logout", { method: "POST" }).catch(() => ({}));
}

// --- Health ---
export function health() {
  return apiFetch("/api/health").catch(() => null);
}

// --- Video Sources and Upload ---
export function getVideoSources() {
  return apiFetch("/api/video-sources").catch(() => ({ videos: [], message: "Could not fetch demo videos" }));
}

export function uploadVideo(file) {
  const formData = new FormData();
  formData.append("file", file);
  return apiFetch("/api/video/upload", {
    method: "POST",
    body: formData,
  });
}

// --- Stream Control ---
export function startStream(params = {}) {
  return apiFetch("/api/webcam/start", {
    method: "POST",
    body: JSON.stringify(params),
  });
}

export function startWebcam(source = 0) {
  return startStream({
    source_type: "webcam",
    source: source,
    source_name: `Laptop Webcam ${source}`,
    loop: false,
  });
}

export function stopWebcam() {
  return apiFetch("/api/webcam/stop", { method: "POST" });
}

export function getWebcamStatus() {
  return apiFetch("/api/webcam/status").catch(() => null);
}

export function getDetections() {
  return apiFetch("/api/webcam/detections").catch(() => null);
}

export function getRawStreamUrl() {
  return `${API_BASE}/api/webcam/raw.mjpg`;
}

export function getAiStreamUrl() {
  return `${API_BASE}/api/webcam/ai.mjpg`;
}

// --- FCR Watchlist ---
export function enrollFace(name, imageFile, leftImageFile = null, rightImageFile = null) {
  const formData = new FormData();
  formData.append("name", name);
  formData.append("image", imageFile);
  if (leftImageFile) formData.append("left_image", leftImageFile);
  if (rightImageFile) formData.append("right_image", rightImageFile);

  return apiFetch("/api/fcr/enroll", {
    method: "POST",
    body: formData,
  });
}

export function getWatchlist() {
  return apiFetch("/api/fcr/watchlist").catch(() => []);
}

export function deleteWatchlistFace(faceId) {
  return apiFetch(`/api/fcr/watchlist/${faceId}`, {
    method: "DELETE",
  });
}

export function getMatches() {
  return apiFetch("/api/fcr/matches").catch(() => []);
}

// --- Authorized Personnel ---
export function getAuthorizedPersonnel() {
  return apiFetch("/api/authorized-personnel").catch(() => []);
}

export function addAuthorizedPersonnel(data) {
  return apiFetch("/api/authorized-personnel", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function deleteAuthorizedPersonnel(personId) {
  return apiFetch(`/api/authorized-personnel/${personId}`, {
    method: "DELETE",
  });
}

// --- Authorized Personnel Face Enrollment ---
export function enrollAuthorizedFace(dataOrName, frontImage, leftImage = null, rightImage = null) {
  const formData = new FormData();
  if (typeof dataOrName === "object" && dataOrName !== null) {
    formData.append("name", dataOrName.name || "");
    if (dataOrName.role_type) formData.append("role_type", dataOrName.role_type);
    if (dataOrName.badge_id) formData.append("badge_id", dataOrName.badge_id);
    if (dataOrName.department) formData.append("department", dataOrName.department);
  } else {
    formData.append("name", dataOrName || "");
  }
  formData.append("image", frontImage);
  if (leftImage) formData.append("left_image", leftImage);
  if (rightImage) formData.append("right_image", rightImage);

  return apiFetch("/api/authorized-personnel/enroll-face", {
    method: "POST",
    body: formData,
  });
}

export function updateAuthorizedFace(personId, frontImage, leftImage = null, rightImage = null) {
  const formData = new FormData();
  formData.append("image", frontImage);
  if (leftImage) formData.append("left_image", leftImage);
  if (rightImage) formData.append("right_image", rightImage);

  return apiFetch(`/api/authorized-personnel/${personId}/face`, {
    method: "POST",
    body: formData,
  });
}

export function getAuthorizedFaces() {
  return apiFetch("/api/authorized-personnel/faces").catch(() => []);
}

export function deleteAuthorizedFace(faceId) {
  return apiFetch(`/api/authorized-personnel/faces/${faceId}`, {
    method: "DELETE",
  });
}

// --- ANPR ---
export function getLatestAnpr() {
  return apiFetch("/api/anpr/latest").catch(() => null);
}

export function getAnprDiagnostics() {
  return apiFetch("/api/anpr/diagnostics").catch(() => null);
}

export function toggleAnpr(enabled) {
  return apiFetch("/api/anpr/toggle", {
    method: "POST",
    body: JSON.stringify({ enabled }),
  });
}

export function getAnprRecords(limit = 100) {
  return apiFetch(`/api/anpr/records?limit=${limit}`).catch(() => []);
}

export function clearAnprRecords() {
  return apiFetch("/api/anpr/records", { method: "DELETE" });
}

// --- Authorized Vehicles ---
export function getAuthorizedVehicles() {
  return apiFetch("/api/authorized-vehicles").catch(() => []);
}

export function addAuthorizedVehicle(data) {
  return apiFetch("/api/authorized-vehicles", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function deleteAuthorizedVehicle(plateNumber) {
  return apiFetch(`/api/authorized-vehicles/${plateNumber}`, {
    method: "DELETE",
  });
}

// --- Alerts & Officer Security Panel ---
export function getAlerts(limit = 100) {
  return apiFetch(`/api/alerts?limit=${limit}`).catch(() => []);
}

export function getOfficerAlerts(limit = 100) {
  return apiFetch(`/api/officer/alerts?limit=${limit}`).catch(() => []);
}

export function clearAlerts() {
  return apiFetch("/api/alerts", { method: "DELETE" });
}


// --- Evidence & Blockchain Verification ---
export function getEvidenceImageUrl(filename) {
  return `${API_BASE}/api/evidence/${filename}`;
}

export function getEvidenceDownloadUrl(eventId) {
  const token = getAuthToken();
  const q = token ? `?token=${encodeURIComponent(token)}` : "";
  return `${API_BASE}/api/evidence/${eventId}/download${q}`;
}

export function verifyEvidenceIntegrity(eventId) {
  return apiFetch(`/api/evidence/${eventId}/verify`);
}

export function getCertificate(eventId) {
  return apiFetch(`/api/evidence/${eventId}/certificate`);
}

// --- Event Evidence Ledger ---
export function getLedger() {
  return apiFetch("/api/ledger").catch(() => []);
}

export function validateLedger() {
  return apiFetch("/api/ledger/validate").catch(() => null);
}

// --- Frame Hash Chain ---
export function getLedgerStatus() {
  return apiFetch("/api/ledger/status").catch(() => null);
}

export function getLedgerRecent(limit = 50) {
  return apiFetch(`/api/ledger/recent?limit=${limit}`).catch(() => ({ frame_chain_records: [], event_evidence_records: [] }));
}

export function verifyFrameChain(sessionId = null) {
  const q = sessionId ? `?session_id=${sessionId}` : "";
  return apiFetch(`/api/ledger/verify${q}`).catch(() => ({ valid: false, message: "Verification request failed" }));
}

// --- Restricted Zones ---
export function getZones() {
  return apiFetch("/api/zones").catch(() => []);
}

export function createZone(zoneData) {
  return apiFetch("/api/zones", {
    method: "POST",
    body: JSON.stringify(zoneData),
  });
}

export function deleteZone(zoneId) {
  return apiFetch(`/api/zones/${zoneId}`, {
    method: "DELETE",
  });
}
