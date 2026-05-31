"""
FlexConnect Pro — recursos avancados
=====================================

Estende o FlexConnect com recursos que devs em producao precisam:
- Cache de respostas (economiza custo em prompts repetidos)
- Rate limiting (evita estourar quota e custo)
- Streaming de respostas (UX em tempo real)

Estes sao os recursos "pro" — a base (flexconnect.py) e MIT/gratis,
estes recursos sao o diferencial comercial.

Uso:
    from flexconnect_pro import FlexConnectPro
    fc = FlexConnectPro(cache_ttl=3600, rate_limit_rpm=60)
    r = fc.ask("...", priority="cheap")        # usa cache automatico
    for chunk in fc.ask_stream("..."):         # streaming
        print(chunk, end="")
"""
from __future__ import annotations

import hashlib
import time
from collections import deque
from dataclasses import dataclass

from .core import FlexConnect, Resposta, rotear


# ─────────────────────────────────────────
# Cache de respostas
# ─────────────────────────────────────────

class CacheRespostas:
    """Cache simples em memoria com TTL. Economiza custo em prompts repetidos."""

    def __init__(self, ttl: int = 3600, max_entradas: int = 1000):
        self.ttl = ttl
        self.max_entradas = max_entradas
        self._cache: dict = {}

    def _chave(self, prompt: str, priority: str) -> str:
        return hashlib.sha256(f"{priority}::{prompt}".encode()).hexdigest()[:24]

    def get(self, prompt: str, priority: str):
        chave = self._chave(prompt, priority)
        item = self._cache.get(chave)
        if item is None:
            return None
        valor, expira = item
        if time.time() > expira:
            del self._cache[chave]
            return None
        return valor

    def set(self, prompt: str, priority: str, resposta):
        if len(self._cache) >= self.max_entradas:
            # Remove a entrada mais antiga
            mais_antiga = min(self._cache.items(), key=lambda x: x[1][1])
            del self._cache[mais_antiga[0]]
        chave = self._chave(prompt, priority)
        self._cache[chave] = (resposta, time.time() + self.ttl)

    def stats(self) -> dict:
        return {"entradas": len(self._cache), "ttl": self.ttl}


# ─────────────────────────────────────────
# Rate limiter
# ─────────────────────────────────────────

class RateLimiter:
    """Limita requisicoes por minuto. Evita estourar quota/custo."""

    def __init__(self, rpm: int = 60):
        self.rpm = rpm
        self._timestamps: deque = deque()

    def aguardar(self):
        """Bloqueia ate poder fazer a proxima requisicao."""
        agora = time.time()
        # Remove timestamps com mais de 60s
        while self._timestamps and agora - self._timestamps[0] > 60:
            self._timestamps.popleft()

        if len(self._timestamps) >= self.rpm:
            espera = 60 - (agora - self._timestamps[0])
            if espera > 0:
                time.sleep(espera)
        self._timestamps.append(time.time())

    def pode_agora(self) -> bool:
        agora = time.time()
        while self._timestamps and agora - self._timestamps[0] > 60:
            self._timestamps.popleft()
        return len(self._timestamps) < self.rpm


# ─────────────────────────────────────────
# FlexConnect Pro
# ─────────────────────────────────────────

class FlexConnectPro(FlexConnect):
    """
    FlexConnect com cache, rate limiting e streaming.

    Exemplo:
        fc = FlexConnectPro(cache_ttl=3600, rate_limit_rpm=60)
        r = fc.ask("pergunta repetida")  # 2a vez vem do cache (custo 0)
        for chunk in fc.ask_stream("conte uma historia"):
            print(chunk, end="", flush=True)
    """

    def __init__(self, chaves=None, cache_ttl: int = 3600, rate_limit_rpm: int = 60):
        super().__init__(chaves)
        self.cache = CacheRespostas(ttl=cache_ttl)
        self.limiter = RateLimiter(rpm=rate_limit_rpm)
        self.cache_hits = 0

    def ask(self, prompt: str, priority: str = "balanced", max_tokens: int = 1000) -> Resposta:
        # 1. Tenta cache
        cached = self.cache.get(prompt, priority)
        if cached is not None:
            self.cache_hits += 1
            return cached

        # 2. Rate limit
        self.limiter.aguardar()

        # 3. Chamada normal
        resposta = super().ask(prompt, priority, max_tokens)

        # 4. Cacheia se deu certo
        if resposta.sucesso:
            self.cache.set(prompt, priority, resposta)

        return resposta

    def ask_stream(self, prompt: str, priority: str = "balanced", max_tokens: int = 1000):
        """
        Streaming de resposta — yield de chunks conforme chegam.
        Atualmente suporta OpenAI/Together/OpenRouter (SSE).
        """
        self.limiter.aguardar()
        candidatos = rotear(priority)

        for modelo in candidatos:
            chave = self.chaves.get(modelo.provedor, "")
            if not chave:
                continue
            if modelo.provedor in ("openai", "together", "openrouter"):
                gerou = yield from self._stream_openai_compat(modelo, prompt, max_tokens, chave)
                if gerou:
                    return
            elif modelo.provedor == "google":
                # Gemini: sem streaming aqui, faz chamada normal e entrega de uma vez
                texto = self._chamar(modelo, prompt, max_tokens, chave)
                if texto:
                    yield texto
                    return

    def _stream_openai_compat(self, modelo, prompt: str, max_tokens: int, chave: str) -> bool:
        """Streaming via SSE para APIs compativeis com OpenAI. Retorna True se gerou algo."""
        try:
            import httpx
            import json as _json
        except ImportError:
            return False

        urls = {
            "openai": "https://api.openai.com/v1/chat/completions",
            "together": "https://api.together.xyz/v1/chat/completions",
            "openrouter": "https://openrouter.ai/api/v1/chat/completions",
        }

        try:
            with httpx.stream(
                "POST", urls[modelo.provedor],
                headers={"Authorization": f"Bearer {chave}", "Content-Type": "application/json"},
                json={"model": modelo.modelo_api, "max_tokens": max_tokens, "stream": True,
                      "messages": [{"role": "user", "content": prompt}]},
                timeout=60,
            ) as r:
                if r.status_code != 200:
                    return False
                gerou = False
                for linha in r.iter_lines():
                    if not linha or not linha.startswith("data: "):
                        continue
                    dados = linha[6:]
                    if dados.strip() == "[DONE]":
                        break
                    try:
                        obj = _json.loads(dados)
                        delta = obj["choices"][0].get("delta", {}).get("content", "")
                        if delta:
                            gerou = True
                            yield delta
                    except Exception:
                        continue
                return gerou
        except Exception:
            return False

    def stats(self) -> dict:
        base = super().stats()
        base["cache_hits"] = self.cache_hits
        base["cache"] = self.cache.stats()
        base["rate_limit_rpm"] = self.limiter.rpm
        return base


if __name__ == "__main__":
    print("=== Teste FlexConnect Pro ===\n")
    fc = FlexConnectPro(cache_ttl=3600, rate_limit_rpm=60)

    print("1. Cache — primeira chamada (vai pra API):")
    r1 = fc.ask("Diga 'teste' em uma palavra", priority="cheap", max_tokens=20)
    print(f"   Modelo: {r1.modelo_usado} | Custo: ${r1.custo_estimado} | {r1.duracao_s}s")

    print("\n2. Cache — MESMA chamada (deve vir do cache, custo 0, instantaneo):")
    r2 = fc.ask("Diga 'teste' em uma palavra", priority="cheap", max_tokens=20)
    print(f"   Modelo: {r2.modelo_usado} | Cache hits: {fc.cache_hits} | {r2.duracao_s}s")

    print("\n3. Streaming — resposta chega em pedacos:")
    print("   ", end="")
    for chunk in fc.ask_stream("Conte ate 5 separado por virgula", priority="quality", max_tokens=50):
        print(chunk, end="", flush=True)
    print()

    print("\n4. Stats:")
    import json
    print(json.dumps(fc.stats(), indent=2))
