

import mysql.connector
from mysql.connector import Error, pooling
from typing import Optional, Dict, List, Tuple
import hashlib
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
import random
import string
import json

load_dotenv()

# Database configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', 3306)),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', ''),
    'database': os.getenv('DB_NAME', 'sudoku_duel'),
    'pool_name': 'sudoku_pool',
    'pool_size': 5
}

# Connection pool
connection_pool = None


def init_db_pool():
    """start database connection pool"""
    global connection_pool
    try:
        connection_pool = pooling.MySQLConnectionPool(**DB_CONFIG)
        print("Database connection pool created successfully")
        return True
    except Error as e:
        print(f"Error creating connection pool: {e}")
        return False


def get_connection():
    """get a connection from the pool"""
    try:
        return connection_pool.get_connection()
    except Error as e:
        print(f"Error getting connection from pool: {e}")
        return None


def hash_password(password: str) -> str:
    """turn password into hash"""
    return hashlib.sha256(password.encode()).hexdigest()


# user account functions

def create_user(username: str, password: str, display_name: Optional[str] = None, 
                email: Optional[str] = None) -> Tuple[bool, str, Optional[int]]:
    """
    make a new user account
    Returns: (success, message, user_id)
    """
    conn = get_connection()
    if not conn:
        return False, "Database connection failed", None
    
    try:
        cursor = conn.cursor()
        password_hash = hash_password(password)
        display_name = display_name or username
        
        query = """
            INSERT INTO users (username, display_name, password_hash, email)
            VALUES (%s, %s, %s, %s)
        """
        cursor.execute(query, (username.lower(), display_name, password_hash, email))
        conn.commit()
        
        user_id = cursor.lastrowid
        
        # create stats for new user
        cursor.execute("INSERT INTO user_stats (user_id) VALUES (%s)", (user_id,))
        conn.commit()
        
        cursor.close()
        return True, "User created successfully", user_id
        
    except Error as e:
        if e.errno == 1062:  # Duplicate entry
            return False, "Username already exists", None
        return False, f"Database error: {str(e)}", None
    finally:
        conn.close()


def authenticate_user(username: str, password: str) -> Tuple[bool, Optional[Dict]]:
    """
    check if username and password are correct
    Returns: (success, user_data)
    """
    conn = get_connection()
    if not conn:
        return False, None
    
    try:
        cursor = conn.cursor(dictionary=True)
        password_hash = hash_password(password)
        
        query = """
            SELECT u.user_id, u.username, u.display_name, u.email, u.created_at,
                   us.total_games, us.total_wins, us.total_losses, us.win_rate,
                   us.total_score, us.best_time_9x9
            FROM users u
            LEFT JOIN user_stats us ON u.user_id = us.user_id
            WHERE u.username = %s AND u.password_hash = %s AND u.is_active = TRUE
        """
        cursor.execute(query, (username.lower(), password_hash))
        user = cursor.fetchone()
        
        if user:
            # save last login time
            cursor.execute(
                "UPDATE users SET last_login = NOW() WHERE user_id = %s",
                (user['user_id'],)
            )
            conn.commit()
            cursor.close()
            return True, user
        
        cursor.close()
        return False, None
        
    except Error as e:
        print(f"Authentication error: {e}")
        return False, None
    finally:
        conn.close()


def get_user_profile(user_id: int) -> Optional[Dict]:
    """get user profile with stats"""
    conn = get_connection()
    if not conn:
        return None
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        query = """
            SELECT u.user_id, u.username, u.display_name, u.created_at,
                   us.total_games, us.total_wins, us.total_losses, us.win_rate,
                   us.total_score, us.average_score,
                   us.best_time_4x4, us.best_time_9x9, us.best_time_16x16
            FROM users u
            LEFT JOIN user_stats us ON u.user_id = us.user_id
            WHERE u.user_id = %s AND u.is_active = TRUE
        """
        cursor.execute(query, (user_id,))
        user = cursor.fetchone()
        cursor.close()
        return user
        
    except Error as e:
        print(f"Error fetching user profile: {e}")
        return None
    finally:
        conn.close()


# game result functions

def save_game_result(user_id: int, board_size: int, difficulty: int,
                     time_seconds: int, hints_used: int, errors_made: int,
                     completed: bool) -> Tuple[bool, Optional[int]]:
    """
    save game result and update player stats
    Returns: (success, game_id)
    """
    conn = get_connection()
    if not conn:
        return False, None
    
    try:
        cursor = conn.cursor()
        
        # calculate points
        score = calculate_score(board_size, difficulty, time_seconds, 
                               hints_used, errors_made, completed)
        
        # save game to history
        query = """
            INSERT INTO game_history 
            (user_id, board_size, difficulty, time_seconds, hints_used, 
             errors_made, completed, score)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(query, (user_id, board_size, difficulty, time_seconds,
                              hints_used, errors_made, completed, score))
        game_id = cursor.lastrowid
        
        # update player stats using database procedure
        cursor.callproc('update_user_stats', 
                       (user_id, board_size, time_seconds, completed, score))
        
        conn.commit()
        cursor.close()
        return True, game_id
        
    except Error as e:
        print(f"Error saving game result: {e}")
        conn.rollback()
        return False, None
    finally:
        conn.close()


def calculate_score(board_size: int, difficulty: int, time_seconds: int,
                   hints_used: int, errors_made: int, completed: bool) -> int:
    """calculate player score based on performance"""
    if not completed:
        return 0
    
    # bigger puzzle = more base points
    base_scores = {4: 200, 9: 500, 16: 1000}
    base_score = base_scores.get(board_size, 500)
    
    # harder difficulty = more points
    difficulty_multipliers = {1: 1.0, 2: 1.5, 3: 2.0}
    multiplier = difficulty_multipliers.get(difficulty, 1.0)
    
    # faster time = bonus points
    time_targets = {4: 60, 9: 300, 16: 900}
    target_time = time_targets.get(board_size, 300)
    time_bonus = max(0, (target_time - time_seconds) * 0.5)
    
    # hints and errors reduce points
    hint_penalty = hints_used * 50
    error_penalty = errors_made * 30
    
    # calculate final score
    score = int((base_score + time_bonus - hint_penalty - error_penalty) * multiplier)
    return max(0, score)


def get_user_game_history(user_id: int, limit: int = 10) -> List[Dict]:
    """get past games for a player"""
    conn = get_connection()
    if not conn:
        return []
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        query = """
            SELECT game_id, board_size, difficulty, time_seconds, 
                   hints_used, errors_made, completed, score, played_at
            FROM game_history
            WHERE user_id = %s
            ORDER BY played_at DESC
            LIMIT %s
        """
        cursor.execute(query, (user_id, limit))
        games = cursor.fetchall()
        cursor.close()
        return games
        
    except Error as e:
        print(f"Error fetching game history: {e}")
        return []
    finally:
        conn.close()


# leaderboard functions

def get_global_leaderboard(limit: int = 100) -> List[Dict]:
    """get overall top players"""
    conn = get_connection()
    if not conn:
        return []
    
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM leaderboard_global LIMIT %s", (limit,))
        leaderboard = cursor.fetchall()
        cursor.close()
        return leaderboard
        
    except Error as e:
        print(f"Error fetching global leaderboard: {e}")
        return []
    finally:
        conn.close()


def get_weekly_leaderboard(limit: int = 100) -> List[Dict]:
    """get top players this week"""
    conn = get_connection()
    if not conn:
        return []
    
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM leaderboard_weekly LIMIT %s", (limit,))
        leaderboard = cursor.fetchall()
        cursor.close()
        return leaderboard
        
    except Error as e:
        print(f"Error fetching weekly leaderboard: {e}")
        return []
    finally:
        conn.close()


def get_friends_leaderboard(user_id: int) -> List[Dict]:
    """get leaderboard of your friends"""
    conn = get_connection()
    if not conn:
        return []
    
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.callproc('get_friends_leaderboard', (user_id,))
        
        # get results from database procedure
        for result in cursor.stored_results():
            leaderboard = result.fetchall()
            cursor.close()
            return leaderboard
        
        cursor.close()
        return []
        
    except Error as e:
        print(f"Error fetching friends leaderboard: {e}")
        return []
    finally:
        conn.close()


def get_user_rank(user_id: int) -> Optional[Dict]:
    """get your rank in leaderboard"""
    conn = get_connection()
    if not conn:
        return None
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        query = """
            SELECT rank_position, total_score, win_rate, total_wins
            FROM leaderboard_global
            WHERE user_id = %s
        """
        cursor.execute(query, (user_id,))
        rank = cursor.fetchone()
        cursor.close()
        return rank
        
    except Error as e:
        print(f"Error fetching user rank: {e}")
        return None
    finally:
        conn.close()


# friend management functions

def send_friend_request(user_id: int, friend_username: str) -> Tuple[bool, str]:
    """send friend request to another player"""
    conn = get_connection()
    if not conn:
        return False, "Database connection failed"
    
    try:
        cursor = conn.cursor()
        
        # find friend by username
        cursor.execute("SELECT user_id FROM users WHERE username = %s", 
                      (friend_username.lower(),))
        result = cursor.fetchone()
        
        if not result:
            cursor.close()
            return False, "User not found"
        
        friend_id = result[0]
        
        if user_id == friend_id:
            cursor.close()
            return False, "Cannot add yourself as friend"
        
        # add friendship to database
        query = """
            INSERT INTO friendships (user_id, friend_id, status)
            VALUES (%s, %s, 'pending')
        """
        cursor.execute(query, (user_id, friend_id))
        conn.commit()
        cursor.close()
        return True, "Friend request sent"
        
    except Error as e:
        if e.errno == 1062:  # Duplicate entry
            return False, "Friend request already exists"
        return False, f"Database error: {str(e)}"
    finally:
        conn.close()


def accept_friend_request(user_id: int, friend_id: int) -> Tuple[bool, str]:
    """accept a friend request"""
    conn = get_connection()
    if not conn:
        return False, "Database connection failed"
    
    try:
        cursor = conn.cursor()
        
        # change status to accepted
        query = """
            UPDATE friendships 
            SET status = 'accepted'
            WHERE user_id = %s AND friend_id = %s AND status = 'pending'
        """
        cursor.execute(query, (friend_id, user_id))
        
        # make friendship work both ways
        query2 = """
            INSERT INTO friendships (user_id, friend_id, status)
            VALUES (%s, %s, 'accepted')
            ON DUPLICATE KEY UPDATE status = 'accepted'
        """
        cursor.execute(query2, (user_id, friend_id))
        
        conn.commit()
        cursor.close()
        return True, "Friend request accepted"
        
    except Error as e:
        return False, f"Database error: {str(e)}"
    finally:
        conn.close()


def get_friends_list(user_id: int) -> List[Dict]:
    """get list of your friends"""
    conn = get_connection()
    if not conn:
        return []
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        query = """
            SELECT u.user_id, u.username, u.display_name,
                   us.total_wins, us.total_games, us.win_rate,
                   f.status, f.created_at as friend_since
            FROM friendships f
            INNER JOIN users u ON f.friend_id = u.user_id
            LEFT JOIN user_stats us ON u.user_id = us.user_id
            WHERE f.user_id = %s AND f.status = 'accepted'
            ORDER BY u.display_name
        """
        cursor.execute(query, (user_id,))
        friends = cursor.fetchall()
        cursor.close()
        return friends
        
    except Error as e:
        print(f"Error fetching friends list: {e}")
        return []
    finally:
        conn.close()


def get_pending_friend_requests(user_id: int) -> List[Dict]:
    """get friend requests waiting for you"""
    conn = get_connection()
    if not conn:
        return []
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        query = """
            SELECT u.user_id, u.username, u.display_name,
                   us.total_wins, us.total_games, us.win_rate,
                   f.friendship_id, f.created_at
            FROM friendships f
            INNER JOIN users u ON f.user_id = u.user_id
            LEFT JOIN user_stats us ON u.user_id = us.user_id
            WHERE f.friend_id = %s AND f.status = 'pending'
            ORDER BY f.created_at DESC
        """
        cursor.execute(query, (user_id,))
        requests = cursor.fetchall()
        cursor.close()
        return requests
        
    except Error as e:
        print(f"Error fetching pending requests: {e}")
        return []
    finally:
        conn.close()


def get_recommendations(user_id: int, limit: int = 10) -> List[Dict]:
    """get suggested friends based on mutual friends"""
    conn = get_connection()
    if not conn:
        return []
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        # find friends of friends
        query = """
            SELECT DISTINCT 
                u.user_id, u.username, u.display_name,
                us.total_wins, us.total_games, us.win_rate,
                COUNT(DISTINCT f2.user_id) as mutual_friends
            FROM users u
            LEFT JOIN user_stats us ON u.user_id = us.user_id
            INNER JOIN friendships f1 ON f1.friend_id = u.user_id
            INNER JOIN friendships f2 ON f2.user_id = f1.user_id AND f2.friend_id = %s
            WHERE u.user_id != %s
                AND u.is_active = TRUE
                AND f1.status = 'accepted'
                AND f2.status = 'accepted'
                AND u.user_id NOT IN (
                    SELECT friend_id FROM friendships WHERE user_id = %s AND status IN ('accepted', 'pending')
                    UNION
                    SELECT user_id FROM friendships WHERE friend_id = %s AND status IN ('accepted', 'pending')
                )
            GROUP BY u.user_id, u.username, u.display_name, us.total_wins, us.total_games, us.win_rate
            ORDER BY mutual_friends DESC, us.total_wins DESC
            LIMIT %s
        """
        cursor.execute(query, (user_id, user_id, user_id, user_id, limit))
        recommendations = cursor.fetchall()
        cursor.close()
        return recommendations
        
    except Error as e:
        print(f"Error fetching recommendations: {e}")
        return []
    finally:
        conn.close()


# multiplayer room functions


def generate_room_code() -> str:
    """
    make a random 6 character room code
    Returns: 6-character room code (A-Z, 0-9)
    """
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choice(chars) for _ in range(6))


def create_multiplayer_game(user_id: int, board_size: int, difficulty: int, 
                           puzzle_data: str, solution_data: str) -> Tuple[bool, str, Optional[Dict]]:
    """
    make a new multiplayer game room
    
    Args:
        user_id: player creating the room
        board_size: puzzle size (4, 9, or 16)
        difficulty: difficulty level (1, 2, or 3)
        puzzle_data: the puzzle as JSON
        solution_data: the answer as JSON
    
    Returns: (success, message, game_data)
    game_data contains: game_id, room_code, status, created_at
    """
    conn = get_connection()
    if not conn:
        return False, "Database connection failed", None
    
    try:
        cursor = conn.cursor()
        
        # make unique room code
        max_attempts = 10
        room_code = None
        for _ in range(max_attempts):
            candidate = generate_room_code()
            cursor.execute("SELECT game_id FROM multiplayer_games WHERE room_code = %s", (candidate,))
            if not cursor.fetchone():
                room_code = candidate
                break
        
        if not room_code:
            return False, "Failed to generate unique room code", None
        
        # save game to database
        query = """
            INSERT INTO multiplayer_games 
            (room_code, puzzle_data, solution_data, board_size, difficulty, status)
            VALUES (%s, %s, %s, %s, %s, 'waiting')
        """
        cursor.execute(query, (room_code, puzzle_data, solution_data, board_size, difficulty))
        conn.commit()
        
        game_id = cursor.lastrowid
        
        # add creator as first player
        player_query = """
            INSERT INTO multiplayer_players 
            (game_id, user_id, board_state)
            VALUES (%s, %s, %s)
        """
        cursor.execute(player_query, (game_id, user_id, puzzle_data))
        conn.commit()
        
        cursor.close()
        
        game_data = {
            'game_id': game_id,
            'room_code': room_code,
            'status': 'waiting',
            'created_at': datetime.now().isoformat()
        }
        
        return True, "Room created successfully", game_data
        
    except Error as e:
        return False, f"Database error: {str(e)}", None
    finally:
        conn.close()


def join_multiplayer_game(user_id: int, room_code: str) -> Tuple[bool, str, Optional[Dict]]:
    """
    join an existing multiplayer room
    
    Args:
        user_id: player joining
        room_code: 6 character room code
    
    Returns: (success, message, game_data)
    game_data contains: game_id, room_code, status, opponent_info, puzzle_data, solution_data
    """
    conn = get_connection()
    if not conn:
        return False, "Database connection failed", None
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        # check if room exists and is waiting
        query = """
            SELECT game_id, puzzle_data, solution_data, board_size, difficulty, status
            FROM multiplayer_games
            WHERE room_code = %s
        """
        cursor.execute(query, (room_code,))
        game = cursor.fetchone()
        
        if not game:
            return False, "Room not found", None
        
        if game['status'] != 'waiting':
            return False, "Room is not available for joining", None
        
        game_id = game['game_id']
        
        # make sure player not already in game
        cursor.execute(
            "SELECT player_id FROM multiplayer_players WHERE game_id = %s AND user_id = %s",
            (game_id, user_id)
        )
        if cursor.fetchone():
            return False, "You are already in this room", None
        
        # make sure room has space
        cursor.execute(
            "SELECT COUNT(*) as count FROM multiplayer_players WHERE game_id = %s",
            (game_id,)
        )
        player_count = cursor.fetchone()['count']
        
        if player_count >= 2:
            return False, "Room is full", None
        
        # add second player to game
        player_query = """
            INSERT INTO multiplayer_players 
            (game_id, user_id, board_state)
            VALUES (%s, %s, %s)
        """
        cursor.execute(player_query, (game_id, user_id, game['puzzle_data']))
        
        # start the game
        cursor.execute(
            "UPDATE multiplayer_games SET status = 'in_progress', started_at = NOW() WHERE game_id = %s",
            (game_id,)
        )
        conn.commit()
        
        # load opponent data
        cursor.execute("""
            SELECT u.user_id, u.username, u.display_name
            FROM multiplayer_players mp
            JOIN users u ON mp.user_id = u.user_id
            WHERE mp.game_id = %s AND mp.user_id != %s
        """, (game_id, user_id))
        opponent = cursor.fetchone()
        
        cursor.close()
        
        game_data = {
            'game_id': game_id,
            'room_code': room_code,
            'status': 'in_progress',
            'opponent': opponent,
            'puzzle_data': game['puzzle_data'],
            'solution_data': game['solution_data'],
            'board_size': game['board_size'],
            'difficulty': game['difficulty']
        }
        
        return True, "Joined room successfully", game_data
        
    except Error as e:
        return False, f"Database error: {str(e)}", None
    finally:
        conn.close()


def get_room_details(room_code: str) -> Tuple[bool, str, Optional[Dict]]:
    """
    get info about a multiplayer room
    
    Args:
        room_code: 6 character room code
    
    Returns: (success, message, room_data)
    room_data contains: game_id, room_code, status, players, started_at, time_elapsed
    """
    conn = get_connection()
    if not conn:
        return False, "Database connection failed", None
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        # get game info
        query = """
            SELECT game_id, room_code, status, started_at, created_at
            FROM multiplayer_games
            WHERE room_code = %s
        """
        cursor.execute(query, (room_code,))
        game = cursor.fetchone()
        
        if not game:
            return False, "Room not found", None
        
        # get players in room
        players_query = """
            SELECT u.user_id, u.username, u.display_name, mp.score, mp.completed
            FROM multiplayer_players mp
            JOIN users u ON mp.user_id = u.user_id
            WHERE mp.game_id = %s
        """
        cursor.execute(players_query, (game['game_id'],))
        players = cursor.fetchall()
        
        cursor.close()
        
        # how long game took
        time_elapsed = 0
        if game['started_at']:
            time_elapsed = int((datetime.now() - game['started_at']).total_seconds())
        
        room_data = {
            'game_id': game['game_id'],
            'room_code': game['room_code'],
            'status': game['status'],
            'players': players,
            'started_at': game['started_at'].isoformat() if game['started_at'] else None,
            'time_elapsed': time_elapsed
        }
        
        return True, "Room details retrieved", room_data
        
    except Error as e:
        return False, f"Database error: {str(e)}", None
    finally:
        conn.close()


def get_active_rooms(limit: int = 50) -> Tuple[bool, str, Optional[List[Dict]]]:
    """
    get list of open multiplayer rooms
    
    Args:
        limit: max number of rooms to return
    
    Returns: (success, message, rooms_list)

    """
    conn = get_connection()
    if not conn:
        return False, "Database connection failed", None
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        query = """
            SELECT 
                mg.game_id,
                mg.room_code,
                mg.status,
                mg.board_size,
                mg.difficulty,
                mg.created_at,
                COUNT(mp.player_id) as player_count,
                GROUP_CONCAT(u.username SEPARATOR ', ') as players
            FROM multiplayer_games mg
            LEFT JOIN multiplayer_players mp ON mg.game_id = mp.game_id
            LEFT JOIN users u ON mp.user_id = u.user_id
            WHERE mg.status IN ('waiting', 'in_progress')
            GROUP BY mg.game_id
            ORDER BY mg.created_at DESC
            LIMIT %s
        """
        cursor.execute(query, (limit,))
        rooms = cursor.fetchall()
        
        cursor.close()
        return True, "Active rooms retrieved", rooms
        
    except Error as e:
        return False, f"Database error: {str(e)}", None
    finally:
        conn.close()


def expire_old_rooms(timeout_minutes: int = 5) -> Tuple[bool, str, int]:
    """
    delete old rooms that nobody joined
    
    Args:
        timeout_minutes: how long to wait before deleting (default 5)
    
    Returns: (success, message, rooms_deleted)
    """
    conn = get_connection()
    if not conn:
        return False, "Database connection failed", 0
    
    try:
        cursor = conn.cursor()
        
        # find and delete old waiting rooms
        query = """
            DELETE FROM multiplayer_games
            WHERE status = 'waiting'
            AND created_at < DATE_SUB(NOW(), INTERVAL %s MINUTE)
        """
        cursor.execute(query, (timeout_minutes,))
        conn.commit()
        
        deleted_count = cursor.rowcount
        cursor.close()
        
        return True, f"Expired {deleted_count} old rooms", deleted_count
        
    except Error as e:
        return False, f"Database error: {str(e)}", 0
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════
# MULTIPLAYER GAME STATE MANAGEMENT
# ═══════════════════════════════════════════════════════════

def validate_move(game_id: int, user_id: int, row: int, col: int, value: int,
                  board_state: str) -> Tuple[bool, str, Optional[Dict]]:
    """
    Validate a move in multiplayer game 
    
    Args:
        game_id: ID of the multiplayer game
        user_id: ID of the player making the move
        row: Row index (0-based)
        col: Column index (0-based)
        value: Value placed (1-9 for 9x9, etc.)
        board_state: JSON string of current board state
    
    Returns: (success, message, validation_data)
    validation_data contains: is_valid, is_error, error_count
    """
    conn = get_connection()
    if not conn:
        return False, "Database connection failed", None
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        # load game data
        cursor.execute("""
            SELECT puzzle_data, solution_data, board_size
            FROM multiplayer_games
            WHERE game_id = %s
        """, (game_id,))
        
        game = cursor.fetchone()
        if not game:
            cursor.close()
            return False, "Game not found", None
        
        # Parse puzzle and solution
        try:
            puzzle = json.loads(game['puzzle_data']) if isinstance(game['puzzle_data'], str) else game['puzzle_data']
            solution = json.loads(game['solution_data']) if isinstance(game['solution_data'], str) else game['solution_data']
            board = json.loads(board_state) if isinstance(board_state, str) else board_state
        except (json.JSONDecodeError, TypeError):
            cursor.close()
            return False, "Invalid board state format", None
        
        board_size = game['board_size']
        index = row * board_size + col
        
        # Validate move is legal (row/col in range)
        if not (0 <= row < board_size and 0 <= col < board_size):
            cursor.close()
            return False, "Invalid row or column", None
        
        if not (1 <= value <= board_size):
            cursor.close()
            return False, f"Value must be between 1 and {board_size}", None
        
        # Validate move doesn't conflict with puzzle
        if puzzle[index] != 0:
            cursor.close()
            return False, "Cannot modify given cells", None
        
        # Check if move is correct (validate against solution)
        is_error = (solution[index] != value)
        
        # Get current error count
        cursor.execute("""
            SELECT errors_made FROM multiplayer_players
            WHERE game_id = %s AND user_id = %s
        """, (game_id, user_id))
        
        player = cursor.fetchone()
        error_count = (player['errors_made'] if player else 0) + (1 if is_error else 0)
        
        cursor.close()
        
        validation_data = {
            'is_valid': True,
            'is_error': is_error,
            'error_count': error_count
        }
        
        return True, "Move validated", validation_data
        
    except Error as e:
        return False, f"Database error: {str(e)}", None
    finally:
        conn.close()


def check_player_disconnection(game_id: int, timeout_seconds: int = 30) -> Tuple[bool, List[Dict]]:
    """
    check if players are still connected
    
    Args:
        game_id: multiplayer game ID
        timeout_seconds: how long before considering disconnected (default 30)
    
    Returns: (success, disconnected_players)
    disconnected_players contains: user_id, username, last_activity_ago
    """
    conn = get_connection()
    if not conn:
        return False, []
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        # find players who havent moved recently
        query = """
            SELECT mp.user_id, u.username, 
                   TIMESTAMPDIFF(SECOND, COALESCE(mp.last_move_at, mp.joined_at), NOW()) as inactivity_seconds
            FROM multiplayer_players mp
            JOIN users u ON mp.user_id = u.user_id
            WHERE mp.game_id = %s
            AND TIMESTAMPDIFF(SECOND, COALESCE(mp.last_move_at, mp.joined_at), NOW()) > %s
        """
        cursor.execute(query, (game_id, timeout_seconds))
        disconnected = cursor.fetchall()
        
        cursor.close()
        return True, disconnected
        
    except Error as e:
        print(f"Error checking disconnection: {e}")
        return False, []
    finally:
        conn.close()


def handle_player_disconnection(game_id: int, user_id: int) -> Tuple[bool, str]:
    """
    handle when player disconnects
    
    Args:
        game_id: multiplayer game ID
        user_id: disconnected player ID
    
    Returns: (success, message)
    """
    conn = get_connection()
    if not conn:
        return False, "Database connection failed"
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        # mark player as disconnected
        cursor.execute("""
            UPDATE multiplayer_players
            SET disconnected_at = NOW()
            WHERE game_id = %s AND user_id = %s
        """, (game_id, user_id))
        
        # pause the game
        cursor.execute("""
            UPDATE multiplayer_games
            SET status = 'paused'
            WHERE game_id = %s AND status = 'in_progress'
        """, (game_id,))
        
        conn.commit()
        cursor.close()
        
        return True, "Player disconnection handled"
        
    except Error as e:
        return False, f"Database error: {str(e)}"
    finally:
        conn.close()


def allow_reconnection(game_id: int, user_id: int, timeout_minutes: int = 5) -> Tuple[bool, str]:
    """
    let player reconnect if not too late
    
    Args:
        game_id: multiplayer game ID
        user_id: player trying to reconnect
        timeout_minutes: how long they have to reconnect (default 5)
    
    Returns: (success, message)
    """
    conn = get_connection()
    if not conn:
        return False, "Database connection failed"
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        # check if player was disconnected
        cursor.execute("""
            SELECT disconnected_at FROM multiplayer_players
            WHERE game_id = %s AND user_id = %s
        """, (game_id, user_id))
        
        player = cursor.fetchone()
        if not player or not player['disconnected_at']:
            cursor.close()
            return False, "Player was not disconnected"
        
        # check if too late to reconnect
        time_since_disconnect = (datetime.now() - player['disconnected_at']).total_seconds()
        if time_since_disconnect > timeout_minutes * 60:
            # too late: player loses automatically
            cursor.execute("""
                UPDATE multiplayer_players
                SET completed = TRUE, score = 0, completed_at = NOW()
                WHERE game_id = %s AND user_id = %s
            """, (game_id, user_id))
            conn.commit()
            cursor.close()
            return False, "Reconnection timeout exceeded. Auto-loss applied."
        
        # let player reconnect
        cursor.execute("""
            UPDATE multiplayer_players
            SET disconnected_at = NULL
            WHERE game_id = %s AND user_id = %s
        """, (game_id, user_id))
        
        # resume game if both players back
        cursor.execute("""
            SELECT COUNT(*) as disconnected_count FROM multiplayer_players
            WHERE game_id = %s AND disconnected_at IS NOT NULL
        """, (game_id,))
        
        result = cursor.fetchone()
        if result['disconnected_count'] == 0:
            cursor.execute("""
                UPDATE multiplayer_games
                SET status = 'in_progress'
                WHERE game_id = %s AND status = 'paused'
            """, (game_id,))
        
        conn.commit()
        cursor.close()
        
        return True, "Reconnection successful"
        
    except Error as e:
        return False, f"Database error: {str(e)}"
    finally:
        conn.close()


def save_player_move(game_id: int, user_id: int, row: int, col: int, value: int,
                     board_state: str) -> Tuple[bool, str, Optional[Dict]]:
    """
    save a player move in multiplayer game
    
    Args:
        game_id: multiplayer game ID
        user_id: player making the move
        row: row number (starts at 0)
        col: column number (starts at 0)
        value: number placed (1-9 for 9x9, etc)
        board_state: current board as JSON
    
    Returns: (success, message, move_data)
    move_data contains: move_id, board_state, score, errors_made
    """
    conn = get_connection()
    if not conn:
        return False, "Database connection failed", None
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        # make sure player is in this game
        cursor.execute("""
            SELECT player_id, board_state, errors_made, score
            FROM multiplayer_players
            WHERE game_id = %s AND user_id = %s
        """, (game_id, user_id))
        
        player = cursor.fetchone()
        if not player:
            cursor.close()
            return False, "Player not in this game", None
        
        # check if move is valid
        success, message, validation = validate_move(game_id, user_id, row, col, value, board_state)
        if not success:
            cursor.close()
            return False, message, None
        
        # count errors
        new_errors = player['errors_made']
        if validation['is_error']:
            new_errors += 1
        
        # save board state and move time
        query = """
            UPDATE multiplayer_players
            SET board_state = %s, last_move_at = NOW(), errors_made = %s
            WHERE game_id = %s AND user_id = %s
        """
        cursor.execute(query, (board_state, new_errors, game_id, user_id))
        conn.commit()
        
        move_data = {
            'move_id': player['player_id'],
            'board_state': board_state,
            'score': player['score'],
            'errors_made': new_errors
        }
        
        cursor.close()
        return True, "Move saved successfully", move_data
        
    except Error as e:
        return False, f"Database error: {str(e)}", None
    finally:
        conn.close()


def get_game_state(game_id: int, user_id: int) -> Tuple[bool, str, Optional[Dict]]:
    """
    get current game state for a player
    
    Args:
        game_id: multiplayer game ID
        user_id: player ID
    
    Returns: (success, message, game_state)
    game_state contains: game_id, status, your_board, opponent_info, time_elapsed
    """
    conn = get_connection()
    if not conn:
        return False, "Database connection failed", None
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        # load game data
        cursor.execute("""
            SELECT game_id, status, started_at, finished_at, winner_id, 
                   board_size, difficulty, puzzle_data, solution_data
            FROM multiplayer_games
            WHERE game_id = %s
        """, (game_id,))
        
        game = cursor.fetchone()
        if not game:
            return False, "Game not found", None
        
        # load your game data
        cursor.execute("""
            SELECT player_id, board_state, score, errors_made, hints_used, 
                   completed, completed_at
            FROM multiplayer_players
            WHERE game_id = %s AND user_id = %s
        """, (game_id, user_id))
        
        your_player = cursor.fetchone()
        if not your_player:
            return False, "You are not in this game", None
        
        # load opponent data
        cursor.execute("""
            SELECT u.user_id, u.username, u.display_name, mp.score, 
                   mp.errors_made, mp.completed, mp.completed_at
            FROM multiplayer_players mp
            JOIN users u ON mp.user_id = u.user_id
            WHERE mp.game_id = %s AND mp.user_id != %s
        """, (game_id, user_id))
        
        opponent = cursor.fetchone()
        
        cursor.close()
        
        # how long game took
        time_elapsed = 0
        if game['started_at']:
            time_elapsed = int((datetime.now() - game['started_at']).total_seconds())
        
        game_state = {
            'game_id': game_id,
            'status': game['status'],
            'board_size': game['board_size'],
            'difficulty': game['difficulty'],
            'your_board': your_player['board_state'],
            'your_score': your_player['score'],
            'your_errors': your_player['errors_made'],
            'your_hints': your_player['hints_used'],
            'your_completed': your_player['completed'],
            'solution': game['solution_data'],
            'opponent': opponent,
            'time_elapsed': time_elapsed,
            'winner_id': game['winner_id']
        }
        
        return True, "Game state retrieved", game_state
        
    except Error as e:
        return False, f"Database error: {str(e)}", None
    finally:
        conn.close()


def complete_multiplayer_game(game_id: int, user_id: int, time_seconds: int,
                              hints_used: int, errors_made: int,
                              board_state: str) -> Tuple[bool, str, Optional[Dict]]:
    """
    mark player puzzle as completed in multiplayer
    
    Args:
        game_id: multiplayer game ID
        user_id: player who completed
        time_seconds: how long it took
        hints_used: number of hints used
        errors_made: number of errors made
        board_state: final board state
    
    Returns: (success, message, completion_data)
    completion_data contains: score, completed_at, opponent_status, game_finished
    """
    conn = get_connection()
    if not conn:
        return False, "Database connection failed", None
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        # load game data
        cursor.execute("""
            SELECT board_size, difficulty, status
            FROM multiplayer_games
            WHERE game_id = %s
        """, (game_id,))
        
        game = cursor.fetchone()
        if not game:
            return False, "Game not found", None
        
        # calculate points
        score = calculate_score(game['board_size'], game['difficulty'],
                               time_seconds, hints_used, errors_made, True)
        
        # save player completion
        query = """
            UPDATE multiplayer_players
            SET score = %s, time_seconds = %s, hints_used = %s, 
                errors_made = %s, completed = TRUE, completed_at = NOW(),
                board_state = %s
            WHERE game_id = %s AND user_id = %s
        """
        cursor.execute(query, (score, time_seconds, hints_used, errors_made,
                              board_state, game_id, user_id))
        conn.commit()
        
        # check if you finished first
        cursor.execute("""
            SELECT COUNT(*) as completed_count
            FROM multiplayer_players
            WHERE game_id = %s AND completed = TRUE
        """, (game_id,))
        
        completed_count = cursor.fetchone()['completed_count']
        
        # load opponent data
        cursor.execute("""
            SELECT u.user_id, u.username, mp.player_id, mp.score, mp.completed
            FROM multiplayer_players mp
            JOIN users u ON mp.user_id = u.user_id
            WHERE mp.game_id = %s AND mp.user_id != %s
        """, (game_id, user_id))
        
        opponent = cursor.fetchone()
        
        game_finished = False
        
        # first player to complete wins immediately
        if completed_count == 1:
            # you won by finishing first
            # other player loses (mark as completed with current score)
            if opponent and not opponent['completed']:
                cursor.execute("""
                    UPDATE multiplayer_players
                    SET completed = TRUE, completed_at = NOW()
                    WHERE game_id = %s AND user_id = %s
                """, (game_id, opponent['user_id']))
                conn.commit()
            
            # figure out winner (will be the player who finished)
            winner_id = determine_winner(game_id)
            
            # end the game
            cursor.execute("""
                UPDATE multiplayer_games
                SET status = 'completed', finished_at = NOW(), winner_id = %s
                WHERE game_id = %s
            """, (winner_id, game_id))
            conn.commit()
            
            game_finished = True
            
            # save to history table
            cursor.close()
            conn.close()
            
            # save results to history
            from database import save_multiplayer_result
            save_success, save_message, save_result = save_multiplayer_result(game_id)
            if not save_success:
                print(f"Warning: Failed to save multiplayer result: {save_message}")
            
            # get updated opponent data
            conn = get_connection()
            if not conn:
                return False, "Database connection failed", None
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT u.user_id, u.username, mp.score, mp.completed
                FROM multiplayer_players mp
                JOIN users u ON mp.user_id = u.user_id
                WHERE mp.game_id = %s AND mp.user_id != %s
            """, (game_id, user_id))
            opponent = cursor.fetchone()
        
        cursor.close()
        
        completion_data = {
            'score': score,
            'completed_at': datetime.now().isoformat(),
            'opponent_status': opponent,
            'game_finished': game_finished
        }
        
        return True, "Puzzle completed successfully", completion_data
        
    except Error as e:
        return False, f"Database error: {str(e)}", None
    finally:
        conn.close()


def determine_winner(game_id: int) -> Optional[int]:
    """
    figure out who won the multiplayer game
    
    Winner is decided by:
    1. higher score wins
    2. if scores equal, faster time wins
    3. if both equal, first to finish wins
    
    Args:
        game_id: multiplayer game ID
    
    Returns: user_id of winner, or None if game not complete
    """
    conn = get_connection()
    if not conn:
        return None
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        # get both players completion info
        cursor.execute("""
            SELECT user_id, score, time_seconds, completed_at
            FROM multiplayer_players
            WHERE game_id = %s
            ORDER BY completed_at ASC
        """, (game_id,))
        
        players = cursor.fetchall()
        cursor.close()
        
        if len(players) != 2:
            return None
        
        player1, player2 = players[0], players[1]
        
        # compare scores (higher wins)
        if player1['score'] > player2['score']:
            return player1['user_id']
        elif player2['score'] > player1['score']:
            return player2['user_id']
        
        # scores equal, compare time (faster wins)
        if player1['time_seconds'] < player2['time_seconds']:
            return player1['user_id']
        elif player2['time_seconds'] < player1['time_seconds']:
            return player2['user_id']
        
        # everything equal, first to finish wins
        return player1['user_id']
        
    except Error as e:
        print(f"Error determining winner: {e}")
        return None
    finally:
        conn.close()


def save_multiplayer_result(game_id: int) -> Tuple[bool, str, Optional[Dict]]:
    """
    save final multiplayer game result to history
    
    Args:
        game_id: completed multiplayer game ID
    
    Returns: (success, message, result_data)
    result_data contains: history_id, winner_id, player1_score, player2_score
    """
    conn = get_connection()
    if not conn:
        return False, "Database connection failed", None
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        # load game data
        cursor.execute("""
            SELECT board_size, difficulty, winner_id, status
            FROM multiplayer_games
            WHERE game_id = %s
        """, (game_id,))
        
        game = cursor.fetchone()
        if not game:
            return False, "Game not found", None
        
        if game['status'] != 'completed':
            return False, "Game is not completed", None
        
        # get both players info
        cursor.execute("""
            SELECT user_id, score, time_seconds
            FROM multiplayer_players
            WHERE game_id = %s
            ORDER BY user_id ASC
        """, (game_id,))
        
        players = cursor.fetchall()
        
        if len(players) != 2:
            return False, "Game does not have exactly 2 players", None
        
        player1, player2 = players[0], players[1]
        
        # save to multiplayer history table
        query = """
            INSERT INTO multiplayer_history
            (game_id, player1_id, player2_id, winner_id, player1_score, 
             player2_score, player1_time, player2_time, board_size, difficulty)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(query, (
            game_id,
            player1['user_id'],
            player2['user_id'],
            game['winner_id'],
            player1['score'],
            player2['score'],
            player1['time_seconds'],
            player2['time_seconds'],
            game['board_size'],
            game['difficulty']
        ))
        conn.commit()
        
        history_id = cursor.lastrowid
        
        # update stats for both players
        for player in players:
            is_winner = player['user_id'] == game['winner_id']
            cursor.callproc('update_multiplayer_stats',
                           (player['user_id'], is_winner, player['score']))
        
        conn.commit()
        cursor.close()
        
        result_data = {
            'history_id': history_id,
            'winner_id': game['winner_id'],
            'player1_score': player1['score'],
            'player2_score': player2['score']
        }
        
        return True, "Result saved successfully", result_data
        
    except Error as e:
        return False, f"Database error: {str(e)}", None
    finally:
        conn.close()


# helper functions

def test_connection() -> bool:
    """check if database connection works"""
    conn = get_connection()
    if conn:
        conn.close()
        return True
    return False


def close_pool():
    """close all database connections"""
    global connection_pool
    if connection_pool:
        # set pool to None to close
        connection_pool = None
        print("Database connection pool closed")
