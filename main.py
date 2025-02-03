from flask import Flask, request, jsonify
import sqlite3

app = Flask(__name__)

# Database setup
DATABASE = "tournaments.db"

def get_db():
    conn = sqlite3.connect(DATABASE)
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

# Routes
@app.route("/")
def home():
    return jsonify({"message": "Welcome to the Badminton Tournament API!"})

@app.route("/tournaments", methods=["GET", "POST"])
def tournaments():
    conn = get_db()
    cursor = conn.cursor()

    if request.method == "GET":
        # Get all tournaments
        cursor.execute("SELECT * FROM Tournaments")
        tournaments = cursor.fetchall()
        return jsonify([dict(tournament) for tournament in tournaments])

    elif request.method == "POST":
        # Create a new tournament
        data = request.get_json()
        name = data.get("name")
        type = data.get("type")
        password = data.get("password")

        if not name or not type or not password:
            return jsonify({"error": "Missing required fields"}), 400

        try:
            cursor.execute("""
                INSERT INTO Tournaments (name, type, password)
                VALUES (?, ?, ?)
            """, (name, type, password))
            conn.commit()
            return jsonify({"message": "Tournament created successfully!"}), 201
        except sqlite3.IntegrityError:
            return jsonify({"error": "Tournament name already exists"}), 400

@app.route("/tournaments/<int:tournament_id>", methods=["GET"])
def tournament_details(tournament_id):
    conn = get_db()
    cursor = conn.cursor()

    # Get tournament details
    cursor.execute("SELECT * FROM Tournaments WHERE tournament_id = ?", (tournament_id,))
    tournament = cursor.fetchone()
    if not tournament:
        return jsonify({"error": "Tournament not found"}), 404

    # Get players in the tournament
    cursor.execute("""
        SELECT p.player_id, p.name, pit.partner_id
        FROM Players p
        JOIN Players_In_Tournaments pit ON p.player_id = pit.player_id
        WHERE pit.tournament_id = ?
    """, (tournament_id,))
    players = cursor.fetchall()

    return jsonify({
        "tournament": dict(tournament),
        "players": [dict(player) for player in players]
    })

@app.route("/players", methods=["GET", "POST"])
def players():
    conn = get_db()
    cursor = conn.cursor()

    if request.method == "GET":
        # Get all players
        cursor.execute("SELECT * FROM Players")
        players = cursor.fetchall()
        return jsonify([dict(player) for player in players])

    elif request.method == "POST":
        # Create a new player
        data = request.get_json()
        name = data.get("name")

        if not name:
            return jsonify({"error": "Missing player name"}), 400

        cursor.execute("""
            INSERT INTO Players (name)
            VALUES (?)
        """, (name,))
        conn.commit()
        return jsonify({"message": "Player created successfully!"}), 201

@app.route("/tournaments/<int:tournament_id>/add_player", methods=["POST"])
def add_player_to_tournament(tournament_id):
    conn = get_db()
    cursor = conn.cursor()

    data = request.get_json()
    player_id = data.get("player_id")
    partner_id = data.get("partner_id")  # For doubles, optional

    if not player_id:
        return jsonify({"error": "Missing player ID"}), 400

    # Check if the player is already in the tournament
    cursor.execute("""
        SELECT * FROM Players_In_Tournaments
        WHERE tournament_id = ? AND player_id = ?
    """, (tournament_id, player_id))
    if cursor.fetchone():
        return jsonify({"error": "Player already in tournament"}), 400

    # Add player to tournament
    cursor.execute("""
        INSERT INTO Players_In_Tournaments (player_id, tournament_id, partner_id)
        VALUES (?, ?, ?)
    """, (player_id, tournament_id, partner_id))
    conn.commit()
    return jsonify({"message": "Player added to tournament successfully!"}), 201

# Run the app
if __name__ == "__main__":
    app.run(debug=True)