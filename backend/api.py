from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import List, Dict
import logging
import os
from game_logic import GameEngine, Direction, SkillDomain
from database import Database

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Update the static files configuration in api.py
frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))
static_dir = os.path.join(frontend_dir, "static")

# Create static directory if it doesn't exist
os.makedirs(static_dir, exist_ok=True)

# Mount static files
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Initialize components
game_engine = GameEngine()
db = Database()

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket
        logger.info(f"Client {client_id} connected")

    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            logger.info(f"Client {client_id} disconnected")

    async def broadcast(self, message: dict):
        disconnected_clients = []
        for client_id, connection in self.active_connections.items():
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting to client {client_id}: {e}")
                disconnected_clients.append(client_id)
        
        for client_id in disconnected_clients:
            self.disconnect(client_id)

manager = ConnectionManager()

@app.get("/")
async def serve_index():
    index_path = os.path.join(frontend_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    raise HTTPException(status_code=404, detail="index.html not found")

@app.get("/health")
async def health_check():
    return {"status": "healthy", "game_engine": "running"}

class GameStartRequest(BaseModel):
    player_name: str
    skills: List[str]

@app.post("/start_game")
async def start_game(request: GameStartRequest):
    try:
        # Validate skills
        valid_skills = [s.value for s in SkillDomain]
        if not all(skill in valid_skills for skill in request.skills):
            return JSONResponse(
                status_code=400,
                content={"status": "error", "message": "Invalid skills provided"}
            )

        # Initialize player
        player_id = game_engine.initialize_player(request.player_name, request.skills)
        db.save_player(player_id, request.player_name, request.skills)

        return {
            "status": "success",
            "player_id": player_id,
            "game_state": game_engine.get_state()
        }
    except Exception as e:
        logger.error(f"Error starting game: {e}")
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)}
        )

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await manager.connect(websocket, client_id)
    try:
        while True:
            data = await websocket.receive_json()
            if data["type"] == "move":
                snake_id = data["snake_id"]
                direction = Direction[data["direction"].upper()].value
                game_engine.make_move(snake_id, direction)
                new_state = game_engine.update()
                
                await manager.broadcast({
                    "type": "state_update",
                    "state": new_state.to_dict()
                })

                if new_state.game_over:
                    db.save_game_result(client_id, new_state.to_dict())
                    await manager.broadcast({
                        "type": "game_over",
                        "final_score": new_state.score
                    })
    except WebSocketDisconnect:
        manager.disconnect(client_id)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(client_id)

@app.get("/leaderboard")
async def get_leaderboard():
    try:
        return db.get_leaderboard()
    except Exception as e:
        logger.error(f"Error fetching leaderboard: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch leaderboard")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)