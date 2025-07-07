import logging
from typing import Any, Dict, List

from dotenv import load_dotenv
from inspect_ai import Task, task
from inspect_ai.dataset import Sample

from puzzles.tower_of_hanoi import TowerOfHanoi
from scorers.basic_scorers import (
    invalid_turns_scorer,
    moves_used_scorer,
    puzzle_solved_scorer,
    turns_taken_scorer,
)
from solvers.multi_turn import multi_turn_solver
from utils.config_loader import load_config
from utils.templates import load_templates

logger = logging.getLogger(__name__)
load_dotenv()

def get_puzzle_class(puzzle_type: str) -> type:
    puzzle_classes = {
        "tower_of_hanoi": TowerOfHanoi
    }

    if puzzle_type not in puzzle_classes:
        raise ValueError(f"Unsupported puzzle type: {puzzle_type}. "
                       f"Supported types: {list(puzzle_classes.keys())}")

    return puzzle_classes[puzzle_type]


def create_samples(config: Dict[str, Any]) -> List[Sample]:
    """Create samples for each puzzle size.

    Args:
        config: Configuration dictionary

    Returns:
        List of Sample objects
    """
    try:
        samples = []
        puzzle_sizes = config["puzzle_sizes"]
        puzzle_type = config["puzzle"]
        puzzle_class = get_puzzle_class(puzzle_type)

        for n in puzzle_sizes:
            sample = Sample(
                input="",  # Will be built by solver
                metadata={
                    "n": n,
                    "puzzle_type": puzzle_type,
                    "optimal_moves": puzzle_class(n).get_optimal_move_count()
                }
            )
            samples.append(sample)

        logger.info(f"Created {len(samples)} samples for puzzle sizes: {puzzle_sizes}")
        return samples

    except KeyError as e:
        raise ValueError(f"Missing required config key: {e}") from e


def validate_task_config(config: Dict[str, Any], templates: Dict[str, str]) -> None:
    """Validate task configuration and templates.

    Raises:
        ValueError: If validation fails
    """
    required_templates = {"system", "user_turn"}
    missing_templates = required_templates - set(templates.keys())
    if missing_templates:
        raise ValueError(f"Missing required templates: {missing_templates}")

    # Check puzzle type is supported
    get_puzzle_class(config.get("puzzle", "Unknown"))

    puzzle_sizes = config.get("puzzle_sizes", [])
    if not puzzle_sizes:
        raise ValueError("No puzzle sizes specified")

    for size in puzzle_sizes:
        if not isinstance(size, int) or size <= 0:
            raise ValueError(f"Invalid puzzle size: {size}. Must be positive integer.")

    logger.info("Task configuration validation passed")


@task
def tower_hanoi_experiment(config_path: str = "configs/default.py") -> Task:
    """Multi-turn Tower of Hanoi evaluation task.

    This task evaluates Large Language Models on the Tower of Hanoi puzzle
    using multi-turn interactions. Models can submit partial
    solutions and receive state feedback, addressing token limit constraints.

    Example:
        ```bash
        # Run with default config
        inspect eval src/run_experiment.py

        # Run with custom config
        inspect eval src/run_experiment.py -T config_path=configs/experiment_001.py

        # Run with model override
        inspect eval src/run_experiment.py --model openai/gpt-4
        ```
    """

    logger.debug("Initializing Tower of Hanoi experiment...")

    config = load_config(config_path)
    logger.debug(f"Loaded configuration from {config_path}")

    template_dir = config.get("prompt_template_dir", "./prompts/tower_of_hanoi/")
    templates = load_templates(template_dir)
    logger.debug(f"Loaded {len(templates)} templates from {template_dir}")

    validate_task_config(config, templates)
    puzzle_class = get_puzzle_class(config["puzzle"])

    task_obj = Task(
        dataset=create_samples(config),
        solver=multi_turn_solver(puzzle_class, config, templates),
        scorer=[puzzle_solved_scorer(), moves_used_scorer(), turns_taken_scorer(), invalid_turns_scorer()],
        model=config.get("model"),
        model_args = {
            "temperature": config.get("temperature", 1.0)
        }
    )

    logger.info(f"Task configuration: "
               f"puzzle={config['puzzle']}, "
               f"model={config.get('model')}, "
               f"temperature={config.get('temperature', 1.0)}")

    return task_obj
