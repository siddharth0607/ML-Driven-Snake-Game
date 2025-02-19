from dataclasses import dataclass
from typing import List, Tuple, Dict, Optional, Any
import numpy as np
import json
from enum import Enum
import logging
from datetime import datetime
import random

# Set up logging with more detailed format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('game.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class GameError(Exception):
    """Custom exception for game-related errors"""
    pass

class Direction(Enum):
    UP = (0, -1)
    DOWN = (0, 1)
    LEFT = (-1, 0)
    RIGHT = (1, 0)

class SkillDomain(Enum):
    FRONTEND = "frontend"
    BACKEND = "backend"
    DATABASE = "database"
    ML = "ml"
    CLOUD = "cloud"

@dataclass
class Token:
    position: Tuple[int, int]
    domain: str
    value: int
    active: bool = True
    created_at: float = datetime.now().timestamp()

    def to_dict(self) -> dict:
        return {
            'position': self.position,
            'domain': self.domain,
            'value': self.value,
            'active': self.active,
            'created_at': self.created_at
        }

class Snake:
    def __init__(self, domain: str, start_pos: Tuple[int, int], player_id: str):
        if not isinstance(start_pos, tuple) or len(start_pos) != 2:
            raise GameError("Invalid start position format")
            
        self.domain = domain
        self.body = [start_pos]
        self.direction = Direction.RIGHT.value
        self.score = 0
        self.collected_tokens = []
        self.player_id = player_id
        self.is_alive = True
        self.last_move_timestamp = datetime.now().timestamp()
        self.moves_history = []

    def move(self, grow: bool = False) -> None:
        try:
            new_head = (
                self.body[0][0] + self.direction[0],
                self.body[0][1] + self.direction[1]
            )
            self.body.insert(0, new_head)
            if not grow:
                self.body.pop()
            self.moves_history.append({
                'position': new_head,
                'timestamp': datetime.now().timestamp()
            })
        except Exception as e:
            logger.error(f"Error moving snake: {e}")
            raise GameError(f"Failed to move snake: {str(e)}")

    def change_direction(self, new_direction: Tuple[int, int]) -> bool:
        if not isinstance(new_direction, tuple) or len(new_direction) != 2:
            raise GameError("Invalid direction format")
            
        if (new_direction[0] * -1, new_direction[1] * -1) == self.direction:
            return False
        self.direction = new_direction
        return True

    def check_self_collision(self) -> bool:
        return self.body[0] in self.body[1:]

    def to_dict(self) -> dict:
        return {
            'domain': self.domain,
            'body': self.body,
            'direction': self.direction,
            'score': self.score,
            'player_id': self.player_id,
            'is_alive': self.is_alive,
            'collected_tokens': self.collected_tokens,
            'last_move_timestamp': self.last_move_timestamp,
            'moves_count': len(self.moves_history)
        }

class GameState:
    def __init__(self, board_size: Tuple[int, int]):
        if not isinstance(board_size, tuple) or len(board_size) != 2:
            raise GameError("Invalid board size format")
            
        self.board_size = board_size
        self.snakes: Dict[str, Snake] = {}
        self.tokens: List[Token] = []
        self.score = 0
        self.game_over = False
        self.tick = 0
        self.players: Dict[str, dict] = {}
        self.start_time = datetime.now().timestamp()

    def to_dict(self) -> dict:
        return {
            'board_size': self.board_size,
            'snakes': {k: v.to_dict() for k, v in self.snakes.items()},
            'tokens': [t.to_dict() for t in self.tokens],
            'score': self.score,
            'game_over': self.game_over,
            'tick': self.tick,
            'players': self.players,
            'start_time': self.start_time
        }


class GameEngine:
    def __init__(self, board_size: Tuple[int, int] = (30, 30)):
        if not isinstance(board_size, tuple) or len(board_size) != 2:
            raise GameError("Invalid board size format")
            
        self.board_size = board_size
        self.state = GameState(board_size)
        self.snakes = {}  # ✅ Explicitly storing snakes
        self.min_tokens = 5
        self.token_spawn_rate = 0.1
        self.max_players = 4
        logger.info(f"Game engine initialized with board size {board_size}")

    def _get_random_empty_position(self) -> Tuple[int, int]:
        max_attempts = 100
        attempts = 0
        
        while attempts < max_attempts:
            pos = (
                np.random.randint(0, self.board_size[0]),
                np.random.randint(0, self.board_size[1])
            )
            if self._is_position_empty(pos):
                return pos
            attempts += 1
            
        raise GameError("Could not find empty position on board")
    
    def _is_position_empty(self, pos: Tuple[int, int]) -> bool:
        """Check if a given position is empty (not occupied by a snake or a token)."""
        for snake in self.state.snakes.values():
            if pos in snake.body:
                return False
        
        for token in self.state.tokens:
            if token.active and token.position == pos:
                return False
                
        return True


    def reset(self) -> GameState:
        self.state = GameState(self.board_size)
        self.snakes = {}  # ✅ Reset snakes separately
        self._spawn_initial_tokens()
        logger.info("Game state reset")
        return self.state
    
    def _spawn_token(self) -> None:
        try:
            position = self._get_random_empty_position()
            domain = random.choice([d.value for d in SkillDomain])
            value = random.randint(1, 10)
            token = Token(position, domain, value)
            self.state.tokens.append(token)
            logger.info(f"Spawned token at position {position}")
        except GameError as e:
            logger.error(f"Failed to spawn token: {e}")


    def initialize_player(self, player_name: str, skills: List[str]) -> str:
        if len(self.state.players) >= self.max_players:
            raise GameError("Maximum number of players reached")
            
        if not skills or not all(skill in [s.value for s in SkillDomain] for skill in skills):
            raise GameError("Invalid skills provided")

        player_id = f"player_{len(self.state.players)}"
        self.state.players[player_id] = {
            'name': player_name,
            'skills': skills,
            'score': 0,
            'joined_at': datetime.now().timestamp()
        }

        for skill in skills:
            try:
                start_pos = self._get_random_empty_position()
                snake_id = f"{player_id}_{skill}"
                snake = Snake(skill, start_pos, player_id)
                
                self.state.snakes[snake_id] = snake  # ✅ Keep in GameState
                self.snakes[snake_id] = snake  # ✅ Also store in GameEngine
                
            except Exception as e:
                logger.error(f"Error initializing snake for skill {skill}: {e}")
                raise GameError(f"Failed to initialize snake: {str(e)}")

        logger.info(f"Player {player_name} initialized with skills {skills}")
        return player_id

    def update(self) -> GameState:
        self.state.tick += 1

        for snake_id, snake in self.snakes.items():  # ✅ Use self.snakes instead
            if not snake.is_alive:
                continue

            try:
                snake.move()
                head = snake.body[0]
                
                # Check wall collision
                if (head[0] < 0 or head[0] >= self.board_size[0] or
                    head[1] < 0 or head[1] >= self.board_size[1]):
                    snake.is_alive = False
                    logger.info(f"Snake {snake.player_id} hit wall")
                    continue

                # Check self collision
                if snake.check_self_collision():
                    snake.is_alive = False
                    logger.info(f"Snake {snake.player_id} hit itself")
                    continue

                self._check_token_collection(snake)
            except Exception as e:
                logger.error(f"Error updating snake {snake.player_id}: {e}")
                snake.is_alive = False

        if len([t for t in self.state.tokens if t.active]) < self.min_tokens:
            self._spawn_token()

        self.state.game_over = not any(snake.is_alive for snake in self.snakes.values())
        return self.state

    def make_move(self, snake_id: str, direction: Tuple[int, int]) -> bool:
        if snake_id not in self.snakes:  # ✅ Check self.snakes
            raise GameError(f"Invalid snake ID: {snake_id}")

        snake = self.snakes[snake_id]
        if not snake.is_alive:
            return False

        try:
            return snake.change_direction(direction)
        except Exception as e:
            logger.error(f"Error making move for snake {snake_id}: {e}")
            raise GameError(f"Failed to make move: {str(e)}")

    def get_state(self) -> dict:
        return self.state.to_dict()

if __name__ == "__main__":
    # Test the game engine
    engine = GameEngine()
    try:
        player_id = engine.initialize_player("TestPlayer", ["frontend", "backend"])
        
        for _ in range(5):
            state = engine.update()
            print(f"Tick {state.tick}: {len(state.tokens)} tokens active")
    except GameError as e:
        logger.error(f"Game error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
