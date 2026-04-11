# CodePet Backend (clean + fixed routing)

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from pydantic import BaseModel
from datetime import date, timedelta
import math

from database import engine, get_db, Base
from models import Player, CodingSession

app = FastAPI()

# Allow frontend to talk to backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

# 🔥 FIXED ROUTING
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def serve_home():
    return FileResponse("static/index.html")

# ------------------ GAME LOGIC ------------------

EVOLUTIONS = [
    (0,    "🥚", "Egg"),
    (100,  "🐣", "Bitling"),
    (300,  "🐧", "Pixelwing"),
    (700,  "🦊", "Codex Fox"),
    (1400, "🐉", "Dragonbit"),
    (2500, "🌟", "Starforged"),
    (4500, "🔮", "Omnibyte"),
]

def get_evolution(xp: int):
    for min_xp, emoji, title in reversed(EVOLUTIONS):
        if xp >= min_xp:
            return emoji, title
    return "🥚", "Egg"

def calc_xp(mins: int, mood: str) -> int:
    base = math.floor(mins / 10) * 10
    multipliers = {
        "flow": 1.5,
        "stuck": 1.3,
        "explore": 1.2,
        "grind": 1.0
    }
    return round(base * multipliers.get(mood, 1.0))

# ------------------ REQUEST MODELS ------------------

class RegisterRequest(BaseModel):
    username: str
    pet_name: str = "Byte"

class LogSessionRequest(BaseModel):
    username: str
    duration: int
    language: str
    mood: str

# ------------------ STARTUP ------------------

@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

# ------------------ ROUTES ------------------

@app.post("/register")
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(
        select(Player).where(Player.username == req.username)
    )
    if existing.scalar():
        raise HTTPException(status_code=400, detail="Username already taken")

    player = Player(
        username=req.username,
        pet_name=req.pet_name
    )
    db.add(player)
    await db.commit()
    await db.refresh(player)

    return {"message": "Welcome!", "player_id": player.id}


@app.get("/player/{username}")
async def get_player(username: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Player).where(Player.username == username)
    )
    player = result.scalar()

    if not player:
        raise HTTPException(status_code=404, detail="Player not found")

    emoji, title = get_evolution(player.xp)

    return {
        "username": player.username,
        "pet_name": player.pet_name,
        "xp": player.xp,
        "sessions": player.sessions,
        "streak": player.streak,
        "total_mins": player.total_mins,
        "pet_emoji": emoji,
        "pet_title": title,
    }


@app.post("/log")
async def log_session(req: LogSessionRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Player).where(Player.username == req.username)
    )
    player = result.scalar()

    if not player:
        raise HTTPException(status_code=404, detail="Player not found")

    xp_gain = calc_xp(req.duration, req.mood)
    today = str(date.today())

    if player.last_date != today:
        yesterday = str(date.today() - timedelta(days=1))
        player.streak = (
            player.streak + 1 if player.last_date == yesterday else 1
        )
        player.last_date = today

    prev_evo = get_evolution(player.xp)

    player.xp += xp_gain
    player.sessions += 1
    player.total_mins += req.duration
    player.pet_emoji, _ = get_evolution(player.xp)

    session = CodingSession(
        player_id=player.id,
        duration=req.duration,
        language=req.language,
        mood=req.mood,
        xp_gained=xp_gain
    )

    db.add(session)
    await db.commit()

    new_evo = get_evolution(player.xp)
    evolved = new_evo != prev_evo

    return {
        "xp_gained": xp_gain,
        "total_xp": player.xp,
        "streak": player.streak,
        "evolved": evolved,
        "new_form": new_evo[1] if evolved else None,
    }


@app.get("/leaderboard")
async def leaderboard(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Player).order_by(desc(Player.xp)).limit(10)
    )
    players = result.scalars().all()

    return [
        {
            "rank": i + 1,
            "username": p.username,
            "pet_name": p.pet_name,
            "xp": p.xp,
            "streak": p.streak,
            "pet_emoji": get_evolution(p.xp)[0],
            "pet_title": get_evolution(p.xp)[1],
        }
        for i, p in enumerate(players)
    ]
@app.get("/admin/players")
async def get_all_players(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Player))
    players = result.scalars().all()

    return [
        {
            "id": p.id,
            "username": p.username,
            "pet_name": p.pet_name,
            "xp": p.xp,
            "streak": p.streak,
            "total_mins": p.total_mins
        }
        for p in players
    ]


@app.delete("/admin/player/{player_id}")
async def delete_player(player_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Player).where(Player.id == player_id))
    player = result.scalar()

    if not player:
        raise HTTPException(status_code=404, detail="Player not found")

    await db.delete(player)
    await db.commit()

    return {"message": "Player deleted"}
