#!/usr/bin/env python3
"""
Extract model list and config info from the cursor-agent CLI.

Usage:
    python3 scripts/extract-models.py [--json]

Output:
    - cursor-agent version
    - model count
    - model list (one per line, or JSON with --json)
    - config info (backend URL, agent URL, selected model, auth email)
"""

import argparse
import json
import os
import shutil
import subprocess
import sys


def find_agent() -> str:
    """Find the cursor-agent binary."""
    home = os.path.expanduser("~")
    candidates = [
        os.path.join(home, ".local", "bin", "cursor-agent"),
        shutil.which("cursor-agent"),
    ]
    for path in candidates:
        if path and os.path.isfile(path) and os.access(path, os.X_OK):
            return path

    print("ERROR: cursor-agent not found.", file=sys.stderr)
    print("Install via: curl -fsS https://cursor.com/install | bash", file=sys.stderr)
    sys.exit(1)


def run_agent(args: list[str]) -> str:
    """Run cursor-agent with given args and return stdout."""
    agent = find_agent()
    try:
        result = subprocess.run(
            [agent] + args,
            capture_output=True,
            text=True,
            timeout=30,
        )
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        print(f"ERROR: cursor-agent {' '.join(args)} timed out", file=sys.stderr)
        return ""
    except FileNotFoundError:
        print(f"ERROR: {agent} not found", file=sys.stderr)
        sys.exit(1)


def get_config_info() -> dict:
    """Read cursor CLI config."""
    config_path = os.path.join(os.path.expanduser("~"), ".cursor", "cli-config.json")
    if not os.path.isfile(config_path):
        return {}

    try:
        with open(config_path) as f:
            config = json.load(f)
        return {
            "backendUrl": config.get("serverConfigCache", {}).get("backendUrl"),
            "agentUrl": config.get("serverConfigCache", {}).get("agentUrlConfig", {}).get("agentUrl"),
            "version": config.get("version"),
            "selectedModel": config.get("selectedModel"),
            "authEmail": config.get("authInfo", {}).get("email"),
        }
    except (json.JSONDecodeError, OSError) as e:
        return {"error": str(e)}


def main():
    parser = argparse.ArgumentParser(
        description="Extract model list and config info from cursor-agent CLI"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output model list in JSON format",
    )
    args = parser.parse_args()

    # Version
    version = run_agent(["--version"])
    print(f"=== cursor-agent version ===")
    print(version)
    print()

    # Model list
    if args.json:
        models = run_agent(["models", "--format", "json"])
        if not models:
            # Fallback: parse the text output and build JSON
            models_text = run_agent(["models"])
            model_list = []
            for line in models_text.split("\n"):
                line = line.strip()
                if not line or line.startswith("Available") or line.startswith("Tip:"):
                    continue
                parts = line.split(" - ", 1)
                if len(parts) == 2:
                    model_list.append({"id": parts[0].strip(), "name": parts[1].strip()})
            models = json.dumps(model_list, indent=2)
        print("=== Model list (JSON) ===")
        print(models)
    else:
        models = run_agent(["models"])
        count = len([l for l in models.split("\n") if l.strip() and not l.startswith(" ")])
        print(f"=== Model count: {count} ===")
        print()
        print("=== Model list ===")
        print(models)

    print()

    # Config info
    config = get_config_info()
    print("=== Config info ===")
    print(json.dumps(config, indent=2))


if __name__ == "__main__":
    main()
