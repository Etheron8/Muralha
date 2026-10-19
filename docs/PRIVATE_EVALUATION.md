# Instalação privada do avaliador

**Nunca adicione os arquivos abaixo ao repositório público.** A pasta local padrão `private_oracles/` é ignorada pelo Git. Em deployment, monte-a de armazenamento privado acessível somente ao avaliador.

## Gabarito privado

Crie `<MURALHA_GOLDEN_DIR>/<challenge_id>.json`. Exemplo de formato sem resposta real:

```json
{
  "cwe": "CWE-NNN",
  "severity": "high",
  "file": "src/example.py",
  "line_range": [1, 4],
  "root_cause_phrases": ["frase controlada para rubrica"],
  "fix_phrases": ["descrição de correção esperada"]
}
```

A rubrica serve para pontuar o diagnóstico, não para provar que a correção funciona. Correspondência por palavras-chave pode produzir falsos positivos e deve ser calibrada com respostas de referência variadas.

## Casos funcionais privados

Quando `MURALHA_ENABLE_SANDBOX=true`, o serviço procura:

```
<MURALHA_PRIVATE_TESTS_DIR>/<challenge_id>/cases.json
```

Formato atual suportado:

```json
{
  "function": "can_access_document",
  "cases": [
    {
      "name": "deny_non_owner",
      "kwargs": {
        "requester_id": 99,
        "role": "user",
        "document": {"owner_id": 7}
      },
      "expected": false
    }
  ]
}
```

O avaliador mantém o manifesto e os valores esperados fora do contêiner. Para cada caso, inicia um contêiner descartável e envia **somente os argumentos daquele caso**. O código candidato não recebe o manifesto completo, os resultados esperados ou uma pasta com os testes. O worker atualmente aceita a função de fixture `can_access_document`; novos tipos de desafio precisam de um adapter dedicado revisado antes de serem publicados.

Construa a imagem previamente com:

```powershell
docker build -t muralha-test-runner:py312 -f sandbox/Dockerfile .
```

Ou execute `scripts/build_test_runner.ps1` no PowerShell. O processo que invoca Docker deve rodar num host/worker dedicado, sem credenciais sensíveis e sem acesso a outros serviços. Não exponha o socket Docker à internet.

## Regras antes de publicar

- O ID deve coincidir exatamente com o catálogo.
- `file` e `line_range` devem corresponder à fixture revisada.
- Os casos válidos precisam continuar válidos depois da correção; casos proibidos devem ser negados.
- Adicione casos de limite e de tipos inesperados.
- Não use segredos de produção nem faça chamadas externas.
- Execute cada caso isoladamente e devolva ao cliente apenas a pontuação/feedback permitido para aquele benchmark.

## Produção

Nunca publique gabaritos em rotas HTTP, artifacts públicos ou logs de CI. O fluxo de Pull Request usa casos de contrato públicos da versão-base; mantenha os casos privados da API fora do repositório público. Para código hostil de terceiros, prefira worker separado em VM descartável. Docker restringe os recursos, mas não garante isolamento absoluto contra vulnerabilidades de kernel/runtime.
