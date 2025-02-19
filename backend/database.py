import sqlite3
from typing import List, Dict
import json
import logging
from pathlib import Path
from fastapi import HTTPException

logger = logging.getLogger(__name__)

class DatabaseError(Exception):
    """Custom exception for database-related errors"""
    pass

class Database:
    def __init__(self, db_path: str = "data/player_data.db"):
        self.db_path = db_path
        try:
            self._init_db()
        except sqlite3.Error as e:
            logger.error(f"Database initialization failed: {e}")
            raise DatabaseError(f"Failed to initialize database: {str(e)}")

    def _init_db(self):
        """Initialize database with required tables"""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Create players table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS players (
                        player_id TEXT PRIMARY KEY,
                        name TEXT NOT NULL UNIQUE,
                        skills TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Create games table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS games (
                        game_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        player_id TEXT NOT NULL,
                        score INTEGER NOT NULL,
                        duration INTEGER NOT NULL,
                        state_data TEXT NOT NULL,
                        played_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (player_id) REFERENCES players (player_id)
                    )
                """)
                
                conn.commit()
                logger.info("Database initialized successfully")
        except sqlite3.Error as e:
            logger.error(f"Database initialization error: {e}")
            raise DatabaseError(f"Failed to create tables: {str(e)}")

    def save_player(self, player_id: str, name: str, skills: List[str]):
        """Save new player to database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO players (player_id, name, skills) VALUES (?, ?, ?)",
                    (player_id, name, json.dumps(skills))
                )
                conn.commit()
                logger.info(f"Player {name} saved successfully")
        except sqlite3.IntegrityError:
            raise DatabaseError(f"Player with name '{name}' already exists.")
        except sqlite3.Error as e:
            logger.error(f"Error saving player: {e}")
            raise DatabaseError(f"Failed to save player: {str(e)}")

    def save_game_result(self, player_id: str, final_state: dict):
        """Save game result to database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """INSERT INTO games 
                       (player_id, score, duration, state_data) 
                       VALUES (?, ?, ?, ?)""",
                    (
                        player_id,
                        final_state['score'],
                        final_state['tick'],
                        json.dumps(final_state)
                    )
                )
                conn.commit()
                logger.info(f"Game result saved for player {player_id}")
        except sqlite3.Error as e:
            logger.error(f"Error saving game result: {e}")
            raise DatabaseError(f"Failed to save game result: {str(e)}")

    def get_leaderboard(self, limit: int = 10) -> List[Dict]:
        """Get top players by score"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT p.name, g.score, g.played_at
                    FROM games g
                    JOIN players p ON g.player_id = p.player_id
                    ORDER BY g.score DESC
                    LIMIT ?
                """, (limit,))
                
                results = [
                    {
                        "name": row[0],
                        "score": row[1],
                        "played_at": row[2]
                    }
                    for row in cursor.fetchall()
                ]
                return results
        except sqlite3.Error as e:
            logger.error(f"Error fetching leaderboard: {e}")
            raise DatabaseError(f"Failed to fetch leaderboard: {str(e)}")

    def get_player_by_name(self, player_name: str):
        """Check if player already exists in the database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM players WHERE name = ?", (player_name,))
                return cursor.fetchone()
        except sqlite3.Error as e:
            logger.error(f"Error fetching player by name: {e}")
            raise DatabaseError(f"Failed to fetch player: {str(e)}")

    def get_player_history(self, player_id: str) -> List[Dict]:
        """Get player's game history"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT score, duration, played_at, state_data
                    FROM games
                    WHERE player_id = ?
                    ORDER BY played_at DESC
                """, (player_id,))
                
                results = cursor.fetchall()
                if not results:
                    return []

                return [
                    {
                        "score": row[0],
                        "duration": row[1],
                        "played_at": row[2],
                        "state_data": json.loads(row[3])
                    }
                    for row in results
                ]
        except sqlite3.Error as e:
            logger.error(f"Database error in get_player_history: {e}")
            raise DatabaseError(f"Failed to fetch player history: {str(e)}")