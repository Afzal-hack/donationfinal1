"""
mrAvzal Donation — main.py (Backend)
=====================================
Papka strukturasi:
  project/
  ├── main.py               ← shu fayl (backend)
  ├── requirements.txt
  ├── vercel.json
  ├── .gitignore
  ├── donations.json        ← avtomatik yaratiladi
  ├── templates/
  │   └── index.html        ← asosiy sahifa
  └── static/
      ├── css/
      │   └── style.css
      ├── js/
      │   └── main.js
      └── images/           ← rasm va favicon

API endpoints:
  GET  /                          → index.html
  POST /api/donations             → yangi donation
  POST /api/admin/login           → token olish
  GET  /api/admin/donations       → barcha xabarlar
  DELETE /api/admin/donations/{id}→ bitta o'chirish
  DELETE /api/admin/donations     → hammasini o'chirish
"""

import os, json, uuid, time, hashlib, secrets
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel

# ─── CONFIG ──────────────────────────────────────────
ADMIN_PASSWORD   = os.getenv("ADMIN_PASSWORD", "YOUR_PASSWORD_HERE")
SECRET_KEY       = os.getenv("SECRET_KEY",     secrets.token_hex(32))
DATA_FILE        = Path("donations.json")
AUTO_DELETE_MINS = int(os.getenv("AUTO_DELETE_MINS", "10"))
BASE_DIR         = Path(__file__).parent
# ─────────────────────────────────────────────────────

app = FastAPI(title="mrAvzal Donation API", docs_url=None, redoc_url=None)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Static fayllarni ulash (/static/css, /static/js, /static/images)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")


# ─── DATA HELPERS ────────────────────────────────────
def load_data() -> list:
    if not DATA_FILE.exists():
        return []
    try:
        return json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []

def save_data(donations: list) -> None:
    DATA_FILE.write_text(
        json.dumps(donations, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

def purge_expired(donations: list) -> list:
    now = datetime.now(timezone.utc)
    return [d for d in donations
            if datetime.fromisoformat(d["expires_at"]) > now]


# ─── TOKEN AUTH ──────────────────────────────────────
_tokens: dict[str, float] = {}

def create_token() -> str:
    token = secrets.token_urlsafe(32)
    _tokens[token] = time.time() + 3600
    return token

def verify_token(authorization: Optional[str] = Header(None)) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Token kerak")
    token = authorization.split(" ", 1)[1]
    exp = _tokens.get(token)
    if not exp or time.time() > exp:
        raise HTTPException(401, "Token eskirgan")
    return token


# ─── SCHEMAS ─────────────────────────────────────────
class DonationIn(BaseModel):
    name:     str
    amount:   float
    currency: str
    message:  str = ""

class LoginIn(BaseModel):
    password: str


# ─── ROUTES ──────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
def serve_index():
    """HTML sahifani qaytaradi."""
    html_file = BASE_DIR / "templates" / "index.html"
    return HTMLResponse(content=html_file.read_text(encoding="utf-8"))


@app.post("/api/donations", status_code=201)
def create_donation(body: DonationIn):
    """Yangi donation qabul qiladi va saqlaydi."""
    if body.amount <= 0:
        raise HTTPException(400, "Summa noto'g'ri")
    if body.currency not in ("UZS", "USD"):
        raise HTTPException(400, "Valyuta noto'g'ri")

    donations = purge_expired(load_data())

    now = datetime.now(timezone.utc)
    entry = {
        "id":         str(uuid.uuid4()),
        "name":       (body.name or "Anonymous")[:40],
        "amount":     round(body.amount, 2),
        "currency":   body.currency,
        "message":    body.message[:300],
        "created_at": now.isoformat(),
        "expires_at": (now + timedelta(minutes=AUTO_DELETE_MINS)).isoformat(),
    }
    donations.insert(0, entry)
    save_data(donations)
    return {"ok": True, "id": entry["id"]}


@app.post("/api/admin/login")
def admin_login(body: LoginIn):
    """Parolni tekshirib token qaytaradi."""
    expected = hashlib.sha256(ADMIN_PASSWORD.encode()).digest()
    given    = hashlib.sha256(body.password.encode()).digest()
    if not secrets.compare_digest(expected, given):
        raise HTTPException(401, "Noto'g'ri parol")
    return {"token": create_token()}


@app.get("/api/admin/donations")
def get_donations(token: str = Depends(verify_token)):
    """Barcha xabarlarni qaytaradi (eskilarini tozalab)."""
    donations = purge_expired(load_data())
    save_data(donations)

    total_uzs = sum(
        d["amount"] if d["currency"] == "UZS" else d["amount"] * 12500
        for d in donations
    )
    return {
        "donations": donations,
        "stats": {
            "count":     len(donations),
            "total_uzs": round(total_uzs),
        }
    }


@app.delete("/api/admin/donations/{donation_id}")
def delete_one(donation_id: str, token: str = Depends(verify_token)):
    """Bitta xabarni o'chiradi."""
    donations = load_data()
    filtered  = [d for d in donations if d["id"] != donation_id]
    if len(filtered) == len(donations):
        raise HTTPException(404, "Topilmadi")
    save_data(filtered)
    return {"ok": True}


@app.delete("/api/admin/donations")
def delete_all(token: str = Depends(verify_token)):
    """Barcha xabarlarni o'chiradi."""
    save_data([])
    return {"ok": True}


# ─── LOCAL RUN ───────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    print("\n🚀  http://localhost:8000  da oching\n")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
