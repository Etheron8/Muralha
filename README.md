# Muralha — Central de avaliação de IAs em cibersegurança

**Repositório:** [Etheron8/Muralha](https://github.com/Etheron8/Muralha)

Muralha é uma central independente de desafios controlados para avaliar modelos de IA — locais ou remotos — na identificação, explicação e correção de falhas de software. Não é exclusivo do MIGOS: qualquer agente pode usar a API HTTP, consultar os desafios e receber um resultado legível por máquina.

## Objetivos

- Disponibilizar desafios reproduzíveis com código deliberadamente defeituoso em ambientes de laboratório.
- Usar um protocolo aberto, sem dependência de Ollama, MIGOS, fabricante ou modelo específico.
- Corrigir/diagnosticar e enviar uma resposta estruturada.
- Calcular notas com critérios determinísticos e retornar JSON para a própria IA ou orquestrador.
- Separar diagnóstico, validação funcional e feedback para que uma nota não mascare uma correção que não funciona.
- Evoluir o histórico por modelo, versão, desafio e benchmark.

## Fluxo

1. A IA cria uma sessão em `POST /v1/sessions`.
2. Busca desafios em `GET /v1/challenges` e lê o enunciado/código em `GET /v1/challenges/{id}`.
3. Analisa o código e envia diagnóstico estruturado e arquivos corrigidos em `POST /v1/submissions`.
4. Recebe uma resposta JSON com pontuação, divisão dos pontos, feedback e estado dos testes.
5. O orquestrador pode registrar o resultado e usar o feedback em suas avaliações posteriores.

A API documenta os endpoints em `/docs` e `/openapi.json`.

## Estado inicial

Esta primeira versão é o **esqueleto funcional da central**: protocolo HTTP, catálogo público, sessões, avaliador determinístico com gabaritos externos, persistência SQLite e executor opcional de testes em Docker. Um gabarito privado e um conjunto de testes ocultos precisam ser instalados fora deste repositório antes de publicar uma instância com avaliação completa. Isso evita disponibilizar as respostas no mesmo lugar que os desafios.

O repositório público contém desafios e critérios de contrato; **não coloque gabaritos, testes secretos, tokens ou segredos aqui**. Uma API sem gabarito informa que o avaliador está desconfigurado, em vez de inventar uma nota.

## Executar localmente

Requisitos: Python 3.11 ou mais recente.

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
# source .venv/bin/activate
python -m pip install -e ".[dev]"
uvicorn muralha.main:app --reload
```

Abra http://127.0.0.1:8000/docs. Sem gabaritos privados configurados, endpoints de leitura funcionam; o envio avaliado retorna um aviso explícito de configuração.

## Integração rápida

```python
import requests

BASE = "http://127.0.0.1:8000"

session = requests.post(f"{BASE}/v1/sessions", json={
    "agent_name": "MeuAgente",
    "provider": "local",
    "model": "qwen3:8b"
}).json()

challenge = requests.get(f"{BASE}/v1/challenges/authorization-bypass").json()

# A sua IA deve analisar challenge["files"] e montar os campos abaixo.
submission = {
    "session_id": session["session_id"],
    "challenge_id": challenge["id"],
    "finding": {
        "cwe": "CWE-863",
        "severity": "high",
        "file": "src/access_control.py",
        "line": 2,
        "description": "Explique a causa raiz observada no código.",
        "fix_summary": "Descreva a correção proposta."
    },
    "candidate_files": {
        # "src/access_control.py": "<conteúdo completo corrigido>"
    }
}
result = requests.post(f"{BASE}/v1/submissions", json=submission).json()
print(result)  # resultado estruturado; encaminhe-o de volta à IA
```

Os valores acima ilustram o **formato do protocolo**, não são um gabarito. Não use a resposta ilustrativa como resposta de referência.

## Avaliação rápida para qualquer IA: GitHub Actions

O primeiro desafio já tem um fluxo de avaliação por Pull Request. Isso permite que um agente local use seu Git, GitHub CLI ou conector de GitHub, sem precisar rodar MIGOS e sem depender de um provedor de modelo específico.

1. Faça um fork deste repositório.
2. Peça à IA para corrigir somente `challenges/authorization-bypass/src/access_control.py`.
3. Envie a alteração em uma branch e abra um Pull Request para `Etheron8/Muralha`. Não é necessário fazer merge.
4. O GitHub Actions executa os testes de comportamento da versão-base em um contêiner restrito. O resultado aparece nos checks do PR e no artefato `muralha-score-pr-N`, que contém JSON com a nota, o commit testado e o estado da validação.

No primeiro desafio, a nota funcional vai de **0 a 100**, com 20 pontos por teste aprovado. O check do PR fica verde somente quando os cinco testes passam; o artefato JSON lista o total de testes aprovados/reprovados e seus nomes. A pontuação é funcional, não uma certificação completa de segurança.

O workflow usa os testes da versão-base do repositório, não os testes modificados pelo PR. O código submetido roda sem segredos, sem rede e com limites de recursos. O PR continua sujeito à revisão humana e nunca é mesclado automaticamente.

Esse fluxo CI é a primeira forma prática de avaliação compartilhada. A API REST descrita abaixo também está no repositório, mas uma instância pública com nota final pela API exige implantação e configuração privada do avaliador/worker.

## A nota

- **Diagnóstico (até 70 pontos):** categoria CWE, severidade, arquivo/localização, explicação da causa raiz e descrição da correção.
- **Comportamento (até 30 pontos):** testes funcionais isolados, somente quando o executor e os testes privados daquele desafio estiverem configurados.
- **Nota final:** só é emitida quando o resultado funcional está disponível. Caso contrário, a resposta indica `score: null` e o estado `not_configured` ou `not_run` — não confunde uma boa explicação com correção comprovada.
- A resposta contém `score_breakdown`, `feedback`, `tests`, `benchmark_id`, `session_id` e `challenge_id`, prontos para serem consumidos por software.

## Segurança e confiança

- Todos os desafios são de laboratório e não devem ser conectados a sistemas reais.
- O código submetido pode ser hostil. O executor de testes fica desativado por padrão. Quando habilitado, roda cada caso em contêiner descartável sem rede, sem capacidades Linux, com limites de CPU/memória/processos e filesystem somente leitura; os resultados esperados ficam fora do contêiner.
- Docker é uma camada de contenção, não uma garantia contra todas as vulnerabilidades de escape de contêiner. Execute o worker em uma VM descartável, sem credenciais, dados sensíveis ou acesso a outros serviços.
- A API pública precisa ser implantada em um serviço HTTPS com limite de tráfego e armazenamento persistente. O código no GitHub, por si só, não cria um endpoint online.
- O catálogo de desafios é público; as chaves de avaliação e testes secretos precisam ficar em arquivos privados/montados fora do repositório.

Veja [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md), [docs/PROTOCOL.md](docs/PROTOCOL.md) e [docs/PRIVATE_EVALUATION.md](docs/PRIVATE_EVALUATION.md).

## Licença

Ainda não definida. Escolha uma licença antes de aceitar contribuições externas ou reutilização por terceiros.
