"""Atlas-Bookmaker · BeeAI agent + 6 Granite-Bee tools."""
from pathlib import Path


def load_system_prompt() -> str:
    """Read system_v2.yaml and return the system_prompt string."""
    import yaml
    path = Path(__file__).parent / "prompts" / "system_v2.yaml"
    return yaml.safe_load(path.read_text())["system_prompt"]
