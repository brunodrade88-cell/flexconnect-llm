"""
Exemplo 2: Economia de custo — escolha a prioridade por tarefa.

Tarefas simples usam modelo barato; tarefas complexas usam o melhor.
Voce nao paga por qualidade que nao precisa.
"""
from flexconnect import FlexConnect

fc = FlexConnect()

# Tarefa simples -> barato
r1 = fc.ask("Traduza 'hello' para portugues", priority="cheap")
print(f"[CHEAP] {r1.modelo_usado}: {r1.texto.strip()[:50]} (${r1.custo_estimado})")

# Tarefa complexa -> qualidade
r2 = fc.ask("Analise os trade-offs de microservices vs monolito", priority="quality")
print(f"[QUALITY] {r2.modelo_usado}: {r2.texto.strip()[:50]}... (${r2.custo_estimado})")

print(f"\nCusto total da sessao: ${fc.stats()['custo_total_usd']}")
