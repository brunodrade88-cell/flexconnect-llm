"""
Exemplo 3: FlexConnect Pro — cache (custo zero em repeticoes) + streaming.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from flexconnect_pro import FlexConnectPro

fc = FlexConnectPro(cache_ttl=3600, rate_limit_rpm=60)

# Cache: a 2a chamada identica nao custa nada
pergunta = "Qual a capital da Franca?"
r1 = fc.ask(pergunta, priority="cheap")
r2 = fc.ask(pergunta, priority="cheap")  # vem do cache
print(f"1a chamada: {r1.modelo_usado} (${r1.custo_estimado})")
print(f"2a chamada: cache hit! (cache_hits={fc.cache_hits}, custo zero)")

# Streaming: resposta em tempo real
print("\nStreaming: ", end="")
for chunk in fc.ask_stream("Liste 3 linguagens de programacao", priority="quality"):
    print(chunk, end="", flush=True)
print()
