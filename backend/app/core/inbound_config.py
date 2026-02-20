"""
Inbound call configuration management.
Manages whether inbound calls are enabled or disabled.
"""

# In-memory storage for inbound status
# TODO: Consider persisting to database or Redis for production
_inbound_enabled = False

def get_inbound_status() -> bool:
    """Get the current inbound call status."""
    return _inbound_enabled

def set_inbound_status(enabled: bool) -> None:
    """Set the inbound call status."""
    global _inbound_enabled
    _inbound_enabled = enabled
