"""Official evaluator import shim.

The organizer imports ``starter.agent.Agent``.  The implementation lives in
``shopping_copilot.agent`` so the evaluator always exercises team-owned code.
"""

from shopping_copilot.agent import Agent

__all__ = ["Agent"]
