import random

_ADJECTIVES = [
    "swift", "calm", "brave", "wise", "bold", "keen", "warm", "cool",
    "deep", "bright", "quick", "sure", "clear", "firm", "soft",
    "sharp", "still", "proud", "free", "true",
]
_NOUNS = [
    "falcon", "river", "lynx", "oak", "wave", "peak", "stone", "cloud",
    "fox", "reef", "mesa", "creek", "pine", "hawk", "birch",
    "wolf", "crane", "vale", "dune", "ridge",
]


def make_run_name() -> str:
    """Generate a random memorable adjective-noun name for an LLM config run."""
    return f"{random.choice(_ADJECTIVES)}-{random.choice(_NOUNS)}"
