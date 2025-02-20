from dataclasses import dataclass
from typing import List, Tuple, Dict, Optional
import numpy as np
import json
from enum import Enum
import logging
from datetime import datetime
import random

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('game.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

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

    @classmethod
    def get_skills(cls) -> Dict[str, List[str]]:
        return {
            "frontend": ["HTML", "CSS", "JavaScript"],
            "backend": ["Python", "Java", "C++", ".NET"],
            "database": ["SQL", "NoSQL", "MySQL", "Oracle"],
            "ml": ["ML", "DL", "AI"],
            "cloud": ["AWS", "Azure"]
        }

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
        self.domain = domain
        self.body = [start_pos]
        self.direction = Direction.RIGHT.value
        self.score = 0
        self.collected_tokens = []
        self.player_id = player_id
        self.is_alive = True
        self.last_move_timestamp = datetime.now().timestamp()

    def move(self, grow: bool = False) -> None:
        new_head = (
            self.body[0][0] + self.direction[0],
            self.body[0][1] + self.direction[1]
        )
        self.body.insert(0, new_head)
        if not grow:
            self.body.pop()
        self.last_move_timestamp = datetime.now().timestamp()

    def change_direction(self, new_direction: Tuple[int, int]) -> bool:
        if (new_direction[0] * -1, new_direction[1] * -1) == self.direction:
            return False
        self.direction = new_direction
        return True

    def check_collision(self, position: Tuple[int, int]) -> bool:
        return position in self.body

    def to_dict(self) -> dict:
        return {
            'domain': self.domain,
            'body': self.body,
            'direction': self.direction,
            'score': self.score,
            'player_id': self.player_id,
            'is_alive': self.is_alive,
            'collected_tokens': self.collected_tokens
        }

class GameState:
    def __init__(self, board_size: Tuple[int, int]):
        self.board_size = board_size
        self.snakes: Dict[str, Snake] = {}
        self.tokens: List[Token] = []
        self.score = 0
        self.game_over = False
        self.tick = 0
        self.start_time = datetime.now().timestamp()

    def to_dict(self) -> dict:
        return {
            'board_size': self.board_size,
            'snakes': {k: v.to_dict() for k, v in self.snakes.items()},
            'tokens': [t.to_dict() for t in self.tokens],
            'score': self.score,
            'game_over': self.game_over,
            'tick': self.tick,
            'start_time': self.start_time
        }

class GameEngine:
    def __init__(self, board_size: Tuple[int, int] = (30, 30)):
        self.board_size = board_size
        self.state = GameState(board_size)
        self.min_tokens = 5
        self.token_spawn_rate = 0.1

    def _get_random_empty_position(self) -> Tuple[int, int]:
        max_attempts = 100
        for _ in range(max_attempts):
            pos = (
                random.randint(0, self.board_size[0] - 1),
                random.randint(0, self.board_size[1] - 1)
            )
            if self._is_position_empty(pos):
                return pos
        raise ValueError("No empty position found")

    def _is_position_empty(self, pos: Tuple[int, int]) -> bool:
        for snake in self.state.snakes.values():
            if pos in snake.body:
                return False
        for token in self.state.tokens:
            if token.active and token.position == pos:
                return False
        return True

    def _spawn_token(self) -> None:
        try:
            position = self._get_random_empty_position()
            domain = random.choice(list(SkillDomain)).value
            value = random.randint(1, 10)
            self.state.tokens.append(Token(position, domain, value))
        except Exception as e:
            logger.error(f"Failed to spawn token: {e}")

    def initialize_player(self, player_name: str, skills: List[str]) -> str:
        player_id = f"player_{len(self.state.snakes)}"
        
        for skill in skills:
            start_pos = self._get_random_empty_position()
            snake = Snake(skill, start_pos, player_id)
            snake_id = f"{player_id}_{skill}"
            self.state.snakes[snake_id] = snake

        while len([t for t in self.state.tokens if t.active]) < self.min_tokens:
            self._spawn_token()

        return player_id

    def update(self) -> GameState:
        self.state.tick += 1

        # Update all snakes
        for snake_id, snake in self.state.snakes.items():
            if not snake.is_alive:
                continue

            # Move snake
            snake.move()
            head = snake.body[0]

            # Check wall collision
            if (head[0] < 0 or head[0] >= self.board_size[0] or
                head[1] < 0 or head[1] >= self.board_size[1]):
                snake.is_alive = False
                continue

            # Check self collision
            if snake.check_collision(head):
                snake.is_alive = False
                continue

            # Check token collection
            for token in self.state.tokens:
                if token.active and token.position == head:
                    token.active = False
                    snake.score += token.value
                    snake.collected_tokens.append(token.domain)
                    self.state.score += token.value

        # Spawn new tokens if needed
        if len([t for t in self.state.tokens if t.active]) < self.min_tokens:
            self._spawn_token()

        # Check game over
        self.state.game_over = not any(snake.is_alive for snake in self.state.snakes.values())

        return self.state

    def make_move(self, snake_id: str, direction: Tuple[int, int]) -> bool:
        if snake_id not in self.state.snakes:
            return False
        snake = self.state.snakes[snake_id]
        if not snake.is_alive:
            return False
        return snake.change_direction(direction)

    def get_state(self) -> dict:
        return self.state.to_dict()
