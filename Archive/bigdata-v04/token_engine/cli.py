"""
cli.py – Simple command‑line wrapper for the deterministic token engine.
"""

import argparse
import sys
from .engine import TokenEngine


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Deterministic Token Engine with confirm/override"
    )
    parser.add_argument("prompt", help="Prompt text to send to the model")
    parser.add_argument(
        "--allow-override",
        action="store_true",
        help="Temporarily allow token budget to be exceeded",
    )
    args = parser.parse_args()

    engine = TokenEngine()
    result = engine.process(args.prompt, allow_override=args.allow_override)

    if result == "THROTTLE_REQUIRED":
        # Interactive confirmation loop.
        answer = input(
            "Estimated token usage exceeds budget. Reduce token output? (y/n): "
        ).strip().lower()
        if answer in {"y", "yes"}:
            reduced = engine._run_model(args.prompt)[: len(args.prompt) // 2]
            print("✅ Reduced output:", reduced)
        else:
            print("❌ Full output returned.")
            print(engine._run_model(args.prompt))
    else:
        print("✅ Output:", result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
