# IBVAP: Intelligent Border Video Analytics Platform

**Intelligent Border Video Analytics Platform (IBVAP)** is a high-performance computer vision and surveillance analytics system built for border security infrastructure and critical checkpoint monitoring. Developed as a Smart India Hackathon (SIH) prototype.

---

## 1. Problem Statement & Mission

Border control checkpoints and tactical surveillance environments require continuous, automated video intelligence that operates with strict data integrity and real-time processing guarantees.

IBVAP addresses these operational challenges:
- **Facial Comparison & Recognition (FCR)**: Instantaneous face localization and vector cosine-similarity matching against watchlist databases.
- **Truthful ANPR / License Plate Recognition**: High-precision plate localization and character recognition (FastALPR ONNX CPU pipeline) with temporal persistence filtering to eliminate false positives.
- **Tamper-Evident Evidence Ledger**: Per-frame SHA-256 cryptographic chaining to create non-repudiable audit logs for verified incidents.
- **Flexible Video Source Ingestion**: Seamless switching between live laptop/USB optical sensors, bundled surveillance sample clips, and user-uploaded operational footage without application restarts.
- **2.5D Spatial Awareness**: Perspective ground-plane projection of detected entities relative to optical sensor origin.

---

## 2. System Architecture

```
                                    +-----------------------------------------+
                                    |        SURVEILLANCE VIDEO INGEST        |
                                    | (Webcam 0 / Demo Videos / User Uploads) |
                                    +--------------------+--------------------+
                                                         |
                                                         v
                                    +--------------------+--------------------+
                                    |      OPENCV VIDEO CAPTURE ENGINE        |
                                    |  (4K Downscaling, Session ID Validator) |
                                    +---------+--------------------+----------+
                                              |                    |
                         +--------------------+                    +--------------------+
                         v                                                              v
      +------------------+------------------+                        +------------------+------------------+
      |        FACIAL AI PIPELINE           |                        |       FASTALPR ANPR PIPELINE        |
      | - YuNet: 5-Point Landmark Detector  |                        | - YOLOv9-t: Plate Bounding Box      |
      | - SFace: 128D Embedding Recognizer  |                        | - MobileViT/CCT: Global Character OCR|
      | - Cosine Similarity Watchlist Match |                        | - 3-Tier Temporal Consensus Tracking |
      +------------------+------------------+                        +------------------+------------------+
                         |                                                              |
                         +--------------------+                    +--------------------+
                                              |                    |
                                              v                    v
                                    +---------+--------------------+----------+
                                    |        CRYPTOGRAPHIC EVIDENCE LEDGER     |
                                    |   (Append-Only SHA-256 Hash Chain Block) |
                                    +--------------------+--------------------+
                                                         |
                                                         v
                                    +--------------------+--------------------+
                                    |             FASTAPI BACKEND              |
                                    | (REST APIs, MJPEG Streams, Telemetry)   |
                                    +--------------------+--------------------+
                                                         |
                                                         v
                                    +--------------------+--------------------+
                                    |       REACT 18 / VITE FRONTEND          |
                                    |  (Live Feed, Watchlist, ANPR, Ledger,   |
                                    |   2.5D Scene Projection, Diagnostics)   |
                                    +-----------------------------------------+
```

---

## 3. Core Capabilities & Technology Stack

### A. Machine Learning & Computer Vision
- **YuNet Face Detection** (`face_detection_yunet_2023mar.onnx`): Real-time multi-scale landmark face detector.
- **SFace Face Recognition** (`face_recognition_sface_2021dec.onnx`): 128-dimensional L2-normalized embedding extraction with cosine similarity comparison ($Threshold \ge 0.55$).
- **FastALPR License Plate Engine**: Embedded ONNX YOLO-v9-t detector and global character OCR model running on `CPUExecutionProvider`.
- **Temporal Consensus ANPR**: 3-tier filtering pipeline (Raw Candidates $\rightarrow$ Validated Geometry $\rightarrow$ Confirmed Consensus Plates $\ge 3$ consecutive readings).

### B. Cryptographic Audit Chain
- **Tamper-Evident Ledger**: Computes SHA-256 digests of raw captured frames and critical alert events into an append-only JSON block chain (`backend/data/ledger.json` and `backend/data/frame_chain.json`).
- **Chain Validation**: Built-in verification endpoint (`/api/ledger/validate`) detects any retrospective modification of evidence blocks or metadata.

### C. Backend Stack
- **FastAPI** (Python 3.10+): Async REST endpoints and non-blocking multipart/x-mixed-replace MJPEG streaming.
- **OpenCV Python** (`cv2`): Frame acquisition, downscaling, DirectShow interfacing, and canvas HUD rendering.

### D. Frontend Stack
- **React 18 & Vite**: Component-driven surveillance console with tab routing (`Live Feed`, `Watchlist`, `ANPR`, `Alerts`, `Ledger`, `2.5D Scene`, `Settings`).
- **Lucide Icons & Vanilla CSS**: Cyber-tactical dark-mode design with responsive status telemetry.

---

## 4. Repository Structure

```
Team-Cache-Claude/
├── backend/
│   ├── data/                   # Runtime data stores (ledger, watchlist, alerts)
│   ├── models/                 # ONNX model binary weights
│   ├── runtime_uploads/        # User-uploaded surveillance videos
│   ├── sample_videos/          # Bundled demonstration video clips
│   ├── schemas/                # Pydantic data schemas
│   ├── services/
│   │   ├── alert_store.py      # Threat alert persistence
│   │   ├── anpr_engine.py      # FastALPR 3-tier inference pipeline
│   │   ├── anpr_store.py       # Confirmed plate record persistence
│   │   ├── face_engine.py      # YuNet + SFace recognition engine
│   │   ├── fcr_watchlist.py    # Target enrollment & vector matching
│   │   ├── ledger.py           # SHA-256 evidence chain manager
│   │   ├── video_manager.py    # Video discovery and upload handler
│   │   └── webcam.py           # Atomic source lifecycle & MJPEG streamer
│   ├── main.py                 # FastAPI application routes
│   ├── requirements.txt        # Backend dependencies
│   ├── test_plate_debug.py     # Targeted ANPR diagnostic test script
│   ├── test_tamper.py          # Cryptographic tamper verification test
│   └── test_verification.py    # End-to-end API verification suite
├── src/
│   ├── assets/                 # Frontend static assets
│   ├── components/
│   │   ├── AlertsTab.jsx       # Alert notification log
│   │   ├── AnprTab.jsx         # ANPR log & engine diagnostics
│   │   ├── LedgerTab.jsx       # Cryptographic evidence explorer
│   │   ├── LiveFeedTab.jsx     # Multi-source live surveillance display
│   │   ├── SceneTab.jsx        # 2.5D spatial projection canvas
│   │   ├── SettingsTab.jsx     # Sensor and model diagnostics
│   │   └── WatchlistTab.jsx    # Facial enrollment management
│   ├── api.js                  # Frontend API client
│   ├── App.jsx                 # Main application layout
│   └── styles.css              # Global design system
├── index.html                  # HTML entry point
├── package.json                # Frontend package configuration
├── vite.config.js              # Vite bundler configuration
└── README.md                   # Project documentation
```

---

## 5. Getting Started

### Prerequisites
- **Python**: Version 3.10, 3.11, or 3.12
- **Node.js**: Version 18+ and `npm`
- **Sensor**: Laptop webcam or USB camera (optional if using video clips)

### Step 1: Backend Setup
```bash
# Navigate to backend directory
cd backend

# Create and activate Python virtual environment
python -m venv .venv

# On Windows:
.\.venv\Scripts\activate

# On Linux/macOS:
source .venv/bin/activate

# Install backend dependencies
pip install -r requirements.txt
pip install "fast-alpr[onnx]"

# Copy environment configuration
cp .env.example .env
```

### Step 2: Frontend Setup
```bash
# In the root repository directory
npm install

# Copy frontend configuration
cp .env.example .env
```

---

## 6. Running the Platform

### Terminal 1: Start Backend API
```bash
cd backend
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```
API server running at: `http://127.0.0.1:8000`

### Terminal 2: Start Frontend Application
```bash
npm run dev
```
Surveillance Console running at: `http://localhost:5173`

---

## 7. API Reference

| Endpoint | Method | Description |
|---|---|---|
| `/api/health` | GET | Operational state and active model status |
| `/api/video-sources` | GET | List bundled demo surveillance clips |
| `/api/upload-video` | POST | Secure multipart upload of MP4/AVI footage |
| `/api/webcam/start` | POST | Atomic start of capture stream (webcam or video) |
| `/api/webcam/stop` | POST | Atomic stream shutdown |
| `/api/webcam/status` | GET | Stream telemetry, session ID, and FPS metrics |
| `/api/webcam/raw.mjpg` | GET | Multipart MJPEG stream of unannotated frames |
| `/api/webcam/ai.mjpg` | GET | Multipart MJPEG stream with HUD bounding overlays |
| `/api/webcam/detections` | GET | Real-time JSON detection payload (Faces + Confirmed Plates) |
| `/api/fcr/enroll` | POST | Enroll target identity with photo |
| `/api/fcr/watchlist` | GET | List enrolled targets and thumbnails |
| `/api/fcr/watchlist/{face_id}` | DELETE | Remove target identity |
| `/api/anpr/diagnostics` | GET | FastALPR performance, OCR latency, and candidate counts |
| `/api/anpr/records` | GET | Confirmed vehicle registration records |
| `/api/alerts` | GET | Log of verified high-threat watchlist match events |
| `/api/ledger` | GET | Complete cryptographic evidence hash chain |
| `/api/ledger/validate` | GET | Cryptographic validation of ledger integrity |

---

## 8. Verification & Diagnostics

```bash
# Compile check backend code
python -m compileall backend

# Run ANPR static test on sample video
python backend/test_plate_debug.py backend/runtime_uploads/upl_207c9acf5cb8.mp4

# Run cryptographic ledger tamper verification
python backend/test_tamper.py

# Build frontend production bundle
npm run build
```

---

## 9. Ethics, Privacy, and Security

1. **Academic Prototype**: Developed for demonstration and proof-of-concept purposes for SIH 2024.
2. **Deterministic Matching**: All facial matches are reported with similarity confidence scores and labeled as `Possible Match` to avoid false certainty.
3. **Data Security**: Uploaded files and enrollment images are stored locally with sanitised UUID filenames to prevent path traversal.
4. **No Third-Party Cloud Leaks**: Inference runs 100% on-premise on CPU via ONNX Runtime without sending biometric vectors to external cloud APIs.
