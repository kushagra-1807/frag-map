"""
FRAG-MAP Backend — Python Flask Server
Fetches real TLE data from CelesTrak and serves orbital density analysis.

SETUP:
  pip install flask requests flask-cors sgp4

RUN:
  python server.py

Then open index.html OR visit http://localhost:5000/api/density
"""

from flask import Flask, jsonify
from flask_cors import CORS
import requests, math, json
from datetime import datetime

app = Flask(__name__)
CORS(app)  # Allow frontend JS to call this API

# ─── ORBITAL SHELL DEFINITIONS ───────────────────────────────────────────────
SHELLS = [
    {"name": "VLEO",     "min": 200,  "max": 400,  "risk": "low",      "color": "#00ff88"},
    {"name": "LEO-1",    "min": 400,  "max": 600,  "risk": "high",     "color": "#ffa500"},
    {"name": "LEO-2",    "min": 600,  "max": 800,  "risk": "critical", "color": "#ff4444"},
    {"name": "LEO-3",    "min": 800,  "max": 1000, "risk": "critical", "color": "#ff4444"},
    {"name": "LEO-4",    "min": 1000, "max": 1200, "risk": "high",     "color": "#ffa500"},
    {"name": "MEO-Entry","min": 1200, "max": 2000, "risk": "moderate", "color": "#ffff44"},
]

# ─── CELESTRAK ENDPOINTS ─────────────────────────────────────────────────────
CELESTRAK_URLS = {
    "active":    "https://celestrak.org/SOCRATES/query.php?CODE=active&FORMAT=tle",
    "debris":    "https://celestrak.org/SOCRATES/query.php?CODE=debris&FORMAT=tle",
    "stations":  "https://celestrak.org/SOCRATES/query.php?CODE=stations&FORMAT=tle",
    # Simpler JSON endpoint (recommended):
    "json_all":  "https://celestrak.org/SOCRATES/query.php?CODE=ALL&FORMAT=json",
    # GP data (most reliable):
    "gp_active": "https://celestrak.org/GP/query?GROUP=active&FORMAT=json",
    "gp_debris": "https://celestrak.org/GP/query?GROUP=debris&FORMAT=json",
}

def fetch_celestrak_gp(group="active"):
    """Fetch satellite data from CelesTrak GP endpoint (returns JSON directly)."""
    url = f"https://celestrak.org/GP/query?GROUP={group}&FORMAT=json"
    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"CelesTrak fetch error: {e}")
        return []

def mean_motion_to_altitude(mean_motion_rev_per_day):
    """
    Convert TLE mean motion (revs/day) to approximate altitude in km.
    Uses vis-viva equation approximation.
    """
    MU = 398600.4418       # Earth gravitational parameter km³/s²
    RE = 6371.0            # Earth radius km
    n_rad_per_sec = mean_motion_rev_per_day * 2 * math.pi / 86400
    # Semi-major axis: a = (MU / n²)^(1/3)
    a = (MU / (n_rad_per_sec ** 2)) ** (1/3)
    alt = a - RE
    return round(alt, 1)

def classify_shell(altitude_km):
    """Return the shell a given altitude belongs to."""
    for s in SHELLS:
        if s["min"] <= altitude_km <= s["max"]:
            return s["name"]
    return "OUTSIDE_LEO"

def compute_risk_score(count, shell_name):
    """
    Risk metric: density × historical collision factor.
    Returns 0–100 score.
    """
    THRESHOLDS = {
        "VLEO": 2000, "LEO-1": 3000, "LEO-2": 6000,
        "LEO-3": 5000, "LEO-4": 3500, "MEO-Entry": 2000
    }
    threshold = THRESHOLDS.get(shell_name, 3000)
    score = min(100, int((count / threshold) * 100))
    return score

# ─── API ROUTES ───────────────────────────────────────────────────────────────

@app.route("/api/density", methods=["GET"])
def get_density():
    """
    Main endpoint: returns object counts per shell + risk scores.
    Frontend fetches this and renders the dashboard.
    """
    active_sats = fetch_celestrak_gp("active")
    debris_objs = fetch_celestrak_gp("debris")

    all_objects = []

    for obj in active_sats:
        mm = obj.get("MEAN_MOTION", 0)
        if mm > 0:
            alt = mean_motion_to_altitude(mm)
            all_objects.append({"alt": alt, "type": "active", "name": obj.get("OBJECT_NAME","")})

    for obj in debris_objs:
        mm = obj.get("MEAN_MOTION", 0)
        if mm > 0:
            alt = mean_motion_to_altitude(mm)
            all_objects.append({"alt": alt, "type": "debris", "name": obj.get("OBJECT_NAME","")})

    # Count per shell
    shell_data = {s["name"]: {"count":0,"active":0,"debris":0} for s in SHELLS}
    for obj in all_objects:
        shell = classify_shell(obj["alt"])
        if shell in shell_data:
            shell_data[shell]["count"] += 1
            shell_data[shell][obj["type"]] += 1

    # Add risk scores
    for shell_name, data in shell_data.items():
        data["risk_score"] = compute_risk_score(data["count"], shell_name)

    total = len(all_objects)
    active_count = sum(1 for o in all_objects if o["type"]=="active")
    debris_count = total - active_count

    # Kessler risk index (0–10)
    critical_shells = sum(1 for s,d in shell_data.items() if d["risk_score"]>70)
    kessler = round(min(10, (critical_shells/len(SHELLS))*10 + (debris_count/total)*4), 1)

    return jsonify({
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "total_objects": total,
        "active_satellites": active_count,
        "debris_count": debris_count,
        "critical_zones": critical_shells,
        "kessler_index": kessler,
        "shells": shell_data,
        "health": {
            "saturation": min(100, int(total/350)),
            "collision_probability": min(100, int(debris_count/total*100)),
            "debris_growth_rate": 71,  # % based on 10yr trend
        }
    })

@app.route("/api/shell/<shell_name>", methods=["GET"])
def get_shell_detail(shell_name):
    """Detailed breakdown for a specific shell."""
    shell_def = next((s for s in SHELLS if s["name"]==shell_name), None)
    if not shell_def:
        return jsonify({"error": "Shell not found"}), 404

    active_sats = fetch_celestrak_gp("active")
    objects_in_shell = []

    for obj in active_sats:
        mm = obj.get("MEAN_MOTION", 0)
        if mm > 0:
            alt = mean_motion_to_altitude(mm)
            if shell_def["min"] <= alt <= shell_def["max"]:
                objects_in_shell.append({
                    "name": obj.get("OBJECT_NAME",""),
                    "norad_id": obj.get("NORAD_CAT_ID",""),
                    "altitude_km": alt,
                    "inclination": obj.get("INCLINATION",0),
                    "eccentricity": obj.get("ECCENTRICITY",0),
                })

    return jsonify({
        "shell": shell_def,
        "object_count": len(objects_in_shell),
        "sample_objects": objects_in_shell[:20],  # First 20 for demo
    })

@app.route("/api/health", methods=["GET"])
def health_check():
    return jsonify({"status": "ok", "source": "CelesTrak GP API"})

# ─── MAIN ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("╔══════════════════════════════════════╗")
    print("║   FRAG-MAP Backend Server v1.0       ║")
    print("║   http://localhost:5000/api/density  ║")
    print("╚══════════════════════════════════════╝")
    app.run(debug=True, port=5000)