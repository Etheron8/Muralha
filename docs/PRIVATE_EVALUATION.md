# Instalação privada do avaliador

**Nunca adicione os arquivos abaixo ao repositório público.** A pasta local padrão `private_oracles/` é ignorada pelo Git. Em deployment, monte-a de armazenamento/secret files acessível apenas ao serviço avaliador.

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

Os campos descrevem uma rubrica de correspondência determinística. Use frases variadas e teste falsos positivos/negativos antes de disponibilizar uma avaliação. A pontuação por palavras-chave não é um juiz semântico perfeito e deve ser complementada por testes e revisão periódica.

## Testes funcionais privados

Quando `MURALHA_ENABLE_SANDBOX=true`, o serviço procura os testes em:

```
<MURALHA_PRIVATE_TESTS_DIR>/<challenge_id>/tests/
```

Os testes rodam dentro do contêiner de teste e precisam validar os requisitos observáveis da função corrigida. Use nomes e casos de teste não previsíveis, mas não dependa de segredos de produção. O runner atual usa pytest e a imagem de Python configurada em `MURALHA_DOCKER_IMAGE`.

Antes de instalar um gabarito, valide que:
- o ID coincide exatamente com o desafio do catálogo;
- `file` e `line_range` correspondem à fixture revisada;
- a rubrica dá pontos a um diagnóstico preciso, não só a uma palavra específica;
- casos válidos continuam válidos após a correção;
- casos proibidos são rejeitados;
- os testes não fazem chamadas de rede ou acessam serviços externos.

## Produção

Use uma pasta montada privada ou secret files do provedor. Nunca publique os gabaritos via uma rota HTTP, artifact público ou log de CI. Para um benchmark realmente robusto, mantenha os workers que executam código separados do servidor que guarda gabaritos e resultados.
