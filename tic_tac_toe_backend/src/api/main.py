from typing import Dict, List, Optional
import uuid
from fastapi import FastAPI, HTTPException, Path
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# PUBLIC_INTERFACE
class CreateGameResponse(BaseModel):
    """Response model for creating a new game."""
    gameId: str = Field(..., description="Unique identifier of the created game")

# PUBLIC_INTERFACE
class GameState(BaseModel):
    """Represents the full game state returned by API endpoints."""
    board: List[str] = Field(..., description="A list of 9 strings representing the board cells, each '', 'X', or 'O'")
    nextPlayer: str = Field(..., description="The player whose turn is next: 'X' or 'O'")
    status: str = Field(..., description="Game status: 'IN_PROGRESS' | 'X_WON' | 'O_WON' | 'DRAW'")

# PUBLIC_INTERFACE
class MoveRequest(BaseModel):
    """Request payload for making a move."""
    position: int = Field(..., ge=0, le=8, description="Board position index from 0 to 8")

class _Game:
    """Internal game representation for in-memory storage."""
    def __init__(self) -> None:
        # 9-cell board, empty string denotes empty cell
        self.board: List[str] = [""] * 9
        self.next_player: str = "X"
        self.status: str = "IN_PROGRESS"

    def to_state(self) -> GameState:
        """Convert internal game to API state."""
        return GameState(board=self.board.copy(), nextPlayer=self.next_player, status=self.status)

# In-memory storage for games: game_id -> _Game
_GAMES: Dict[str, _Game] = {}

def _check_winner(board: List[str]) -> Optional[str]:
    """Return 'X' or 'O' if there is a winner, or None otherwise."""
    winning_lines = [
        (0, 1, 2),
        (3, 4, 5),
        (6, 7, 8),  # rows
        (0, 3, 6),
        (1, 4, 7),
        (2, 5, 8),  # cols
        (0, 4, 8),
        (2, 4, 6),  # diags
    ]
    for a, b, c in winning_lines:
        if board[a] and board[a] == board[b] == board[c]:
            return board[a]
    return None

def _update_status(game: _Game) -> None:
    """Update the game's status based on current board."""
    winner = _check_winner(game.board)
    if winner == "X":
        game.status = "X_WON"
    elif winner == "O":
        game.status = "O_WON"
    elif all(cell in ("X", "O") for cell in game.board):
        game.status = "DRAW"
    else:
        game.status = "IN_PROGRESS"

app = FastAPI(
    title="Tic Tac Toe API",
    description="REST API for a simple multiplayer Tic Tac Toe game. Use the endpoints to create a game and make moves.",
    version="0.1.0",
    openapi_tags=[
        {"name": "Health", "description": "Basic health and info endpoints"},
        {"name": "Games", "description": "Create and manage Tic Tac Toe games"},
        {"name": "Moves", "description": "Make moves within a game"},
    ],
)

# Configure CORS to allow frontend access at http://localhost:3000
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# PUBLIC_INTERFACE
@app.get("/", tags=["Health"], summary="Health Check", description="Returns a simple JSON object to indicate the service is running.")
def health_check():
    """Health check endpoint."""
    return {"message": "Healthy"}

# PUBLIC_INTERFACE
@app.post(
    "/games",
    response_model=CreateGameResponse,
    tags=["Games"],
    summary="Create a new game",
    description="Creates a new Tic Tac Toe game and returns its unique gameId.",
    responses={
        201: {"description": "Game created"},
    },
    status_code=201,
)
def create_game() -> CreateGameResponse:
    """Create a new game with an empty board and X to start."""
    game_id = str(uuid.uuid4())
    _GAMES[game_id] = _Game()
    return CreateGameResponse(gameId=game_id)

# PUBLIC_INTERFACE
@app.get(
    "/games/{gameId}",
    response_model=GameState,
    tags=["Games"],
    summary="Fetch game state",
    description="Fetch the current state of a given game by its gameId.",
    responses={
        404: {"description": "Game not found", "content": {"application/json": {"example": {"detail": "Game not found"}}}},
    },
)
def get_game_state(
    gameId: str = Path(..., description="The unique identifier for the game to fetch")
) -> GameState:
    """Return the current game state for the provided gameId."""
    game = _GAMES.get(gameId)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    return game.to_state()

# PUBLIC_INTERFACE
@app.post(
    "/games/{gameId}/moves",
    response_model=GameState,
    tags=["Moves"],
    summary="Make a move",
    description=(
        "Make a move in the specified game. The server enforces turn-order, valid positions (0-8), "
        "and that a move can only be made on empty cells. Returns the updated game state. "
        "If the game is already finished, no more moves are allowed."
    ),
    responses={
        400: {
            "description": "Invalid move",
            "content": {"application/json": {"examples": {
                "Finished": {"summary": "Game finished", "value": {"detail": "Game is already finished"}},
                "Position": {"summary": "Invalid position", "value": {"detail": "Position must be between 0 and 8"}},
                "Occupied": {"summary": "Cell occupied", "value": {"detail": "Cell is already occupied"}},
            }}},
        },
        404: {"description": "Game not found", "content": {"application/json": {"example": {"detail": "Game not found"}}}},
    },
)
def make_move(
    payload: MoveRequest,
    gameId: str = Path(..., description="The unique identifier for the game to play in"),
) -> GameState:
    """Apply a move to the given game and return updated state."""
    game = _GAMES.get(gameId)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    # No moves allowed if finished
    if game.status != "IN_PROGRESS":
        raise HTTPException(status_code=400, detail="Game is already finished")

    pos = payload.position

    # Validate position (Pydantic already enforces bounds 0..8)
    if not (0 <= pos <= 8):
        # Defensive check; should be caught by model
        raise HTTPException(status_code=400, detail="Position must be between 0 and 8")

    # Validate cell is empty
    if game.board[pos] in ("X", "O"):
        raise HTTPException(status_code=400, detail="Cell is already occupied")

    # Place the symbol of the current player
    symbol = game.next_player
    game.board[pos] = symbol

    # Update status and next player
    _update_status(game)
    if game.status == "IN_PROGRESS":
        game.next_player = "O" if game.next_player == "X" else "X"

    return game.to_state()
