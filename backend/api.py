from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Tuple
import json
import logging
from game_logic import GameEngine, Direction
from database import Database

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize game engine and database
game_engine = GameEngine()
db = Database()

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket

    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]

    async def broadcast(self, message: dict):
        for connection in self.active_connections.values():
            await connection.send_json(message)

manager = ConnectionManager()

@app.get("/")
async def root():
    return {"message": "Snake Game API"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "game_engine": "running"}

# Define Pydantic model for input validation
class GameStartRequest(BaseModel):
    player_name: str
    skills: List[str]

@app.post("/start_game")
async def start_game(request: GameStartRequest):
    """Initialize a new game for a player"""
    try:
        # Check if player already exists
        existing_player = db.get_player_by_name(request.player_name)
        if existing_player:
            return {"status": "error", "message": "Player already exists"}

        # Generate a unique player ID
        player_id = game_engine.initialize_player(request.player_name, request.skills)

        # Save player to database
        db.save_player(player_id, request.player_name, request.skills)
        
        return {"status": "success", "player_id": player_id}

    except Exception as e:
        logger.error(f"Error starting game: {e}")
        return {"status": "error", "message": str(e)}

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await manager.connect(websocket, client_id)
    logger.info(f"Client {client_id} connected to WebSocket")
    
    try:
        while True:
            data = await websocket.receive_json()
            logger.info(f"Received WebSocket data: {data}")

            # Validate message format
            if "type" not in data or data["type"] != "move":
                await websocket.send_json({"error": "Invalid message type"})
                continue

            if "snake_id" not in data or "direction" not in data:
                await websocket.send_json({"error": "Missing required fields"})
                continue
            
            snake_id = data["snake_id"]
            direction = data["direction"]

            # Validate direction format
            if not isinstance(direction, list) or len(direction) != 2 or not all(isinstance(i, int) for i in direction):
                await websocket.send_json({"error": "Invalid direction format, must be [x, y] integers"})
                continue

            direction_tuple = tuple(direction)

            if snake_id not in game_engine.snakes:
                await websocket.send_json({"error": f"Snake ID {snake_id} not found"})
                continue

            # Update game state
            game_engine.make_move(snake_id, direction_tuple)
            new_state = game_engine.update()
            
            # Convert state to JSON-serializable format
            state_dict = new_state.to_dict()
            
            # Broadcast new state
            await manager.broadcast({
                "type": "state_update",
                "state": state_dict
            })
            # Save game state if needed
            if new_state.game_over:
                db.save_game_result(client_id, new_state.to_dict())
                await websocket.send_json({"message": "Game over"})
                
    except WebSocketDisconnect:
        logger.info(f"Client {client_id} disconnected")
        manager.disconnect(client_id)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await websocket.send_json({"error": str(e)})
        manager.disconnect(client_id)

@app.get("/leaderboard")
async def get_leaderboard():
    """Get current leaderboard"""
    return db.get_leaderboard()

@app.get("/player/{player_id}/history")
async def get_player_history(player_id: str):
    """Get player's game history"""
    return db.get_player_history(player_id)