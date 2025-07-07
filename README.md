# Multi-Turn Tower of Hanoi Evaluation Framework

_Developed with help from Claude Code and Cursor_

An evaluation framework for testing Large Language Models (LLMs) on the Tower of Hanoi puzzle using multi-turn interactions. This framework addresses token limit constraints by allowing models to submit partial solutions and receive state feedback. Built on the [Inspect AI](https://github.com/UKGovernmentBEIS/inspect_ai) framework by UK AISI

Varela et. al. had the same idea and realized it sooner and more comprehensively. I recommend checking their findings here: [https://www.arxiv.org/pdf/2507.01231]

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Tests](https://img.shields.io/badge/tests-passing-green.svg)](./tests/)
[![Code Style](https://img.shields.io/badge/code%20style-black-black.svg)](https://github.com/psf/black)

## 🌟 Key Features

- **Multi-turn interaction**: Models can submit partial solutions and receive feedback
- **Token limit solution**: Eliminates context window constraints through sliding window management
- **Configurable evaluation**: Flexible configuration system for different experimental setups
- **Extensible design**: Easy to add new puzzles and evaluation metrics

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd multi-turn-tower-hanoi

# Install dependencies using uv (recommended)
uv pip install -r requirements.txt

# Or using pip
pip install -r requirements.txt
```

### Basic Usage

```bash
# Run evaluation with default configuration
inspect eval src/run_experiment.py

# Run with custom configuration
inspect eval src/run_experiment.py -T config_path=configs/custom.py

# Run with specific model
inspect eval src/run_experiment.py --model openai/gpt-4
```

## ⚙️ Configuration

Configuration is done through Python files in the `configs/` directory:

```python
# configs/default.py

# Model settings
model = "claude-3-sonnet-20240229"
temperature = 1.0

# Experiment settings
puzzle = "tower_of_hanoi"
puzzle_sizes = [1, 2, 3, 4, 5, 6, 7, 8, 10, 12, 15, 20]

# Scaling multipliers (relative to optimal moves)
turn_limit_multiplier = 2.0   # 2x optimal moves for turn limit
move_limit_multiplier = 10.0  # 10x optimal for total move attempts

# Termination conditions
repeated_invalid_limit = 3    # Stop after 3 identical invalid attempts
state_revisit_limit = 2       # Stop after visiting same state twice

# Sliding window size
window_size = 4              # Keep last 4 messages in context
```

## 🔧 Development

### Code Quality

The project maintains high code quality standards:

```bash
# Linting and formatting
make lint          # Check code quality
make lint-fix      # Auto-fix issues
make format        # Format code

# Tests
make test
make test-verbose

# Clean up
make clean         # Remove cache files
```

### Adding New Puzzles

1. Implement the `PuzzleInterface` in `src/puzzles/`
2. Add puzzle configuration options
3. Update puzzle class mapping in `run_experiment.py`
4. Add tests in `tests/test_puzzles.py`

Example:

```python
class MyPuzzle(PuzzleInterface):
    def get_initial_state(self, difficulty: int) -> str:
        # Implementation
        pass

    def apply_moves(self, moves: List[List[int]]) -> Union[str, InvalidMoveError]:
        # Implementation
        pass

    # ... other required methods
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
