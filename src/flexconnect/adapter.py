"""
Adapter de compatibilidade — interface estilo 'contratar()'.

Permite usar o FlexConnect como drop-in em sistemas que esperam
uma funcao contratar(tarefa, prompt, ...) -> dict.
"""
from .core import FlexConnect

_PRIORIDADE_MAP = {
    "qualidade": "quality", "quality": "quality",
    "balanceado": "balanced", "balanced": "balanced",
    "rapido": "fast", "fast": "fast",
    "barato": "cheap", "cheap": "cheap", "custo": "cheap",
}

_cliente = None


def contratar(tarefa, prompt, agente_id=None, tipo_tarefa="pergunta",
              prioridade="balanceado", max_tokens=1000, system=""):
    """Interface compativel com mercado_agentes.contratar().

    system: mensagem de sistema opcional (concatenada ao prompt).
    """
    global _cliente
    if _cliente is None:
        _cliente = FlexConnect()
    priority = _PRIORIDADE_MAP.get(prioridade, "balanced")
    prompt_final = f"{system}\n\n{prompt}" if system else prompt
    r = _cliente.ask(prompt_final, priority=priority, max_tokens=max_tokens)
    return {
        "sucesso": r.sucesso,
        "resposta": r.texto,
        "agente": r.modelo_usado,
        "custo_estimado": r.custo_estimado,
        "duracao_s": r.duracao_s,
    }
