"""
Exemplo 1: Uso basico — uma pergunta, melhor modelo automatico.
"""
from flexconnect import FlexConnect

fc = FlexConnect()

# Prioridade "cheap" = menor custo primeiro, com fallback automatico
resposta = fc.ask("Explique o que e um LLM em uma frase", priority="cheap")

print(f"Resposta: {resposta.texto}")
print(f"Modelo usado: {resposta.modelo_usado}")
print(f"Custo: ${resposta.custo_estimado}")
print(f"Tempo: {resposta.duracao_s}s")
