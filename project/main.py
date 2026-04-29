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

import os, json, uuid, time, hashlib, secrets, logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel

# ─── LOGGING ──────────────────────────────────────────
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ─── CONFIG ──────────────────────────────────────────
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")
if not ADMIN_PASSWORD:
    raise ValueError("❌ ADMIN_PASSWORD environment variable is required!")

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    logger.warning("⚠️ SECRET_KEY not set - using generated key (not recommended for production)")
    SECRET_KEY = secrets.token_hex(32)

ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
DATA_FILE = Path("donations.json")
AUTO_DELETE_MINS = int(os.getenv("AUTO_DELETE_MINS", "10"))
BASE_DIR = Path(__file__).parent
TOKEN_EXPIRE_MINS = 60
# ─────────────────────────────────────────────────────

app = FastAPI(title="mrAvzal Donation API", docs_url=None, redoc_url=None)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Content-Type", "Authorization"],
)

# ── Static fayllarni ulash (/static/css, /static/js, /static/images)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")


# ─── DATA HELPERS ────────────────────────────────────
def load_data() -> list:
    if not DATA_FILE.exists():
        return []
    try:
        data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except json.JSONDecodeError as e:
        logger.error(f"JSON parse error in donations.json: {e}")
        return []
    except Exception as e:
        logger.error(f"Error loading data: {e}")
        return []

def save_data(donations: list) -> None:
    try:
        DATA_FILE.write_text(
            json.dumps(donations, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
    except Exception as e:
        logger.error(f"Error saving data: {e}")
        raise HTTPException(500, "Ma'lumotlarni saqlash xatosi")

def purge_expired(donations: list) -> list:
    now = datetime.now(timezone.utc)
    cleaned = []
    for d in donations:
        try:
            if datetime.fromisoformat(d.get("expires_at", "")) > now:
                cleaned.append(d)
        except (ValueError, TypeError) as e:
            logger.warning(f"Invalid expires_at format for donation {d.get('id')}: {e}")
            continue
    return cleaned


# ─── TOKEN AUTH ──────────────────────────────────────
_tokens: dict[str, float] = {}

def cleanup_expired_tokens():
    """Remove expired tokens from memory."""
    now = time.time()
    expired = [k for k, v in _tokens.items() if v <= now]
    for k in expired:
        del _tokens[k]
    if expired:
        logger.info(f"Cleaned up {len(expired)} expired tokens")


def create_token() -> str:
    cleanup_expired_tokens()
    token = secrets.token_urlsafe(32)
    _tokens[token] = time.time() + (TOKEN_EXPIRE_MINS * 60)
    logger.info(f"Token created (total tokens: {len(_tokens)})")
    return token


def verify_token(authorization: Optional[str] = Header(None)) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Token kerak")
    token = authorization.split(" ", 1)[1]
    exp = _tokens.get(token)
    if not exp or time.time() > exp:
        logger.warning(f"Invalid/expired token attempt")
        raise HTTPException(401, "Token eskirgan yoki noto'g'ri")
    return token


# ─── SCHEMAS ─────────────────────────────────────────
class DonationIn(BaseModel):
    name: str
    amount: float
    currency: str
    message: str = ""

class LoginIn(BaseModel):
    password: str


# ─── ROUTES ──────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
def serve_index():
    """HTML sahifani qaytaradi."""
    html_file = BASE_DIR / "templates" / "index.html"
    try:
        if not html_file.exists():
            logger.error(f"HTML file not found: {html_file}")
            raise HTTPException(404, "index.html topilmadi")
        return HTMLResponse(content=html_file.read_text(encoding="utf-8"))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error serving index: {e}")
        raise HTTPException(500, "Sahifani yuklashda xato")


@app.post("/api/donations", status_code=201)
def create_donation(body: DonationIn):
    """Yangi donation qabul qiladi va saqlaydi."""
    # Validate name
    if not body.name or not body.name.strip():
        raise HTTPException(400, "Ism bo'sh bo'lishi mumkin emas")
    
    if body.amount <= 0:
        raise HTTPException(400, "Summa noto'g'ri (0 dan katta bo'lishi kerak)")
    
    if body.currency not in ("UZS", "USD"):
        raise HTTPException(400, "Valyuta noto'g'ri (UZS yoki USD)")

    try:
        donations = purge_expired(load_data())

        now = datetime.now(timezone.utc)
        entry = {
            "id": str(uuid.uuid4()),
            "name": body.name.strip()[:40],
            "amount": round(body.amount, 2),
            "currency": body.currency,
            "message": body.message[:300],
            "created_at": now.isoformat(),
            "expires_at": (now + timedelta(minutes=AUTO_DELETE_MINS)).isoformat(),
        }
        donations.insert(0, entry)
        save_data(donations)
        logger.info(f"Donation created: {entry['id']} by {entry['name']}")
        return {"ok": True, "id": entry["id"]}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating donation: {e}")
        raise HTTPException(500, "Donatsiyani saqlashda xato")


@app.post("/api/admin/login")
def admin_login(body: LoginIn):
    """Parolni tekshirib token qaytaradi."""
    try:
        expected = hashlib.sha256(ADMIN_PASSWORD.encode()).digest()
        given = hashlib.sha256(body.password.encode()).digest()
        if not secrets.compare_digest(expected, given):
            logger.warning("Failed login attempt with incorrect password")
            raise HTTPException(401, "Noto'g'ri parol")
        token = create_token()
        logger.info("Admin login successful")
        return {"token": token}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during login: {e}")
        raise HTTPException(500, "Login xatosi")


@app.get("/api/admin/donations")
def get_donations(token: str = Depends(verify_token)):
    """Barcha xabarlarni qaytaradi (eskilarini tozalab)."""
    try:
        donations = purge_expired(load_data())
        save_data(donations)

        total_uzs = 0
        for d in donations:
            try:
                if d.get("currency") == "UZS":
                    total_uzs += d.get("amount", 0)
                else:
                    total_uzs += d.get("amount", 0) * 12500
            except (TypeError, ValueError):
                logger.warning(f"Invalid amount for donation {d.get('id')}")
                continue

        return {
            "donations": donations,
            "stats": {
                "count": len(donations),
                "total_uzs": round(total_uzs),
            }
        }
    except Exception as e:
        logger.error(f"Error fetching donations: {e}")
        raise HTTPException(500, "Donatsiyalarni yuklashda xato")


@app.delete("/api/admin/donations/{donation_id}")
def delete_one(donation_id: str, token: str = Depends(verify_token)):
    """Bitta xabarni o'chiradi."""
    try:
        donations = load_data()
        filtered = [d for d in donations if d.get("id") != donation_id]
        if len(filtered) == len(donations):
            raise HTTPException(404, "Donation topilmadi")
        save_data(filtered)
        logger.info(f"Donation deleted: {donation_id}")
        return {"ok": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting donation: {e}")
        raise HTTPException(500, "Donatsiyani o'chirishda xato")


@app.delete("/api/admin/donations")
def delete_all(token: str = Depends(verify_token)):
    """Barcha xabarlarni o'chiradi."""
    try:
        save_data([])
        logger.info("All donations deleted")
        return {"ok": True}
    except Exception as e:
        logger.error(f"Error deleting all donations: {e}")
        raise HTTPException(500, "Barcha donatsiyalarni o'chirishda xato")


# ─── LOCAL RUN ───────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    print("\n🚀  http://localhost:8000  da oching\n")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)