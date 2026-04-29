import json
import subprocess
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn
import logging
from datetime import datetime
import asyncio

# Configure logging 
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('sudoku_duel.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# get database helper functions
from database import (
    init_db_pool, test_connection, close_pool,
    create_user, authenticate_user, get_user_profile,
    save_game_result, get_user_game_history,
    get_global_leaderboard, get_weekly_leaderboard, 
    get_friends_leaderboard, get_user_rank,
    send_friend_request, accept_friend_request, get_friends_list,
    get_pending_friend_requests, get_recommendations,
    create_multiplayer_game, join_multiplayer_game, get_room_details,
    save_player_move, get_game_state, complete_multiplayer_game,
    save_multiplayer_result, get_connection,
    validate_move, check_player_disconnection, handle_player_disconnection,
    allow_reconnection
)


app = FastAPI(title="Sudoku Duel")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# connect to database when server starts
@app.on_event("startup")
async def startup_event():
    print("=" * 52)
    print("  Initializing Sudoku Duel Server")
    print("=" * 52)
    if init_db_pool():
        if test_connection():
            print("✓ Database connected successfully")
        else:
            print("✗ Database connection test failed")
    else:
        print("✗ Failed to initialize database pool")
        print("  Server will continue but database features won't work")

@app.on_event("shutdown")
async def shutdown_event():
    close_pool()
    print("Server shutdown complete")

class RegisterRequest(BaseModel):
    username: str
    displayname: Optional[str] = None
    password: str
    email: Optional[str] = None


class LoginRequest(BaseModel):
    username: str
    password: str


class GameResultRequest(BaseModel):
    user_id: int
    board_size: int
    difficulty: int
    time_seconds: int
    hints_used: int
    errors_made: int
    completed: bool


@app.post("/api/register")
def register(req: RegisterRequest):
    """Create a new account."""
    username = req.username.strip().lower()

    if len(username) < 3:
        raise HTTPException(status_code=400, detail="Username must be at least 3 characters.")
    if len(req.password) < 4:
        raise HTTPException(status_code=400, detail="Password must be at least 4 characters.")

    success, message, user_id = create_user(
        username=username,
        password=req.password,
        display_name=req.displayname,
        email=req.email
    )
    
    if not success:
        status_code = 409 if "already exists" in message else 500
        raise HTTPException(status_code=status_code, detail=message)

    return {"message": message, "user_id": user_id}


@app.post("/api/login")
def login(req: LoginRequest):
    """Authenticate and return player profile."""
    username = req.username.strip().lower()

    success, user_data = authenticate_user(username, req.password)
    
    if not success or not user_data:
        raise HTTPException(status_code=401, detail="Invalid username or password.")

    player = {
        "id": user_data["user_id"],
        "username": user_data["username"],
        "name": user_data["display_name"],
        "wins": user_data["total_wins"] or 0,
        "losses": user_data["total_losses"] or 0,
        "games": user_data["total_games"] or 0,
        "win_rate": float(user_data["win_rate"] or 0),
        "total_score": user_data["total_score"] or 0,
        "best_time": user_data["best_time_9x9"]
    }
    return {"player": player}


@app.get("/api/player/{username}")
def get_player(username: str):
    """Fetch a player's public profile."""
    success, user_data = authenticate_user(username.lower(), "")
    
    # Get user by username without password check
    from database import get_connection
    conn = get_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    try:
        cursor = conn.cursor(dictionary=True)
        query = """
            SELECT u.user_id, u.username, u.display_name,
                   us.total_games, us.total_wins, us.total_losses, us.win_rate
            FROM users u
            LEFT JOIN user_stats us ON u.user_id = us.user_id
            WHERE u.username = %s AND u.is_active = TRUE
        """
        cursor.execute(query, (username.lower(),))
        user = cursor.fetchone()
        cursor.close()
        
        if not user:
            raise HTTPException(status_code=404, detail="Player not found.")
        
        return {
            "username": user["username"],
            "name": user["display_name"],
            "wins": user["total_wins"] or 0,
            "losses": user["total_losses"] or 0,
            "games": user["total_games"] or 0,
            "win_rate": float(user["win_rate"] or 0)
        }
    finally:
        conn.close()

@app.post("/api/game/save")
def save_game(req: GameResultRequest):
    """Save game result and update statistics."""
    success, game_id = save_game_result(
        user_id=req.user_id,
        board_size=req.board_size,
        difficulty=req.difficulty,
        time_seconds=req.time_seconds,
        hints_used=req.hints_used,
        errors_made=req.errors_made,
        completed=req.completed
    )
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to save game result")
    
    return {"message": "Game saved successfully", "game_id": game_id}


@app.get("/api/leaderboard/global")
def leaderboard_global(limit: int = 100):
    """Get global leaderboard."""
    leaderboard = get_global_leaderboard(limit)
    return {"leaderboard": leaderboard}


@app.get("/api/leaderboard/weekly")
def leaderboard_weekly(limit: int = 100):
    """Get weekly leaderboard."""
    leaderboard = get_weekly_leaderboard(limit)
    return {"leaderboard": leaderboard}


@app.get("/api/leaderboard/friends/{user_id}")
def leaderboard_friends(user_id: int):
    """Get friends leaderboard."""
    leaderboard = get_friends_leaderboard(user_id)
    return {"leaderboard": leaderboard}


@app.get("/api/user/{user_id}/rank")
def user_rank(user_id: int):
    """Get user's rank in global leaderboard."""
    rank = get_user_rank(user_id)
    if not rank:
        raise HTTPException(status_code=404, detail="User rank not found")
    return rank


@app.get("/api/user/{user_id}/history")
def user_history(user_id: int, limit: int = 10):
    """Get user's game history."""
    history = get_user_game_history(user_id, limit)
    return {"history": history}


@app.get("/api/user/{user_id}/friends")
def user_friends(user_id: int):
    """Get user's friends list."""
    friends = get_friends_list(user_id)
    return {"friends": friends}


@app.get("/api/user/{user_id}/pending-requests")
def user_pending_requests(user_id: int):
    """Get pending friend requests for user."""
    requests = get_pending_friend_requests(user_id)
    return {"pending_requests": requests}


@app.get("/api/user/{user_id}/recommendations")
def user_recommendations(user_id: int):
    """Get friend recommendations based on mutual friends."""
    recommendations = get_recommendations(user_id)
    return {"recommendations": recommendations}


class AddFriendRequest(BaseModel):
    user_id: int
    friend_username: str


class AcceptFriendRequest(BaseModel):
    user_id: int
    friend_id: int


@app.post("/api/friends/add")
def add_friend(req: AddFriendRequest):
    """Send friend request."""
    success, message = send_friend_request(req.user_id, req.friend_username)
    if not success:
        raise HTTPException(status_code=400, detail=message)
    return {"message": message}


@app.post("/api/friends/accept")
def accept_friend(req: AcceptFriendRequest):
    """Accept friend request."""
    success, message = accept_friend_request(req.user_id, req.friend_id)
    if not success:
        raise HTTPException(status_code=400, detail=message)
    return {"message": message}


# Multiplayer game 

# data models for multiplayer requests
class CreateRoomRequest(BaseModel):
    user_id: int
    board_size: int
    difficulty: int


class JoinRoomRequest(BaseModel):
    user_id: int
    room_code: str


class MakeMoveRequest(BaseModel):
    user_id: int
    row: int
    col: int
    value: int
    board_state: list


class CompleteGameRequest(BaseModel):
    user_id: int
    time_seconds: int
    hints_used: int
    errors_made: int
    board_state: list


class GiveUpRequest(BaseModel):
    user_id: int


@app.post("/api/multiplayer/room/create")
def create_room(req: CreateRoomRequest):
    """Create a new multiplayer room ."""
    try:
        logger.info(f"Room creation requested: user_id={req.user_id}, board_size={req.board_size}, difficulty={req.difficulty}")
        
        if req.board_size not in [4, 9, 16]:
            logger.warning(f"Invalid board size: {req.board_size}")
            raise HTTPException(status_code=400, detail="Board size must be 4, 9, or 16.")
        if req.difficulty not in [1, 2, 3]:
            logger.warning(f"Invalid difficulty: {req.difficulty}")
            raise HTTPException(status_code=400, detail="Difficulty must be 1, 2, or 3.")
        
        # call C++ to make the puzzle
        puzzle_result = call_cpp("generate", size=req.board_size, difficulty=req.difficulty)
        
        if "puzzle" not in puzzle_result:
            logger.error(f"C++ generator did not return puzzle")
            raise HTTPException(status_code=500, detail="Puzzle generation failed")
        
        puzzle_data = json.dumps(puzzle_result["puzzle"])
        
        # make solution if we dont have it
        if "solution" in puzzle_result:
            solution_data = json.dumps(puzzle_result["solution"])
        else:
            # solve puzzle to get answer
            solve_result = call_cpp("solve", size=req.board_size, board=puzzle_result["puzzle"])
            if "solution" in solve_result:
                solution_data = json.dumps(solve_result["solution"])
            else:
                logger.error(f"Failed to generate solution for puzzle: {solve_result}")
                raise HTTPException(status_code=500, detail="Solution generation failed")
        
        success, message, result = create_multiplayer_game(
            req.user_id, req.board_size, req.difficulty, puzzle_data, solution_data
        )
        
        if not success:
            logger.error(f"Room creation failed: user_id={req.user_id}, message={message}")
            raise HTTPException(status_code=500, detail=message)
        
        logger.info(f"Room created: room_code={result['room_code']}, game_id={result['game_id']}, user_id={req.user_id}")
        
        return {
            "room_code": result["room_code"],
            "game_id": result["game_id"],
            "status": "waiting",
            "created_at": result["created_at"]
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in create_room: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.post("/api/multiplayer/room/join")
def join_room(req: JoinRoomRequest):
    """Join an existing multiplayer room ."""
    logger.info(f"Room join requested: user_id={req.user_id}, room_code={req.room_code}")
    
    if not req.room_code or len(req.room_code) != 6:
        logger.warning(f"Invalid room code format: {req.room_code}")
        raise HTTPException(status_code=400, detail="Invalid room code format.")
    
    success, message, result = join_multiplayer_game(req.user_id, req.room_code)
    
    if not success:
        logger.warning(f"Room join failed: user_id={req.user_id}, room_code={req.room_code}, message={message}")
        if "not found" in message.lower():
            raise HTTPException(status_code=404, detail=message)
        elif "already has" in message.lower() or "full" in message.lower():
            raise HTTPException(status_code=400, detail=message)
        else:
            raise HTTPException(status_code=500, detail=message)
    
    logger.info(f"Room joined: user_id={req.user_id}, game_id={result['game_id']}, room_code={req.room_code}")
    
    # convert puzzle data from JSON
    try:
        puzzle = json.loads(result["puzzle_data"]) if isinstance(result["puzzle_data"], str) else result["puzzle_data"]
        solution = json.loads(result["solution_data"]) if isinstance(result["solution_data"], str) else result["solution_data"]
    except (json.JSONDecodeError, TypeError):
        puzzle = result["puzzle_data"]
        solution = result["solution_data"]
    
    return {
        "game_id": result["game_id"],
        "room_code": result["room_code"],
        "opponent": result["opponent"],
        "puzzle": puzzle,
        "solution": solution,
        "board_size": result["board_size"],
        "difficulty": result["difficulty"],
        "status": "starting"
    }


@app.get("/api/multiplayer/room/{room_code}")
def get_room(room_code: str):
    """Get room details."""
    logger.info(f"Room details requested: room_code={room_code}")
    
    if not room_code or len(room_code) != 6:
        logger.warning(f"Invalid room code format: {room_code}")
        raise HTTPException(status_code=400, detail="Invalid room code format.")
    
    success, message, result = get_room_details(room_code)
    
    if not success:
        logger.error(f"Room details fetch failed: room_code={room_code}, message={message}")
        if "not found" in message.lower():
            raise HTTPException(status_code=404, detail=message)
        else:
            raise HTTPException(status_code=500, detail=message)
    
    return {
        "game_id": result["game_id"],
        "room_code": result["room_code"],
        "status": result["status"],
        "players": result["players"],
        "started_at": result["started_at"],
        "time_elapsed": result["time_elapsed"]
    }


@app.get("/api/multiplayer/room/{room_code}/status")
def get_room_status(room_code: str):
    """Get room status."""
    if not room_code or len(room_code) != 6:
        raise HTTPException(status_code=400, detail="Invalid room code format.")
    
    success, message, result = get_room_details(room_code)
    
    if not success:
        if "not found" in message.lower():
            raise HTTPException(status_code=404, detail=message)
        else:
            raise HTTPException(status_code=500, detail=message)
    
    return {
        "game_id": result["game_id"],
        "status": result["status"],
        "players_count": len(result["players"]),
        "players": result["players"]
    }


@app.post("/api/multiplayer/room/{room_code}/cancel")
def cancel_room(room_code: str):
    """Cancel a multiplayer room."""
    if not room_code or len(room_code) != 6:
        raise HTTPException(status_code=400, detail="Invalid room code format.")
    
    conn = get_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        # Get game_id from room_code
        query = "SELECT game_id, status FROM multiplayer_games WHERE room_code = %s"
        cursor.execute(query, (room_code,))
        game = cursor.fetchone()
        
        if not game:
            cursor.close()
            raise HTTPException(status_code=404, detail="Room not found.")
        
        if game["status"] == "completed":
            cursor.close()
            raise HTTPException(status_code=400, detail="Cannot cancel a completed game.")
        
        # Update game status to cancelled
        update_query = "UPDATE multiplayer_games SET status = 'cancelled' WHERE game_id = %s"
        cursor.execute(update_query, (game["game_id"],))
        conn.commit()
        cursor.close()
        
        return {"message": "Room cancelled successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error cancelling room: {str(e)}")
    finally:
        conn.close()

@app.post("/api/multiplayer/game/{game_id}/move")
def make_move(game_id: int, req: MakeMoveRequest):
    """Submit a move in multiplayer game ."""
    logger.info(f"Move submitted: game_id={game_id}, user_id={req.user_id}, row={req.row}, col={req.col}, value={req.value}")
    
    if not (0 <= req.row < 9 and 0 <= req.col < 9):
        logger.warning(f"Invalid move coordinates: game_id={game_id}, row={req.row}, col={req.col}")
        raise HTTPException(status_code=400, detail="Invalid row or column.")
    if not (1 <= req.value <= 9):
        logger.warning(f"Invalid move value: game_id={game_id}, value={req.value}")
        raise HTTPException(status_code=400, detail="Value must be between 1 and 9.")
    
    # save board as JSON text
    board_state_str = json.dumps(req.board_state)
    
    success, message, result = save_player_move(
        game_id, req.user_id, req.row, req.col, req.value, board_state_str
    )
    
    if not success:
        logger.error(f"Move save failed: game_id={game_id}, user_id={req.user_id}, message={message}")
        if "not in this game" in message.lower():
            raise HTTPException(status_code=404, detail=message)
        else:
            raise HTTPException(status_code=400, detail=message)
    
    logger.info(f"Move saved successfully: game_id={game_id}, user_id={req.user_id}, errors={result['errors_made']}")
    
    # check what opponent is doing
    conn = get_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT score, completed FROM multiplayer_players
            WHERE game_id = %s AND user_id != %s
        """, (game_id, req.user_id))
        opponent = cursor.fetchone()
        cursor.close()
        
        opponent_status = {
            "score": opponent["score"] if opponent else 0,
            "completed": opponent["completed"] if opponent else False
        }
    except Exception as e:
        logger.error(f"Error fetching opponent status: {str(e)}")
        opponent_status = {"score": 0, "completed": False}
    finally:
        conn.close()
    
    return {
        "success": True,
        "board_state": req.board_state,
        "score": result["score"],
        "errors": result["errors_made"],
        "opponent_status": opponent_status
    }


@app.post("/api/multiplayer/game/{game_id}/complete")
def complete_game(game_id: int, req: CompleteGameRequest):
    """Mark puzzle as completed."""
    if req.time_seconds < 0:
        raise HTTPException(status_code=400, detail="Time cannot be negative.")
    if req.hints_used < 0 or req.errors_made < 0:
        raise HTTPException(status_code=400, detail="Hints and errors cannot be negative.")
    
    # save board as JSON text
    board_state_str = json.dumps(req.board_state)
    
    success, message, result = complete_multiplayer_game(
        game_id, req.user_id, req.time_seconds, req.hints_used, req.errors_made, board_state_str
    )
    
    if not success:
        if "not found" in message.lower():
            raise HTTPException(status_code=404, detail=message)
        else:
            raise HTTPException(status_code=400, detail=message)
    
    opponent_status = "still_playing"
    if result["opponent_status"]:
        opponent_status = "completed" if result["opponent_status"]["completed"] else "still_playing"
    
    return {
        "success": True,
        "score": result["score"],
        "completed_at": result["completed_at"],
        "opponent_status": opponent_status,
        "game_finished": result["game_finished"]
    }


@app.get("/api/multiplayer/game/{game_id}/state")
def get_state(game_id: int, user_id: int):
    """Get current game state ."""
    logger.info(f"State requested: game_id={game_id}, user_id={user_id}")
    
    success, message, result = get_game_state(game_id, user_id)
    
    if not success:
        logger.error(f"State fetch failed: game_id={game_id}, message={message}")
        if "not found" in message.lower():
            raise HTTPException(status_code=404, detail=message)
        else:
            raise HTTPException(status_code=500, detail=message)
    try:
        your_board = json.loads(result["your_board"]) if isinstance(result["your_board"], str) else result["your_board"]
        solution = json.loads(result["solution"]) if isinstance(result["solution"], str) else result["solution"]
    except (json.JSONDecodeError, TypeError):
        your_board = result["your_board"]
        solution = result["solution"]
    
    opponent_score = result["opponent"]["score"] if result["opponent"] else 0
    opponent_completed = result["opponent"]["completed"] if result["opponent"] else False
    
    return {
        "game_id": result["game_id"],
        "status": result["status"],
        "board_size": result["board_size"],
        "difficulty": result["difficulty"],
        "your_board": your_board,
        "solution": solution,
        "your_score": result["your_score"],
        "your_completed": result["your_completed"],
        "opponent_score": opponent_score,
        "opponent_completed": opponent_completed,
        "time_elapsed": result["time_elapsed"]
    }


@app.post("/api/multiplayer/game/{game_id}/validate-move")
def validate_move_endpoint(game_id: int, req: MakeMoveRequest):
    """Validate a move without saving it ."""
    logger.info(f"Move validation requested: game_id={game_id}, user_id={req.user_id}, row={req.row}, col={req.col}")
    
    board_state_str = json.dumps(req.board_state)
    
    success, message, validation = validate_move(
        game_id, req.user_id, req.row, req.col, req.value, board_state_str
    )
    
    if not success:
        logger.warning(f"Move validation failed: game_id={game_id}, message={message}")
        raise HTTPException(status_code=400, detail=message)
    
    logger.info(f"Move validated: game_id={game_id}, is_error={validation['is_error']}")
    
    return {
        "is_valid": validation["is_valid"],
        "is_error": validation["is_error"],
        "error_count": validation["error_count"]
    }


@app.post("/api/multiplayer/game/{game_id}/check-disconnection")
def check_disconnection_endpoint(game_id: int):
    """Check for disconnected players ."""
    logger.info(f"Disconnection check: game_id={game_id}")
    
    success, disconnected = check_player_disconnection(game_id, timeout_seconds=30)
    
    if not success:
        logger.error(f"Disconnection check failed: game_id={game_id}")
        raise HTTPException(status_code=500, detail="Failed to check disconnection")
    
    if disconnected:
        logger.warning(f"Disconnected players found: game_id={game_id}, count={len(disconnected)}")
        for player in disconnected:
            handle_player_disconnection(game_id, player['user_id'])
    
    return {
        "disconnected_count": len(disconnected),
        "disconnected_players": disconnected
    }


@app.post("/api/multiplayer/game/{game_id}/reconnect")
def reconnect_endpoint(game_id: int, req: GiveUpRequest):
    """Allow player to reconnect ."""
    logger.info(f"Reconnection attempt: game_id={game_id}, user_id={req.user_id}")
    
    success, message = allow_reconnection(game_id, req.user_id, timeout_minutes=5)
    
    if not success:
        logger.warning(f"Reconnection failed: game_id={game_id}, user_id={req.user_id}, message={message}")
        raise HTTPException(status_code=400, detail=message)
    
    logger.info(f"Reconnection successful: game_id={game_id}, user_id={req.user_id}")
    
    return {"success": True, "message": message}


@app.get("/api/multiplayer/game/{game_id}/results")
def get_results(game_id: int):
    """Get final game results."""
    logger.info(f"Results requested: game_id={game_id}")
    
    conn = get_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        query = """
            SELECT mg.game_id, mg.winner_id, mg.finished_at, mg.status
            FROM multiplayer_games mg
            WHERE mg.game_id = %s
        """
        cursor.execute(query, (game_id,))
        game = cursor.fetchone()
        
        if not game:
            cursor.close()
            raise HTTPException(status_code=404, detail="Game not found.")
        
        if game["status"] != "completed":
            cursor.close()
            raise HTTPException(status_code=400, detail="Game is not completed yet.")
        
        query = """
            SELECT mp.user_id, u.username, mp.score, mp.time_seconds, 
                   mp.hints_used, mp.errors_made, mp.completed
            FROM multiplayer_players mp
            JOIN users u ON mp.user_id = u.user_id
            WHERE mp.game_id = %s
            ORDER BY mp.score DESC
        """
        cursor.execute(query, (game_id,))
        players = cursor.fetchall()
        cursor.close()
        
        winner_username = None
        if game["winner_id"]:
            conn2 = get_connection()
            cursor2 = conn2.cursor(dictionary=True)
            cursor2.execute("SELECT username FROM users WHERE user_id = %s", (game["winner_id"],))
            winner = cursor2.fetchone()
            if winner:
                winner_username = winner["username"]
            cursor2.close()
            conn2.close()
        
        return {
            "game_id": game["game_id"],
            "winner_id": game["winner_id"],
            "winner_username": winner_username,
            "players": players,
            "finished_at": game["finished_at"]
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching results: {str(e)}")
    finally:
        conn.close()


@app.post("/api/multiplayer/game/{game_id}/give-up")
def give_up(game_id: int, req: GiveUpRequest):
    """Give up in multiplayer game."""
    conn = get_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        query = "SELECT game_id, status FROM multiplayer_games WHERE game_id = %s"
        cursor.execute(query, (game_id,))
        game = cursor.fetchone()
        
        if not game:
            cursor.close()
            raise HTTPException(status_code=404, detail="Game not found.")
        
        if game["status"] == "completed":
            cursor.close()
            raise HTTPException(status_code=400, detail="Game is already completed.")
        
        update_query = """
            UPDATE multiplayer_players 
            SET completed = TRUE, completed_at = NOW(), score = 0
            WHERE game_id = %s AND user_id = %s
        """
        cursor.execute(update_query, (game_id, req.user_id))
        conn.commit()
        
        check_query = """
            SELECT COUNT(*) as completed_count FROM multiplayer_players
            WHERE game_id = %s AND completed = TRUE
        """
        cursor.execute(check_query, (game_id,))
        result = cursor.fetchone()
        
        if result["completed_count"] == 2:
            success, message, results = save_multiplayer_result(game_id)
            cursor.close()
            
            if not success:
                raise HTTPException(status_code=500, detail=message)
            
            return {
                "success": True,
                "message": "Game ended",
                "results": results
            }
        
        cursor.close()
        return {"success": True, "message": "You gave up"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error giving up: {str(e)}")
    finally:
        conn.close()


@app.get("/api/multiplayer/history/{user_id}")
def get_history(user_id: int, limit: int = 20):
    """Get user's multiplayer game history."""
    conn = get_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        query = """
            SELECT mh.game_id, mh.opponent_id, u.username as opponent_username,
                   CASE 
                       WHEN mh.winner_id = %s THEN 'win'
                       ELSE 'loss'
                   END as result,
                   CASE 
                       WHEN mh.player1_id = %s THEN mh.player1_score
                       ELSE mh.player2_score
                   END as your_score,
                   CASE 
                       WHEN mh.player1_id = %s THEN mh.player2_score
                       ELSE mh.player1_score
                   END as opponent_score,
                   mh.played_at
            FROM multiplayer_history mh
            JOIN users u ON mh.opponent_id = u.user_id
            WHERE mh.player1_id = %s OR mh.player2_id = %s
            ORDER BY mh.played_at DESC
            LIMIT %s
        """
        cursor.execute(query, (user_id, user_id, user_id, user_id, user_id, limit))
        history = cursor.fetchall()
        cursor.close()
        
        return {"history": history}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching history: {str(e)}")
    finally:
        conn.close()


@app.get("/api/multiplayer/stats/{user_id}")
def get_stats(user_id: int):
    """Get user's multiplayer statistics."""
    conn = get_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        query = """
            SELECT 
                COUNT(*) as total_games,
                SUM(CASE WHEN winner_id = %s THEN 1 ELSE 0 END) as wins
            FROM multiplayer_history
            WHERE player1_id = %s OR player2_id = %s
        """
        cursor.execute(query, (user_id, user_id, user_id))
        stats = cursor.fetchone()
        
        total_games = stats["total_games"] or 0
        wins = stats["wins"] or 0
        losses = total_games - wins
        win_rate = (wins / total_games * 100) if total_games > 0 else 0
        query = """
            SELECT 
                AVG(CASE 
                    WHEN player1_id = %s THEN player1_score
                    ELSE player2_score
                END) as avg_score,
                MAX(CASE 
                    WHEN player1_id = %s THEN player1_score
                    ELSE player2_score
                END) as best_score
            FROM multiplayer_history
            WHERE player1_id = %s OR player2_id = %s
        """
        cursor.execute(query, (user_id, user_id, user_id, user_id))
        scores = cursor.fetchone()
        cursor.close()
        
        avg_score = scores["avg_score"] or 0
        best_score = scores["best_score"] or 0
        
        return {
            "total_multiplayer_games": total_games,
            "multiplayer_wins": wins,
            "multiplayer_losses": losses,
            "win_rate": round(win_rate, 2),
            "average_score": round(avg_score, 2),
            "best_score": best_score
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching stats: {str(e)}")
    finally:
        conn.close()


@app.get("/api/multiplayer/leaderboard")
def get_leaderboard(limit: int = 100):
    """Get multiplayer leaderboard."""
    conn = get_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        query = """
            SELECT 
                u.user_id, u.username, u.display_name,
                COUNT(mh.game_id) as total_games,
                SUM(CASE WHEN mh.winner_id = u.user_id THEN 1 ELSE 0 END) as wins,
                ROUND(SUM(CASE WHEN mh.winner_id = u.user_id THEN 1 ELSE 0 END) * 100.0 / COUNT(mh.game_id), 1) as win_rate,
                MAX(CASE 
                    WHEN mh.player1_id = u.user_id THEN mh.player1_score
                    ELSE mh.player2_score
                END) as best_score
            FROM users u
            LEFT JOIN multiplayer_history mh ON u.user_id = mh.player1_id OR u.user_id = mh.player2_id
            WHERE u.is_active = TRUE
            GROUP BY u.user_id, u.username, u.display_name
            HAVING COUNT(mh.game_id) > 0
            ORDER BY wins DESC, best_score DESC
            LIMIT %s
        """
        cursor.execute(query, (limit,))
        leaderboard = cursor.fetchall()
        cursor.close()
        
        return {"leaderboard": leaderboard}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching leaderboard: {str(e)}")
    finally:
        conn.close()


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


@app.get("/index.html")
def index():
    return _serve("index.html")


@app.get("/dashboard")
@app.get("/dashboard.html")
def dashboard():
    return _serve("dashboard.html")


@app.get("/game")
@app.get("/game.html")
def game():
    return _serve("game.html")

@app.get("/multiplayer")
@app.get("/multiplayer.html")
def multiplayer():
    return _serve("multiplayer.html")

@app.get("/game-multiplayer")
@app.get("/game-multiplayer.html")
def game_multiplayer():
    return _serve("game-multiplayer.html")

@app.get("/results-multiplayer")
@app.get("/results-multiplayer.html")
def results_multiplayer():
    return _serve("results-multiplayer.html")

@app.get("/test-multiplayer")
@app.get("/test-multiplayer.html")
def test_multiplayer():
    return _serve("test-multiplayer.html")


# SUDOKU (C++ Backend)

CPP_EXE = Path(__file__).parent / "cpp" / "sudoku.exe"

class PuzzleGenRequest(BaseModel):
    size: int      
    difficulty: int  

class HintRequest(BaseModel):
    size: int
    board: list  
    row: int
    col: int

class ValidateRequest(BaseModel):
    size: int
    board: list  

def call_cpp(operation: str, **kwargs) -> dict:
    """Call C++ executable with operation and return JSON result."""
    if not CPP_EXE.exists():
        raise HTTPException(status_code=500, detail=f"C++ executable not found at {CPP_EXE}")
    
    try:
        input_data = {"op": operation, **kwargs}
        input_json = json.dumps(input_data)
        
        result = subprocess.run(
            [str(CPP_EXE)],
            input=input_json,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        print(f"[DEBUG] Operation: {operation}")
        print(f"[DEBUG] Return code: {result.returncode}")
        print(f"[DEBUG] Stdout: {result.stdout}")
        print(f"[DEBUG] Stderr: {result.stderr}")
        
        if result.returncode != 0:
            raise HTTPException(status_code=500, detail=f"C++ error: {result.stderr}")
        
        if not result.stdout.strip():
            raise HTTPException(status_code=500, detail="C++ returned empty output")

        return json.loads(result.stdout)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=500, detail=f"Invalid C++ output format: {str(e)}")
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=500, detail="C++ operation timed out.")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Subprocess error: {str(e)}")


@app.post("/api/puzzle/generate")
def generate_puzzle(req: PuzzleGenRequest):
    """Generate a new sudoku puzzle."""
    if req.size not in [4, 9, 16]:
        raise HTTPException(status_code=400, detail="Size must be 4, 9, or 16.")
    if req.difficulty not in [1, 2, 3]:
        raise HTTPException(status_code=400, detail="Difficulty must be 1 (Easy), 2 (Medium), or 3 (Hard).")
    
    result = call_cpp("generate", size=req.size, difficulty=req.difficulty)
    return result


@app.post("/api/puzzle/hint")
def get_hint(req: HintRequest):
    """Get a hint for a specific cell."""
    if len(req.board) != req.size * req.size:
        raise HTTPException(status_code=400, detail="Board size mismatch.")
    if not (0 <= req.row < req.size and 0 <= req.col < req.size):
        raise HTTPException(status_code=400, detail="Invalid row or column.")
    
    result = call_cpp("hint", size=req.size, board=req.board, row=req.row, col=req.col)
    return result


@app.post("/api/puzzle/validate")
def validate_puzzle(req: ValidateRequest):
    """Validate if the board is correctly filled."""
    if len(req.board) != req.size * req.size:
        raise HTTPException(status_code=400, detail="Board size mismatch.")
    
    result = call_cpp("validate", size=req.size, board=req.board)
    return result


@app.post("/api/puzzle/solve")
def solve_puzzle(req: ValidateRequest):
    """Solve the puzzle and return the complete solution."""
    if len(req.board) != req.size * req.size:
        raise HTTPException(status_code=400, detail="Board size mismatch.")
    
    result = call_cpp("solve", size=req.size, board=req.board)
    return result


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
