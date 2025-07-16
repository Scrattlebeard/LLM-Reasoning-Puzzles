from collections import Counter
import logging
from typing import Any, Dict, List, Optional, Tuple, Union

from inspect_ai.model import ChatMessage, ChatMessageSystem, ChatMessageUser
from inspect_ai.solver import Generate, TaskState, solver

from src.puzzles.base import (
    CompletionResult,
    InvalidMoveError,
    PuzzleContext,
    PuzzleInterface,
)
from src.utils.templates import TemplateManager

logger = logging.getLogger(__name__)


class MultiTurnSolver:

    def __init__(
        self,
        puzzle: PuzzleInterface,
        config: Dict[str, Any],
        templates: Dict[str, str]
    ):
        """
        Args:
            puzzle: Puzzle instance implementing PuzzleInterface
            config: Configuration dictionary with solver parameters
            templates: Dictionary of prompt templates (system, user_first, user_turn)
        """
        self.puzzle = puzzle
        self.config = config
        self.templates = templates
        self.template_manager = TemplateManager()

        self.turn_limit_multiplier = config.get("turn_limit_multiplier", 2.0)
        self.move_limit_multiplier = config.get("move_limit_multiplier", 10.0)
        self.window_size = config.get("window_size", 4)
        self.repeated_invalid_limit = config.get("repeated_invalid_limit", 3)
        self.state_revisit_limit = config.get("state_revisit_limit", 2)

        logger.debug(f"Initialized MultiTurnSolver with config: {config}")

    async def solve(self, state: TaskState, generate: Generate) -> TaskState:
        """
        Args:
            state: Current Inspect AI task state
            generate: Generate function for model interaction
        """

        try:
            context = self._initialize_context()
            logger.debug("Context initialized...")

            system_message = ChatMessageSystem(content=self.templates.get("system", ""))
            context.full_conversation_history.append(system_message)

            should_terminate, termination_reason = False, ""
            while not should_terminate:

                state.messages = self._build_messages_with_window(context)

                logger.debug(f"Turn {context.turn_count + 1}: Generating model response")
                state = await generate(state)
                moves, parse_error = self._process_model_response(state.output.completion)

                if not moves:
                    if parse_error:
                        logger.info(f"Parse error, treating as give up: {parse_error}")
                        should_terminate, termination_reason = True, "parse_error"
                    else:
                        logger.info("Model gave up")
                        should_terminate, termination_reason = True, "gave_up"
                    break

                result = self.puzzle.apply_moves(moves)
                self._update_context_after_moves(context, result, moves)

                logger.debug(f"Turn {context.turn_count} completed: {len(moves)} moves attempted")
                should_terminate, termination_reason = self.should_terminate(context, self.config, self.puzzle)

            completion_result = CompletionResult(
                solved=self.puzzle.is_solved(),
                termination_reason=termination_reason,
                turns_taken=context.turn_count,
                total_moves_attempted=context.total_moves,
                invalid_turns=context.invalid_turns,
                successful_moves=context.successful_moves,
                puzzle_size=self.puzzle.size()
            )

            # Restore full conversation history
            state.messages = context.full_conversation_history
            state.metadata["puzzle_result_json"] = completion_result.to_json()
            state.metadata["puzzle_context"] = context.to_dict()
            logger.info(f"Solve completed: {termination_reason}")
            return state

        except Exception as e:
            logger.error(f"Error in solve method: {e}")

            fallback_result = CompletionResult(
                solved=False,
                termination_reason="error",
                turns_taken=0,
                total_moves_attempted=0,
                invalid_turns=0,
                successful_moves=0,
                puzzle_size=state.metadata.get("n", 3)
            )
            state.output.completion = fallback_result.to_json()
            return state


    def _initialize_context(self) -> PuzzleContext:
        """Initialize a new puzzle context for the first turn.
        """
        return PuzzleContext(
            turn_count=0,
            total_moves=0,
            invalid_turns=0,
            successful_moves=0,
            recent_invalid_attempts=[],
            full_conversation_history=[]
        )


    def _build_messages_with_window(
        self,
        context: PuzzleContext
    ) -> List[ChatMessage]:
        """Build conversation messages with sliding window management."""
        logger.debug(f"Building messages for turn {context.turn_count}")

        user_message_content = self._build_user_message(context)
        new_user_message = ChatMessageUser(content=user_message_content)

        windowed_messages = self._apply_sliding_window(context.full_conversation_history)
        windowed_messages.append(new_user_message)

        logger.debug(f"Built {len(windowed_messages)} messages total")
        return windowed_messages


    def _build_user_message(self, context: PuzzleContext) -> str:
        """Create user message for current turn. """
        template = self.templates.get("user_turn", "")
        progress = f"Turn {context.turn_count + 1}" if context.turn_count > 0 else "This is your first turn."
        error_message = f"\nPrevious move was invalid: {context.recent_invalid_attempts[-1]}\n\n"\
             if context.recent_invalid_attempts else ""

        return self.template_manager.format_template(
            template,
            progress=progress,
            current_state=self.puzzle.get_state(),
            error_message=error_message,
            move_format=self.puzzle.get_move_format()
        )


    def _apply_sliding_window(self, messages: List[ChatMessage]) -> List[ChatMessage]:
        """Apply sliding window to manage conversation history length."""
        #Check for system message.
        system_message = messages[0] if (messages and messages[0].role == "system") else None
        start_index = 1 if system_message else 0

        if len(messages) <= self.window_size + start_index:
            return messages.copy()

        available_slots = self.window_size
        total_non_system_messages = len(messages) - start_index
        messages_to_keep = min(available_slots, total_non_system_messages)

        truncated_messages = [system_message] if system_message else []

        if total_non_system_messages > messages_to_keep:
            truncation_marker = ChatMessageSystem(
                content="[History truncated - earlier turns omitted]"
            )
            truncated_messages.append(truncation_marker)

        recent_messages = messages[-(messages_to_keep):]
        truncated_messages.extend(recent_messages)

        logger.debug(f"Applied sliding window: {len(messages)} -> {len(truncated_messages)} messages")
        return truncated_messages


    def _process_model_response(
        self,
        response: str
    ) -> Tuple[List[List[int]], Optional[str]]:
        """Process LLM response to extract moves and detect errors.

        Returns:
            Tuple of (moves_list, error_message)
            - moves_list: Parsed moves or empty list if parsing failed
            - error_message: Error description if parsing failed, None otherwise
        """
        logger.debug("Processing model response")

        try:
            moves = self.puzzle.parse_moves(response)
            if not moves:
                # Empty list indicates model is giving up
                logger.info("Model submitted empty move list (giving up)")
                return [], None

            logger.debug(f"Successfully parsed {len(moves)} moves: {moves}")
            return moves, None

        except Exception as e:
            error_msg = f"Failed to parse moves from response: {e!s}"
            logger.warning(f"Parse error: {error_msg}, raw response: {response}")
            return [], error_msg


    def _update_context_after_moves(
        self,
        context: PuzzleContext,
        result: Union[str, InvalidMoveError],
        moves: List[List[int]]
    ) -> None:
        """Update puzzle context after move application."""
        context.turn_count += 1
        logger.debug(f"Updated to turn {context.turn_count}")

        if isinstance(result, InvalidMoveError):
            self._handle_invalid_move(context, result)
        else:
            context.successful_moves += len(moves)
            context.total_moves += len(moves)
            context.recent_invalid_attempts.clear()

        logger.debug(f"Updated state: {context.successful_moves}/{context.total_moves} moves successful")


    def _handle_invalid_move(self, context: PuzzleContext, error: InvalidMoveError) -> None:
        """Handle invalid move by updating context with error information."""
        context.invalid_turns += 1
        context.total_moves += error.move_index + 1 # Add to total moves (even though they failed)
        #error_description = f"Move {error.move_index}:{error.move} failed: {error.reason}"
        context.recent_invalid_attempts.append(error.move)


    def should_terminate(self,
        context: PuzzleContext,
        config: Dict[str, Any],
        puzzle: PuzzleInterface
    ) -> Tuple[bool, str]:
        """Check if the solving process should terminate.

        Args:
            context: Current puzzle context with solving history
            config: Configuration dictionary with termination parameters
            puzzle: Puzzle instance implementing PuzzleInterface

        Returns:
            Tuple of (should_terminate, termination_reason)
            - should_terminate: True if solving should stop, False to continue
            - termination_reason: String describing why termination occurred

        Termination conditions checked in priority order:
        1. Puzzle is solved (highest priority)
        2. Turn limit exceeded
        3. Move limit exceeded
        4. Repeated invalid attempts (stuck)
        5. State revisit loops detected
        """
        logger.debug(f"Checking termination conditions for turn {context.turn_count}")

        check_functions = [
            lambda: self._check_puzzle_solved(puzzle),
            lambda: self._check_turn_limit(context, config, puzzle),
            lambda: self._check_move_limit(context, config, puzzle),
            lambda: self._check_repeated_invalid(context, config),
            lambda: self._check_state_loops(config),
        ]
        for check in check_functions:
            should_terminate, reason = check()
            if should_terminate:
                logger.info(f"Termination: {reason}")
                return True, reason

        logger.debug("No termination conditions met, continuing")
        return False, ""


    def _check_puzzle_solved(self, puzzle: PuzzleInterface) -> Tuple[bool, str]:
        """Check if the puzzle is in a solved state.
        """
        return (True, "Solved") if puzzle.is_solved() else (False, "")


    def _check_turn_limit(
        self,
        context: PuzzleContext,
        config: Dict[str, Any],
        puzzle: PuzzleInterface
    ) -> Tuple[bool, str]:

        turn_limit_multiplier = config.get("turn_limit_multiplier", 2.0)
        optimal_moves = puzzle.get_optimal_move_count()
        max_turns = int(turn_limit_multiplier * optimal_moves)

        current_turns = context.turn_count

        logger.debug(f"Turn limit check: {current_turns}/{max_turns} turns")
        return (True, "turn_limit") if current_turns >= max_turns else (False, "")


    def _check_move_limit(
        self,
        context: PuzzleContext,
        config: Dict[str, Any],
        puzzle: PuzzleInterface
    ) -> Tuple[bool, str]:

        move_limit_multiplier = config.get("move_limit_multiplier", 10.0)
        optimal_moves = puzzle.get_optimal_move_count()
        max_moves = int(move_limit_multiplier * optimal_moves)

        current_moves = context.total_moves

        logger.debug(f"Move limit check: {current_moves}/{max_moves} moves")
        return (True, "move_limit") if current_moves >= max_moves else (False, "")


    def _check_repeated_invalid(
        self,
        context: PuzzleContext,
        config: Dict[str, Any]
    ) -> Tuple[bool, str]:

        repeated_invalid_limit = config.get("repeated_invalid_limit", 3)
        recent_attempts = context.recent_invalid_attempts

        logger.debug(f"Repeated invalid check: {len(recent_attempts)} recent attempts")
        return (True, "stuck_invalid") if len(recent_attempts) >= repeated_invalid_limit else (False, "")


    def _check_state_loops(
        self,
        config: Dict[str, Any]
    ) -> Tuple[bool, str]:

        state_revisit_limit = config.get("state_revisit_limit", 2)
        state_history = self.puzzle.get_state_history()

        logger.debug(f"State loop check: {len(state_history)} states in history")

        if not state_history:
            return False, ""

        # Count occurrences of each state
        state_counts = Counter(state_history)

        for state, count in state_counts.items():
            if count > state_revisit_limit:
                logger.debug(f"State loop detected: state {state}... visited {count} times")
                return True, "stuck_loop"

        return False, ""

@solver
def multi_turn_solver(
    puzzle_class: type,
    config: Dict[str, Any],
    templates: Dict[str, str]
):
    async def solve(state: TaskState, generate: Generate) -> TaskState:
        """Async solve function for Inspect AI integration."""

        puzzle_size = state.metadata.get("n")
        puzzle = puzzle_class(puzzle_size)

        solver_instance = MultiTurnSolver(puzzle, config, templates)
        return await solver_instance.solve(state, generate)

    return solve

