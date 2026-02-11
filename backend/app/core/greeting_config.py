"""
Dynamic greeting configuration - shared between admin API and orchestrator.
"""

# Default greeting
_current_greeting = "Hello, this is VocalQ from Tekisho. Which language do you prefer?"


def get_greeting() -> str:
    """Get the current greeting message."""
    return _current_greeting


def set_greeting(greeting: str) -> None:
    """Set a new greeting message."""
    global _current_greeting
    _current_greeting = greeting
