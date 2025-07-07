from inspect_ai.scorer import (
    CORRECT,
    INCORRECT,
    Score,
    Scorer,
    Target,
    accuracy,
    scorer,
)
from inspect_ai.solver import TaskState

from puzzles.base import CompletionResult


@scorer(metrics=[accuracy()])
def puzzle_solved_scorer() -> Scorer:

    async def score(state: TaskState, target: Target) -> Score:
        completion_result = CompletionResult.from_json(state.metadata["puzzle_result_json"])
        return Score(value = CORRECT if completion_result.solved else INCORRECT)

    return score


@scorer(metrics=[accuracy()])
def turns_taken_scorer() -> Scorer:

    async def score(state: TaskState, target: Target) -> Score:
        completion_result = CompletionResult.from_json(state.metadata["puzzle_result_json"])
        return Score(value = completion_result.turns_taken, explanation = \
            f"Took {completion_result.turns_taken} turns to solve the puzzle")

    return score


@scorer(metrics=[accuracy()])
def moves_used_scorer() -> Scorer:

    async def score(state: TaskState, target: Target) -> Score:
        completion_result = CompletionResult.from_json(state.metadata["puzzle_result_json"])
        return Score(value = completion_result.successful_moves, explanation = \
            f"Attempted {completion_result.total_moves_attempted} moves,\
                 of which {completion_result.successful_moves} were successful")

    return score

@scorer(metrics=[accuracy()])
def invalid_turns_scorer() -> Scorer:

    async def score(state: TaskState, target: Target) -> Score:
        completion_result = CompletionResult.from_json(state.metadata["puzzle_result_json"])
        return Score(value = completion_result.invalid_turns, explanation = \
            f"Attempted {completion_result.invalid_turns} invalid turns")

    return score
