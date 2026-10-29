# Deterministic Token Engine

## 📦 Installation
```bash
# Clone the repository (if not already)
cd /mnt/second_drive/Agent_system

# Set up a virtual environment and install the package in editable mode
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip setuptools
pip install -e .
```

## 🚀 Usage
```bash
# Run the CLI with a prompt (replace <your prompt> with your text)
source .venv/bin/activate
python -m token_engine.cli "<your prompt>"

# Allow the engine to exceed the token budget (override) when needed:
python -m token_engine.cli "<your prompt>" --allow-override
```

## 🛠️ How it works
- **Engine** (`engine.py`): Estimates token usage, enforces a configurable budget, and optionally overrides the limit.
- **Predictor** (`predictor.py`): Simple word‑count heuristic (replaceable with a ML model).
- **Rules** (`rules.py`): Defines the budget thresholds.
- **Audit** (`audit.py`): Logs each request as JSON‑lines and performs basic log rotation.
- **CLI** (`cli.py`): Provides a thin wrapper around the engine with an interactive confirmation step.

The component lives under `token_engine/` and can be imported as a Python SDK via `from token_engine import TokenEngine` for integration into larger agents.
