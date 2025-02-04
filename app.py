from flask import Flask, request, jsonify, render_template, redirect, url_for # type: ignore
import sqlite3
from datetime import datetime

app = Flask(__name__)

DATABASE = "tournaments.db"

# Database setup
def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row  # For dictionary-like access
    return conn

# Initialize the database
def initialize_db():
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Tournaments (
            tournament_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            type TEXT NOT NULL CHECK(type IN ('Singles', 'Doubles')),
            categories TEXT NOT NULL,
            date_from TEXT NOT NULL,
            date_to TEXT NOT NULL,
            courts INTEGER NOT NULL,
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
    conn.close()

# Home Route
@app.route('/')
def home():
    return render_template('home.html')

# Fetch all tournaments
@app.route('/tournaments', methods=['GET'])
def get_tournaments():
    status = request.args.get('status')
    search = request.args.get('search', '')
    conn = get_db()
    cursor = conn.cursor()
    
    query = "SELECT * FROM Tournaments WHERE name LIKE ?"
    params = [f'%{search}%']
    
    current_date = datetime.now().date().isoformat()
    
    if status == 'ongoing':
        query += " AND date_from <= ? AND date_to >= ?"
        params.extend([current_date, current_date])
    elif status == 'recent':
        query += " AND date_to < ? ORDER BY date_to DESC LIMIT 5"
        params.append(current_date)
    
    cursor.execute(query, params)
    tournaments = cursor.fetchall()
    conn.close()
    
    return render_template('tournaments.html', tournaments=tournaments)
  
# Fetch tournament details
@app.route('/tournaments/<int:tournament_id>', methods=['GET'])
def get_tournament_details(tournament_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Tournaments WHERE tournament_id = ?", (tournament_id,))
    tournament = cursor.fetchone()
    
    if tournament:
        cursor.execute("""
            SELECT Players.name FROM Players
            JOIN Players_In_Tournaments ON Players.player_id = Players_In_Tournaments.player_id
            WHERE Players_In_Tournaments.tournament_id = ?
        """, (tournament_id,))
        participants = cursor.fetchall()
        tournament = dict(tournament)
        tournament['participants'] = [participant['name'] for participant in participants] if participants else []
        conn.close()
        return render_template('tournament_details.html', tournament=tournament)
    else:
        conn.close()
        return jsonify({"error": "Tournament not found"}), 404

# Create a new tournament
@app.route('/create_tournament', methods=['GET', 'POST'])
def create_tournament():
    if request.method == 'POST':
        data = request.form
        name = data.get('name')
        type = data.get('type')
        categories = data.get('categories')
        date_from = data.get('date_from')
        date_to = data.get('date_to')
        courts = data.get('courts')
        password = data.get('password')
        
        if not name or not type or not categories or not date_from or not date_to or not courts or not password:
            return jsonify({"error": "Missing required fields"}), 400
        
        conn = get_db()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO Tournaments (name, type, categories, date_from, date_to, courts, password)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (name, type, categories, date_from, date_to, courts, password))
            conn.commit()
            conn.close()
            return redirect(url_for('home'))
        except sqlite3.IntegrityError:
            conn.close()
            return jsonify({"error": "Tournament name already exists"}), 400
    
    return render_template('create_tournament.html')

#Create new player
@app.route('/create_player', methods=['POST'])
def create_player():
    if request.method == 'POST':
        data = request.json  # Expecting JSON input
        first_name = data.get('first_name')
        last_name = data.get('last_name')
        club = data.get('club', None)  # Default to None if not provided

        if not first_name or not last_name:
            return jsonify({'error': 'Missing required fields'}), 400

        conn = get_db()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO Players (first_name, last_name, club)
                VALUES (?, ?, ?)
            """, (first_name, last_name, club))
            conn.commit()
            conn.close()
            return jsonify({'message': 'Player created successfully'}), 201
        except sqlite3.IntegrityError:
            conn.close()
            return jsonify({'error': 'Player already exists'}), 400

    return render_template('create_player.html')

if __name__ == '__main__':
    initialize_db()
    app.run(debug=True)
