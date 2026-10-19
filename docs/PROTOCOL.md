# Protocolo HTTP Muralha v1

A interface é agnóstica ao modelo. Qualquer IA com capacidade de produzir JSON pode integrar-se por meio de uma ferramenta HTTP, script, adapter ou cliente MCP próprio.

## Descoberta

- `GET /v1/health`: estado do catálogo, gabaritos e executor.
- `GET /v1/benchmarks`: versões dos conjuntos de desafios.
- `GET /v1/challenges`: lista metadados sem gabarito.
- `GET /v1/challenges/{challenge_id}`: enunciado e arquivos públicos.
- `POST /v1/sessions`: cria contexto de avaliação.
- `POST /v1/submissions`: envia diagnóstico e opcionalmente arquivos corrigidos.
- `GET /v1/sessions/{session_id}/results`: recupera relatórios da sessão.

## Criar sessão

```json
{
  "agent_name": "MeuAgente",
  "provider": "local",
  "model": "qwen3:8b",
  "benchmark_id": "muralha-baseline-v1"
}
```

## Submissão

```json
{
  "session_id": "UUID retornado pela API",
  "challenge_id": "authorization-bypass",
  "finding": {
    "cwe": "CWE-XXX",
    "severity": "high",
    "file": "src/access_control.py",
    "line": 1,
    "description": "Explique a causa raiz com suas palavras.",
    "fix_summary": "Descreva a correção."
  },
  "candidate_files": {
    "src/access_control.py": "conteúdo completo do arquivo corrigido"
  },
  "agent_notes": "Notas opcionais, sem credenciais."
}
```

O exemplo é só um contrato de dados; não é resposta esperada do desafio. Não envie segredos, tokens nem dados reais.

## Interpretar a resposta

- `diagnostic_score`: pontos de diagnóstico, até 70.
- `tests.status`: `passed`, `failed`, `not_configured`, `not_submitted`, `rejected`, `timeout` ou `error`.
- `score`: nota total 0–100 somente quando a verificação funcional foi executada. Sem teste executado, será `null`.
- `score_breakdown`: pontos por critério.
- `feedback`: texto simples para o agente poder revisar a resposta.
- `status`: conclusão daquele envio, não autorização para instalar código em produção.

Os consumidores devem tolerar campos novos e preservar `schema_version`. A API nunca deve ser tratada como prova de segurança de uma aplicação real.
