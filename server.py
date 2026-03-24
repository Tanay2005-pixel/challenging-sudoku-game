
import json
import hashlib
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn

app = FastAPI(title="Sudoku Duel")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_FILE = Path(__file__).parent


def load_db() -> dict:
    if DB_FILE.exists():
        with open(DB_FILE, "r") as f:
            return json.load(f)
    return {"users": {}}


def save_db(db: dict) -> None:
    with open(DB_FILE, "w") as f:
        json.dump(db, f, indent=2)


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

class RegisterRequest(BaseModel):
    username: str
    displayname: Optional[str] = None
    password: str


class LoginRequest(BaseModel):
    username: str
    password: str


@app.post("/api/register")
def register(req: RegisterRequest):
    """Create a new account."""
    username = req.username.strip().lower()

    if len(username) < 3:
        raise HTTPException(status_code=400, detail="Username must be at least 3 characters.")
    if len(req.password) < 4:
        raise HTTPException(status_code=400, detail="Password must be at least 4 characters.")

    db = load_db()
    if username in db["users"]:
        raise HTTPException(status_code=409, detail="Username already taken.")

    db["users"][username] = {
        "username":    username,
        "name":        req.displayname or username,
        "password":    hash_password(req.password),
        "wins":        0,
        "losses":      0,
        "games":       0,
    }
    save_db(db)

    return {"message": "Account created successfully."}


@app.post("/api/login")
def login(req: LoginRequest):
    """Authenticate and return player profile."""
    username = req.username.strip().lower()

    db = load_db()
    user = db["users"].get(username)

    if not user or user["password"] != hash_password(req.password):
        raise HTTPException(status_code=401, detail="Invalid username or password.")

    player = {
        "id":       username,
        "username": user["username"],
        "name":     user["name"],
        "wins":     user["wins"],
        "losses":   user["losses"],
        "games":    user["games"],
    }
    return {"player": player}


@app.get("/api/player/{username}")
def get_player(username: str):
    """Fetch a player's public profile."""
    db = load_db()
    user = db["users"].get(username.lower())
    if not user:
        raise HTTPException(status_code=404, detail="Player not found.")
    return {
        "username": user["username"],
        "name":     user["name"],
        "wins":     user["wins"],
        "losses":   user["losses"],
        "games":    user["games"],
    }


FRONTEND_DIR = Path(__file__).parent / "frontend_new"


def _serve(filename: str):
    path = FRONTEND_DIR / filename
    if path.exists():
        return FileResponse(str(path))
    return HTMLResponse(
        f"<h2>File not found: {filename}</h2>"
        "<p>Make sure your <code>frontend_new/</code> folder is next to <code>server.py</code>.</p>",
        status_code=404,
    )


@app.get("/")
def root():
    return _serve("index.html")


@app.get("/dashboard")
@app.get("/dashboard.html")
def dashboard():
    return _serve("dashboard.html")


@app.get("/game")
@app.get("/game.html")
def game():
    return _serve("game.html")


@app.get("/lobby")
@app.get("/lobby.html")
def lobby():
    return _serve("lobby.html")


if (FRONTEND_DIR / "css").exists():
    app.mount("/css", StaticFiles(directory=str(FRONTEND_DIR / "css")), name="css")

if (FRONTEND_DIR / "js").exists():
    app.mount("/js", StaticFiles(directory=str(FRONTEND_DIR / "js")), name="js")

if __name__ == "__main__":
    print("=" * 52)
    print("  Sudoku Duel Server")
    print("  http://localhost:8000")
    print("=" * 52)
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
