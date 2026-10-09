from toolset_registry.registration import Registration

from agent_tools.tools import AgentTools

_registration = Registration([AgentTools])


def register() -> bool:
    return _registration.register()
