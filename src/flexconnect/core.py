"""
FlexConnect — Roteador inteligente de LLMs
============================================

Um cliente unico para multiplos provedores de LLM (OpenAI, Google,
Together, OpenRouter) com roteamento por INTENCAO, fallback automatico
em cascata e tracking de custo embutido.

Diferencial vs litellm:
- Roteamento por intencao ("quero barato" / "quero qualidade"), nao so por modelo
- Fallback em cascata transparente (tenta o proximo provedor sozinho)
- Tracking de custo embutido, sem config extra
- Setup de 3 linhas

Uso basico:
    from flexconnect import FlexConnect
    fc = FlexConnect()
    resposta = fc.ask("Explique o que e RAG", priority="cheap")

Licenca: MIT (comercializavel)
"""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from typing import Optional


# ─────────────────────────────────────────
# Catalogo de modelos (custo por 1k tokens em USD)
# ─────────────────────────────────────────

@dataclass
class Modelo:
    id: str
    provedor: str
    modelo_api: str
    custo_1k_in: float
    custo_1k_out: float
    velocidade: int  # 1=lento, 5=rapido
    qualidade: int   # 1=basico, 5=excelente


CATALOGO = [
    # Modelos atuais (2026) — custo por 1k tokens em USD (input, output)
    # Baratos/rapidos
    Modelo("gemini-2.5-flash", "google", "gemini-2.5-flash", 0.00015, 0.0006, 5, 4),
    Modelo("gemini-3-flash", "google", "gemini-3-flash", 0.0003, 0.0012, 5, 4),
    Modelo("gpt-5-nano", "openai", "gpt-5-nano", 0.00005, 0.0004, 5, 3),
    # Qualidade alta
    Modelo("gemini-3-pro", "google", "gemini-3-pro", 0.002, 0.012, 3, 5),
    Modelo("gpt-5.5", "openai", "gpt-5.5", 0.00175, 0.014, 3, 5),
    Modelo("claude-opus-4.8", "openrouter", "anthropic/claude-opus-4.8", 0.005, 0.025, 3, 5),
    # Open source / flat
    Modelo("llama-70b", "together", "meta-llama/Llama-3.3-70B-Instruct-Turbo", 0.00088, 0.00088, 4, 4),
]


# ─────────────────────────────────────────
# Roteador por intencao
# ─────────────────────────────────────────

PRIORIDADES = {
    # prioridade -> funcao de score (maior = melhor para essa intencao)
    "cheap":   lambda m: -(m.custo_1k_in + m.custo_1k_out),
    "fast":    lambda m: m.velocidade,
    "quality": lambda m: m.qualidade,
    "balanced": lambda m: m.qualidade + m.velocidade - (m.custo_1k_in + m.custo_1k_out) * 100,
}


def rotear(priority: str = "balanced") -> list[Modelo]:
    """Retorna modelos ordenados pela intencao (melhor primeiro)."""
    score = PRIORIDADES.get(priority, PRIORIDADES["balanced"])
    return sorted(CATALOGO, key=score, reverse=True)


# ─────────────────────────────────────────
# Tracking de custo
# ─────────────────────────────────────────

@dataclass
class Uso:
    chamadas: int = 0
    custo_total: float = 0.0
    tokens_total: int = 0
    por_modelo: dict = field(default_factory=dict)

    def registrar(self, modelo_id: str, tokens: int, custo: float):
        self.chamadas += 1
        self.custo_total += custo
        self.tokens_total += tokens
        if modelo_id not in self.por_modelo:
            self.por_modelo[modelo_id] = {"chamadas": 0, "custo": 0.0}
        self.por_modelo[modelo_id]["chamadas"] += 1
        self.por_modelo[modelo_id]["custo"] += custo


# ─────────────────────────────────────────
# Resultado de uma chamada
# ─────────────────────────────────────────

@dataclass
class Resposta:
    texto: str
    modelo_usado: str
    custo_estimado: float
    duracao_s: float
    tentativas: list = field(default_factory=list)
    sucesso: bool = True


# ─────────────────────────────────────────
# Cliente principal
# ─────────────────────────────────────────

class FlexConnect:
    """
    Cliente unico para multiplos LLMs com roteamento inteligente.

    Exemplo:
        fc = FlexConnect()
        r = fc.ask("Resuma este texto: ...", priority="cheap")
        print(r.texto, r.modelo_usado, r.custo_estimado)
    """

    def __init__(self, chaves: Optional[dict] = None):
        # Chaves: usa as fornecidas, senao pega do ambiente
        self.chaves = chaves or {
            "google": os.environ.get("GOOGLE_API_KEY", ""),
            "openai": os.environ.get("OPENAI_API_KEY", ""),
            "together": os.environ.get("TOGETHER_API_KEY", ""),
            "openrouter": os.environ.get("OPENROUTER_API_KEY", ""),
        }
        self.uso = Uso()

    def ask(self, prompt: str, priority: str = "balanced",
            max_tokens: int = 1000) -> Resposta:
        """
        Faz uma pergunta, escolhe o melhor modelo pela prioridade,
        com fallback automatico em cascata se algum falhar.
        """
        inicio = time.time()
        candidatos = rotear(priority)
        tentativas = []

        for modelo in candidatos:
            chave = self.chaves.get(modelo.provedor, "")
            if not chave:
                tentativas.append(f"{modelo.id}: sem chave")
                continue

            texto = self._chamar(modelo, prompt, max_tokens, chave)
            if texto:
                tokens_est = len(prompt.split()) + len(texto.split())
                custo = (tokens_est / 1000) * (modelo.custo_1k_in + modelo.custo_1k_out) / 2
                self.uso.registrar(modelo.id, tokens_est, custo)
                return Resposta(
                    texto=texto,
                    modelo_usado=modelo.id,
                    custo_estimado=round(custo, 6),
                    duracao_s=round(time.time() - inicio, 2),
                    tentativas=tentativas,
                    sucesso=True,
                )
            tentativas.append(f"{modelo.id}: falhou")

        return Resposta(
            texto="", modelo_usado="nenhum", custo_estimado=0.0,
            duracao_s=round(time.time() - inicio, 2),
            tentativas=tentativas, sucesso=False,
        )

    def stats(self) -> dict:
        """Retorna estatisticas de uso e custo."""
        return {
            "chamadas": self.uso.chamadas,
            "custo_total_usd": round(self.uso.custo_total, 6),
            "tokens_total": self.uso.tokens_total,
            "por_modelo": self.uso.por_modelo,
        }

    # ─── Chamadas por provedor ───

    def _chamar(self, modelo: Modelo, prompt: str, max_tokens: int, chave: str) -> str:
        try:
            import httpx
        except ImportError:
            return ""

        try:
            if modelo.provedor == "google":
                r = httpx.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/{modelo.modelo_api}:generateContent?key={chave}",
                    headers={"Content-Type": "application/json"},
                    json={"contents": [{"parts": [{"text": prompt}]}],
                          "generationConfig": {"maxOutputTokens": max_tokens}},
                    timeout=40,
                )
                if r.status_code == 200:
                    return r.json()["candidates"][0]["content"]["parts"][0]["text"]

            elif modelo.provedor in ("openai", "together", "openrouter"):
                urls = {
                    "openai": "https://api.openai.com/v1/chat/completions",
                    "together": "https://api.together.xyz/v1/chat/completions",
                    "openrouter": "https://openrouter.ai/api/v1/chat/completions",
                }
                r = httpx.post(
                    urls[modelo.provedor],
                    headers={"Authorization": f"Bearer {chave}", "Content-Type": "application/json"},
                    json={"model": modelo.modelo_api, "max_tokens": max_tokens,
                          "messages": [{"role": "user", "content": prompt}]},
                    timeout=40,
                )
                if r.status_code == 200:
                    return r.json()["choices"][0]["message"]["content"]
        except Exception:
            pass
        return ""


if __name__ == "__main__":
    fc = FlexConnect()
    print("=== Teste FlexConnect ===\n")

    for prio in ["cheap", "quality", "fast"]:
        print(f"Prioridade: {prio}")
        ordem = rotear(prio)
        print(f"  Ordem de escolha: {[m.id for m in ordem]}")

    print("\n=== Chamada real (priority=cheap) ===")
    r = fc.ask("Diga ola em uma palavra", priority="cheap", max_tokens=50)
    print(f"Modelo usado: {r.modelo_usado}")
    print(f"Resposta: {r.texto[:80]}")
    print(f"Custo: ${r.custo_estimado} | Duracao: {r.duracao_s}s")
    print(f"Tentativas: {r.tentativas}")

    print("\n=== Stats ===")
    print(json.dumps(fc.stats(), indent=2))
