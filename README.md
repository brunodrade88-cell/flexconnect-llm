# FlexConnect 🔌

[![PyPI](https://img.shields.io/pypi/v/flexconnect-llm)](https://pypi.org/project/flexconnect-llm/)

## Instalação

```bash
pip install flexconnect-llm
```


**Um cliente, todos os LLMs.** Roteamento inteligente por intenção, fallback automático e tracking de custo embutido.

## Por que FlexConnect?

Você usa OpenAI, Google, Together... cada um com seu SDK, suas chaves, seu jeito. Quando um cai, sua app cai junto. Quando o custo sobe, você descobre tarde demais.

FlexConnect resolve isso com **3 linhas**:

```python
from flexconnect import FlexConnect

fc = FlexConnect()
resposta = fc.ask("Explique RAG em uma frase", priority="cheap")
print(resposta.texto)
```

## Diferenciais

| Recurso | FlexConnect | Wrappers comuns |
|---------|-------------|-----------------|
| Roteamento por intenção (`cheap`/`quality`/`fast`) | ✅ | ❌ (só por modelo) |
| Fallback automático em cascata | ✅ | Manual |
| Tracking de custo embutido | ✅ | Plugin extra |
| Setup | 3 linhas | Config por provedor |

## Prioridades

```python
fc.ask("...", priority="cheap")    # menor custo primeiro
fc.ask("...", priority="quality")  # melhor modelo primeiro
fc.ask("...", priority="fast")     # mais rápido primeiro
fc.ask("...", priority="balanced") # equilíbrio (padrão)
```

## Tracking de custo

```python
fc.ask("...")
fc.ask("...")
print(fc.stats())
# {'chamadas': 2, 'custo_total_usd': 0.0001, 'por_modelo': {...}}
```

## Configuração

Por padrão lê as chaves do ambiente:
- `GOOGLE_API_KEY`
- `OPENAI_API_KEY`
- `TOGETHER_API_KEY`
- `OPENROUTER_API_KEY`

Ou passe diretamente:

```python
fc = FlexConnect(chaves={"openai": "sk-..."})
```

## Instalação

```bash
pip install httpx
# copie flexconnect.py para seu projeto
```

## Licença

MIT — uso livre, inclusive comercial.

---

## FlexConnect Pro

Recursos avançados para produção (em `flexconnect_pro.py`):

```python
from flexconnect_pro import FlexConnectPro

fc = FlexConnectPro(cache_ttl=3600, rate_limit_rpm=60)

# Cache automático — prompts repetidos não custam nada
r = fc.ask("pergunta comum")   # vai à API
r = fc.ask("pergunta comum")   # vem do cache (custo zero)

# Streaming — resposta em tempo real
for chunk in fc.ask_stream("escreva um texto longo"):
    print(chunk, end="", flush=True)
```

| Recurso | Free | Pro |
|---------|:----:|:---:|
| Roteamento por intenção | ✅ | ✅ |
| Fallback em cascata | ✅ | ✅ |
| Tracking de custo | ✅ | ✅ |
| Cache de respostas | ❌ | ✅ |
| Rate limiting | ❌ | ✅ |
| Streaming | ❌ | ✅ |

O cache sozinho paga o Pro: prompts repetidos passam a custar **zero**.
