"""System prompts · v2 locked · firm-doctrine system prompt with strict-input rule."""
from pathlib import Path


def load_system_prompt() -> str:
    import yaml
    return yaml.safe_load((Path(__file__).parent / "system_v2.yaml").read_text())["system_prompt"]
