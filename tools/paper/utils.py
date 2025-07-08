import re

def _normalize_title(title: str) -> str:
    """Normalizes a title for comparison by lowercasing and removing non-alphanumeric chars."""
    return re.sub(r'[^a-z0-9]', '', title.lower())

def _get_config_for_step(config: dict, agent_name: str, step_name: str) -> dict:
    """Extracts the LLM configuration for a specific agent and step."""
    llm_name = config['agents'][agent_name][step_name]
    return config['llms'][llm_name] 