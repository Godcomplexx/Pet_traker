from pydantic import BaseModel, Field


class DailyMinesweeperOut(BaseModel):
    date: str
    size: int
    mine_count: int
    mines: list[list[int]]
    counts: list[list[int]]
    reward: int
    solved_today: bool
    best_seconds: int | None = None


class MinesweeperSolveIn(BaseModel):
    revealed: list[list[int]]
    seconds: int = Field(default=0, ge=0, le=86400)


class MinesweeperSolveOut(BaseModel):
    correct: bool
    coins_awarded: int
    coins: int
    already_solved: bool
    message: str
    best_seconds: int | None = None
    seconds: int | None = None


class MinesweeperScoreOut(BaseModel):
    user_id: str
    name: str
    seconds: int
    is_me: bool = False
