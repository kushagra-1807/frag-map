# FRAG-MAP — Orbital Debris Density Visualizer
### Hackathon Submission — Problem Statement 4

---

## Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Frontend UI | HTML5 + CSS3 + Vanilla JS | Dashboard shell |
| 3D Globe | Three.js (r128) | Interactive orbit visualization |
| Charts | Chart.js 4 | Density bar chart |
| Data Source | CelesTrak GP API | Real satellite TLE data |
| Backend (optional) | Python 3 + Flask | Server-side data processing |
| Orbital Math | sgp4 (Python) | TLE propagation |
| CORS | flask-cors | Frontend ↔ Backend bridge |

---

## Quick Start (Frontend Only — No Python Needed)

Just open `index.html` in a browser. Works standalone with simulated data that mirrors real CelesTrak distributions.

---

## Full Stack Setup (Real Live Data)

### 1. Install Python dependencies
```bash
pip install flask flask-cors requests sgp4
```

### 2. Run the backend
```bash
python server.py
```
Server starts at `http://localhost:5000`

### 3. Connect frontend to backend
In `index.html`, replace the `REAL_DATA` block with a fetch call:
```javascript
async function loadData() {
  const res = await fetch('http://localhost:5000/api/density');
  const data = await res.json();
  // populate dashboard with data
}
```

---

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/density` | All shell counts + risk scores + health report |
| `GET /api/shell/{name}` | Detailed object list for a specific shell |
| `GET /api/health` | Server health check |

---

## Orbital Shell Definitions

| Shell | Altitude | Risk | Notes |
|-------|----------|------|-------|
| VLEO | 200–400 km | Low | Atmospheric drag clears debris |
| LEO-1 | 400–600 km | High | ISS, crew vehicles |
| LEO-2 | 600–800 km | CRITICAL | Starlink dense zone |
| LEO-3 | 800–1000 km | CRITICAL | Iridium-COSMOS collision debris |
| LEO-4 | 1000–1200 km | High | Legacy satellites |
| MEO-Entry | 1200–2000 km | Moderate | Van Allen transition |

---

## Risk Metric Formula

```
Risk Score = min(100, (object_count / shell_threshold) × 100)

Kessler Index (0–10) = f(critical_shells, debris_ratio)
```

---

## Features

- Interactive 3D rotating Earth with orbit shell rings
- Altitude slider (200–2000 km) with real-time globe update  
- Per-shell object counts, risk badges, density bars
- Bar chart of density across all shells
- Critical hotspot list (Iridium-COSMOS, Fengyun-1C, etc.)
- Orbital health report with Kessler Syndrome Risk Index
- Drag-to-rotate globe
- Live UTC clock
- Cinematic loading sequence
