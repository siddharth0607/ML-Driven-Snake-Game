# ML Driven Snake Game

## Setup and Installation

# 1. Clone the repository
```bash
git clone https://siddharth0607/ml-driven-snake-game.git
cd ml-driven-snake-game
```

# 2. Create a virtual environment
```bash
python -m venv venv  
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

# 3. Install dependencies
```bash
pip install -r requirements.txt
```

# 4. Run the backend server
```bash
uvicorn backend.api:app --host 0.0.0.0 --port 8000 --reload
```

# 5. Run the frontend

Simply open `http://localhost:8000` in your browser.
