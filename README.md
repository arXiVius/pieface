# 🥧 PieFace: Secure Presence Tracker
Web-based **face recognition attendance** system with GPS logging, built for schools.  

![Python](https://img.shields.io/badge/Python-3.8+-blue?logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-Backend-black?logo=flask)
![OpenCV](https://img.shields.io/badge/OpenCV-Computer_Vision-green?logo=opencv&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-Database-lightblue?logo=sqlite&logoColor=white)
![Security](https://img.shields.io/badge/Security-Bcrypt%20%7C%20Flask--Login-red)

---

## ✨ Features
- **One-Time Sign-Up** → Register face + password.
- **Live Video Feed** → OpenCV streams your webcam with detection boxes.
- **Instant Verification** → Capture, match face, and log presence.
- **GPS Tracking** → Save location (lat/long) with each log.
- **Persistent DB** → Users + logs stored in SQLite.
- **Secure** → Passwords hashed with Bcrypt + session managed via Flask-Login.

---

## 💻 Stack
| Component | Tech | Why |
|-----------|------|-----|
| Server    | Flask | Simple, lightweight web server |
| Vision    | OpenCV + face-recognition | Fast + accurate face encoding |
| Data      | Flask-SQLAlchemy (SQLite) | Easy persistent storage |
| Security  | Flask-Login + Bcrypt | Safe sessions + password hashing |

---

## 🚀 Quickstart
**Prereqs**: Python 3.8+, webcam, `cmake` (for `dlib`).

```bash
# 1. Clone + Setup
git clone https://github.com/YourUsername/arxivius-pieface.git
cd arxivius-pieface
python3 -m venv venv && source venv/bin/activate

# 2. Install Deps
pip install -r requirements.txt

# 3. Run
python app.py
