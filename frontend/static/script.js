class SnakeGame {
    constructor() {
        this.canvas = document.getElementById('game-canvas');
        this.ctx = this.canvas.getContext('2d');
        this.canvas.width = 600;
        this.canvas.height = 600;
        this.cellSize = 20;
        this.boardSize = [30, 30];
        this.websocket = null;
        this.playerId = null;
        this.gameState = null;
        this.isPaused = false;
        this.setupEventListeners();
    }

    setupEventListeners() {
        document.getElementById('start-form').addEventListener('submit', (e) => {
            e.preventDefault();
            this.startGame();
        });

        document.addEventListener('keydown', (e) => {
            if (!this.isPaused && this.gameState) {
                this.handleKeyPress(e);
            }
        });

        document.getElementById('pause-btn').addEventListener('click', () => this.togglePause());
        document.getElementById('restart-btn').addEventListener('click', () => this.restartGame());
        document.getElementById('play-again-btn').addEventListener('click', () => this.showScreen('start-screen'));
    }

    async startGame() {
        const playerName = document.getElementById('player-name').value;
        console.log(playerName)
        const selectedSkills = Array.from(
            document.querySelectorAll('.skills-selection input[type="checkbox"]:checked')
        ).map(checkbox => checkbox.value);
        console.log(selectedSkills)
        if (!playerName.trim()) {
            alert('Please enter your name!');
            return;
        }
    
        if (selectedSkills.length === 0) {
            alert('Please select at least one skill!');
            return;
        }
    
        try {
            const response = await fetch('/start_game', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    player_name: playerName,
                    skills: selectedSkills
                })
            });
    
            const data = await response.json();
            if (data.status === 'success') {
                this.playerId = data.player_id;
                this.gameState = data.game_state;
                this.connectWebSocket();
                this.showScreen('game-screen');
                this.startGameLoop();
            } else {
                alert('Failed to start game: ' + data.message);
            }
        } catch (error) {
            console.error('Error starting game:', error);
            alert('Failed to start game. Please try again.');
        }
    }

    connectWebSocket() {
        this.websocket = new WebSocket(`ws://${window.location.host}/ws/${this.playerId}`);
        
        this.websocket.onmessage = (event) => {
            const data = JSON.parse(event.data);
            if (data.type === 'state_update') {
                this.gameState = data.state;
                this.updateScore();
            } else if (data.type === 'game_over') {
                this.handleGameOver(data.final_score);
            }
        };
    }

    startGameLoop() {
        if (this.gameLoop) return;
        this.gameLoop = setInterval(() => {
            if (!this.isPaused && this.gameState) {
                this.drawGame();
            }
        }, 1000 / 15);
    }

    drawGame() {
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
        this.drawGrid();
        this.drawSnakes();
        this.drawTokens();
    }

    drawGrid() {
        this.ctx.strokeStyle = '#333';
        for (let i = 0; i <= this.canvas.width; i += this.cellSize) {
            this.ctx.beginPath();
            this.ctx.moveTo(i, 0);
            this.ctx.lineTo(i, this.canvas.height);
            this.ctx.stroke();
        }
        for (let i = 0; i <= this.canvas.height; i += this.cellSize) {
            this.ctx.beginPath();
            this.ctx.moveTo(0, i);
            this.ctx.lineTo(this.canvas.width, i);
            this.ctx.stroke();
        }
    }

    drawSnakes() {
        Object.values(this.gameState.snakes).forEach(snake => {
            this.ctx.fillStyle = this.getSnakeColor(snake.domain);
            snake.body.forEach(([x, y]) => {
                this.ctx.fillRect(
                    x * this.cellSize,
                    y * this.cellSize,
                    this.cellSize - 1,
                    this.cellSize - 1
                );
            });
        });
    }

    drawTokens() {
        this.gameState.tokens.forEach(token => {
            if (token.active) {
                this.ctx.fillStyle = this.getTokenColor(token.domain);
                this.ctx.beginPath();
                this.ctx.arc(
                    token.position[0] * this.cellSize + this.cellSize/2,
                    token.position[1] * this.cellSize + this.cellSize/2,
                    this.cellSize/2 - 1,
                    0,
                    Math.PI * 2
                );
                this.ctx.fill();
            }
        });
    }

    handleKeyPress(e) {
        const directions = {
            'ArrowUp': 'UP',
            'ArrowDown': 'DOWN',
            'ArrowLeft': 'LEFT',
            'ArrowRight': 'RIGHT'
        };

        if (directions[e.key] && this.websocket) {
            this.websocket.send(JSON.stringify({
                type: 'move',
                snake_id: `${this.playerId}_${this.gameState.snakes[0].domain}`,
                direction: directions[e.key]
            }));
        }
    }

    getSnakeColor(domain) {
        const colors = {
            'frontend': '#FF4136',
            'backend': '#2ECC40',
            'database': '#0074D9',
            'ml': '#B10DC9',
            'cloud': '#FF851B'
        };
        return colors[domain] || '#AAAAAA';
    }

    getTokenColor(domain) {
        const colors = {
            'frontend': '#FFCCCB',
            'backend': '#90EE90',
            'database': '#ADD8E6',
            'ml': '#E6E6FA',
            'cloud': '#FFE4B5'
        };
        return colors[domain] || '#DDDDDD';
    }

    updateScore() {
        document.getElementById('score').textContent = this.gameState.score;
    }

    handleGameOver(finalScore) {
        clearInterval(this.gameLoop);
        this.gameLoop = null;
        document.getElementById('final-score').textContent = `Final Score: ${finalScore}`;
        this.showScreen('game-over-screen');
        this.updateLeaderboard();
    }

    async updateLeaderboard() {
        try {
            const response = await fetch('/leaderboard');
            const leaderboard = await response.json();
            const list = document.getElementById('leaderboard-list');
            list.innerHTML = leaderboard
                .map((entry, i) => `<li>${i + 1}. ${entry.name}: ${entry.score}</li>`)
                .join('');
        } catch (error) {
            console.error('Error updating leaderboard:', error);
        }
    }

    showScreen(screenId) {
        ['start-screen', 'game-screen', 'game-over-screen'].forEach(id => {
            document.getElementById(id).classList.toggle('hidden', id !== screenId);
        });
    }

    togglePause() {
        this.isPaused = !this.isPaused;
        document.getElementById('pause-btn').textContent = this.isPaused ? 'Resume' : 'Pause';
    }

    restartGame() {
        if (this.websocket) {
            this.websocket.close();
        }
        clearInterval(this.gameLoop);
        this.gameLoop = null;
        this.showScreen('start-screen');
    }
}

document.addEventListener('DOMContentLoaded', () => {
    window.game = new SnakeGame();
});
