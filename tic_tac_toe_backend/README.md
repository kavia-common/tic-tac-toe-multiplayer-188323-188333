# Tic Tac Toe Backend (FastAPI)

This service exposes REST endpoints to manage and play Tic Tac Toe games. It uses an in-memory store for game state and can be extended to use a database later.

## Run locally

- Install dependencies: `pip install -r requirements.txt`
- Start: `uvicorn src.api.main:app --reload --port 3001`
- Open API docs: http://localhost:3001/docs

CORS is configured to allow requests from http://localhost:3000 (the frontend).

## Endpoints

- POST /games
  - Summary: Create a new game
  - Response 201: `{ "gameId": "<uuid>" }`

- GET /games/{gameId}
  - Summary: Fetch current game state
  - Response 200:
    ```
    {
      "board": ["", "", "", "", "", "", "", "", ""],
      "nextPlayer": "X",
      "status": "IN_PROGRESS"
    }
    ```
  - 404 if gameId not found

- POST /games/{gameId}/moves
  - Summary: Make a move at a position 0..8
  - Request: `{ "position": 0 }`
  - Response 200: Updated game state
  - 400 on invalid move (finished game, occupied cell, invalid position)
  - 404 if gameId not found

## Status values

- IN_PROGRESS
- X_WON
- O_WON
- DRAW

## Notes

- Storage is in-memory (process local). Restarting the server clears all games.
- Turn order enforced (X starts, then O, and so on).
- Win/draw detection is applied after each move.
