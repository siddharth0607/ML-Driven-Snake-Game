import logging
from typing import Tuple, Dict, Any
import json
from pathlib import Path
import time
from datetime import datetime

class UtilsError(Exception):
    """Custom exception for utilities-related errors"""
    pass

def setup_logging(log_path: str = "data/game_logs/game.log"):
    """Setup logging configuration"""
    try:
        Path(log_path).parent.mkdir(parents=True, exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_path),
                logging.StreamHandler()
            ]
        )
        logger = logging.getLogger(__name__)
        logger.info("Logging setup completed")
    except Exception as e:
        raise UtilsError(f"Failed to setup logging: {str(e)}")

def calculate_distance(pos1: Tuple[int, int], pos2: Tuple[int, int]) -> float:
    """Calculate Euclidean distance between two points"""
    try:
        return ((pos1[0] - pos2[0])**2 + (pos1[1] - pos2[1])**2)**0.5
    except Exception as e:
        raise UtilsError(f"Failed to calculate distance: {str(e)}")

def save_game_state(state: Dict[str, Any], path: str = "data/game_logs/states"):
    """Save game state to file"""
    try:
        Path(path).mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"game_state_{timestamp}.json"
        
        with open(Path(path) / filename, 'w') as f:
            json.dump(state, f, indent=2)
        
        logger = logging.getLogger(__name__)
        logger.info(f"Game state saved to {filename}")
        return filename
    except Exception as e:
        raise UtilsError(f"Failed to save game state: {str(e)}")

def load_game_state(filename: str) -> Dict[str, Any]:
    """Load game state from file"""
    try:
        with open(filename, 'r') as f:
            state = json.load(f)
        logger = logging.getLogger(__name__)
        logger.info(f"Game state loaded from {filename}")
        return state
    except Exception as e:
        raise UtilsError(f"Failed to load game state: {str(e)}")

def validate_game_state(state: Dict[str, Any]) -> bool:
    """Validate game state structure"""
    try:
        required_keys = ['board_size', 'snakes', 'tokens', 'score', 'game_over', 'tick', 'players']
        return all(key in state for key in required_keys)
    except Exception as e:
        raise UtilsError(f"Failed to validate game state: {str(e)}")