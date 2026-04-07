"""
adk_agent/neuroflow_app/__init__.py
------------------------------------
ADK discovers the agent via this package.
`root_agent` must be importable from this namespace.
"""

from .agent import root_agent  # noqa: F401 — re-exported for ADK discovery

__all__ = ["root_agent"]
