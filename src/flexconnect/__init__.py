"""
FlexConnect — roteador inteligente de LLMs.

Uso:
    from flexconnect import FlexConnect
    fc = FlexConnect()
    r = fc.ask("Explique RAG", priority="cheap")

    from flexconnect import FlexConnectPro
    fc = FlexConnectPro(cache_ttl=3600)
"""
from .core import FlexConnect, Resposta, Modelo, rotear, CATALOGO
from .pro import FlexConnectPro, CacheRespostas, RateLimiter
from .adapter import contratar

__version__ = "0.1.0"
__all__ = [
    "FlexConnect", "FlexConnectPro", "Resposta", "Modelo",
    "rotear", "CATALOGO", "CacheRespostas", "RateLimiter", "contratar",
]
