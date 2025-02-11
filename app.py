from flask import Flask, request, jsonify, render_template, redirect, url_for
import sqlite3
from datetime import datetime
from flask import session, redirect, url_for, request, jsonify, render_template
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
app = Flask(__name__)

app.secret_key = "your_secret_key"  # Change this to a secure key

DATABASE = "tournaments.db"

def get_db():
    conn = sqlite3.connect("tournaments.db")
    conn.row_factory = sqlite3.Row
    return conn

# ---------------- AUTH ROUTES ----------------

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        hashed_password = generate_password_hash(password)

        conn = get_db()
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO Users (username, password) VALUES (?, ?)", (username, hashed_password))
            conn.commit()
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            return jsonify({"error": "Username already exists"}), 400
        finally:
            conn.close()

    return render_template("auth.html", action="register")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Users WHERE username = ?", (username,))
        user = cursor.fetchone()
        conn.close()

        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["user_id"]
            session["username"] = user["username"]
            return redirect(url_for("home"))
        else:
            return jsonify({"error": "Invalid credentials"}), 400

    return render_template("auth.html", action="login")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# ---------------- PROTECT TOURNAMENT ROUTES ----------------

@app.before_request
def require_login():
    """ Protect tournament management routes """
    protected_routes = ["/manage_tournament", "/add_player_to_tournament"]
    if any(request.path.startswith(route) for route in protected_routes) and "user_id" not in session:
        return redirect(url_for("login"))



def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

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
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            club TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Players_In_Tournaments (
            player_id INTEGER NOT NULL,
            tournament_id INTEGER NOT NULL,
            partner_id INTEGER,
            FOREIGN KEY (player_id) REFERENCES Players (player_id),
            FOREIGN KEY (tournament_id) REFERENCES Tournaments (tournament_id),
            FOREIGN KEY (partner_id) REFERENCES Players (player_id)
        )
    """)
    
    conn.commit()
    conn.close()

@app.route('/')
def home():
    return render_template('home.html')

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

@app.route('/tournaments/<int:tournament_id>', methods=['GET'])
def get_tournament_details(tournament_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Tournaments WHERE tournament_id = ?", (tournament_id,))
    tournament = cursor.fetchone()
    
    if tournament:
        cursor.execute("""
            SELECT Players.first_name || ' ' || Players.last_name AS name FROM Players
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

@app.route('/manage_tournament/<int:tournament_id>', methods=['GET'])
def manage_tournament(tournament_id):
    password = request.args.get('password')
    if not password:
        return jsonify({"error": "Password required"}), 400
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Tournaments WHERE tournament_id = ?", (tournament_id,))
    tournament = cursor.fetchone()
    
    if tournament and tournament['password'] == password:
        conn.close()
        return render_template('manage_tournament.html', tournament=tournament)
    else:
        conn.close()
        return jsonify({"error": "Incorrect password"}), 403

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

@app.route('/create_player', methods=['GET', 'POST'])
def create_player():
    if request.method == 'POST':
        data = request.form
        first_name = data.get('first_name')
        last_name = data.get('last_name')
        club = data.get('club', None)

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


@app.route('/search_player/<int:tournament_id>', methods=['GET', 'POST'])
def search_player(tournament_id):
    conn = get_db()
    cursor = conn.cursor()

    if request.method == 'POST':
        search_query = request.form.get('search')
        if search_query:
            # Searching by first name or last name
            cursor.execute("""
                SELECT player_id, first_name, last_name FROM Players
                WHERE first_name LIKE ? OR last_name LIKE ?
            """, (f'%{search_query}%', f'%{search_query}%'))
            players = cursor.fetchall()
        else:
            players = []
    else:
        players = []

    conn.close()
    return render_template('search_player.html', tournament_id=tournament_id, players=players)

@app.route('/add_player_to_tournament/<int:tournament_id>/<int:player_id>', methods=['GET'])
def add_player_to_tournament(tournament_id, player_id):
    conn = get_db()
    cursor = conn.cursor()
    
    # Check if the player is already in the tournament
    cursor.execute("""
        SELECT * FROM Players_In_Tournaments
        WHERE player_id = ? AND tournament_id = ?
    """, (player_id, tournament_id))
    existing_entry = cursor.fetchone()

    if existing_entry:
        conn.close()
        return jsonify({"error": "Player already in this tournament"}), 400

    cursor.execute("""
        INSERT INTO Players_In_Tournaments (player_id, tournament_id)
        VALUES (?, ?)
    """, (player_id, tournament_id))
    conn.commit()
    conn.close()

    return redirect(url_for('manage_tournament', tournament_id=tournament_id))




if __name__ == '__main__':
    initialize_db()
    app.run(debug=True)
