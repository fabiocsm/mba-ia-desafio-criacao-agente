"""Seleção do agente na retomada de uma confirmação já autorizada.

No ADK 2.2.0, _find_agent_to_run escolhe o agente antes da mensagem nova.
Se o último evento for do principal, a tool do especialista não reexecuta.
Fora da retomada canônica, o comportamento continua o do Runner.
"""

from __future__ import annotations

from google.adk.agents.base_agent import BaseAgent
from google.adk.runners import Runner
from google.adk.sessions.session import Session
from typing_extensions import override

from aurora.runtime.confirmacoes import retomada_atual


class AuroraRunner(Runner):
    @override
    def _find_agent_to_run(self, session: Session, root_agent: BaseAgent) -> BaseAgent:
        atual = retomada_atual()
        if atual is None or atual.session_id != session.id:
            return super()._find_agent_to_run(session, root_agent)
        agente = root_agent.find_agent(atual.author)
        if agente is None:
            return super()._find_agent_to_run(session, root_agent)
        return agente
