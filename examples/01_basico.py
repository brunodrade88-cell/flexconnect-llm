"""
Exemplo 1: Uso basico — uma pergunta, melhor modelo automatico.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from flexconnect import FlexConnect

fc = FlexConnect()

# Prioridade "cheap" = menor custo primeiro, com fallback automatico
resposta = fc.ask("Explique o que e um LLM em uma frase", priority="cheap")

print(f"Resposta: {resposta.texto}")
print(f"Modelo usado: {resposta.modelo_usado}")
print(f"Custo: ${resposta.custo_estimado}")
print(f"Tempo: {resposta.duracao_s}s")
