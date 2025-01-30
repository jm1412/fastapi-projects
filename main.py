from fastapi import FastAPI, HTTPException
from asgiref.wsgi import WsgiToAsgi
import sqlite3
from pydantic import BaseModel
from typing import List

# Create the FastAPI app
app = FastAPI()

# Database setup
DATABASE = "tournaments.db"

def get_db():
    conn = sqlite3.connect(DATABASE, check_same_thread=False)
    conn.row_factory = sqlite3.Row  # For dictionary-like access
    return conn

# Initialize database
def initialize_db():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Tournaments (
            tournament_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            type TEXT NOT NULL CHECK(type IN ('Singles', 'Doubles')),
            password TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Players (
            player_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Players_In_Tournaments (
            player_id INTEGER NOT NULL,
            tournament_id INTEGER NOT NULL,
            partner_id INTEGER,  -- For doubles, NULL for singles
            FOREIGN KEY (player_id) REFERENCES Players (player_id),
            FOREIGN KEY (tournament_id) REFERENCES Tournaments (tournament_id),
            FOREIGN KEY (partner_id) REFERENCES Players (player_id)
        )
    """)
    conn.commit()

# Initialize the database when the app starts
initialize_db()

# Pydantic models for request validation
class TournamentCreate(BaseModel):
    name: str
    type: str
    password: str

class PlayerCreate(BaseModel):
    name: str

class PlayerInTournament(BaseModel):
    player_id: int
    tournament_id: int
    partner_id: int = None

# Endpoints
@app.get("/")
def read_root():
    return {"message": "Welcome to the Badminton Tournament API!"}

@app.post("/tournaments", response_model=dict)
def create_tournament(tournament: TournamentCreate):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO Tournaments (name, type, password)
            VALUES (?, ?, ?)
        """, (tournament.name, tournament.type, tournament.password))
        conn.commit()
        return {"message": "Tournament created successfully!"}
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Tournament name already exists.")

@app.get("/tournaments", response_model=List[dict])
def get_tournaments():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Tournaments")
    tournaments = cursor.fetchall()
    return [dict(tournament) for tournament in tournaments]

@app.post("/players", response_model=dict)
def create_player(player: PlayerCreate):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO Players (name)
        VALUES (?)
    """, (player.name,))
    conn.commit()
    return {"message": "Player created successfully!"}

@app.get("/players", response_model=List[dict])
def get_players():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Players")
    players = cursor.fetchall()
    return [dict(player) for player in players]

@app.post("/players_in_tournaments", response_model=dict)
def add_player_to_tournament(player_tournament: PlayerInTournament):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO Players_In_Tournaments (player_id, tournament_id, partner_id)
        VALUES (?, ?, ?)
    """, (player_tournament.player_id, player_tournament.tournament_id, player_tournament.partner_id))
    conn.commit()
    return {"message": "Player added to tournament successfully!"}

# Wrap the FastAPI app with WSGIMiddleware
application = WsgiToAsgi(app)