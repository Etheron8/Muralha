# Arquitetura

## Componentes

1. **Catálogo público** — metadados, enunciados e fixtures intencionalmente defeituosas em `catalog/` e `challenges/`.
2. **API FastAPI** — dá acesso uniforme a agentes locais/remotos, cria sessões e aceita submissões.
3. **Avaliador privado** — gabaritos por desafio carregados de uma pasta que não faz parte do Git.
4. **Pontuação determinística** — critérios explícitos, resultado JSON e feedback por categoria.
5. **Executor de teste opcional** — executa candidate files usando Docker com limites, sem rede e sem privilégios.
6. **Persistência** — SQLite guarda sessões e relatórios; para uso público de maior escala, migrar para banco gerenciado.
7. **CI do projeto** — verifica o código da central. Os testes meta não tentam corrigir automaticamente as fixtures deliberadamente vulneráveis.

## Separação entre desafio e resposta

O repositório público contém somente o material entregue ao agente. Os arquivos `<challenge_id>.json` e `<challenge_id>/tests/` pertencem à instalação privada da central e não podem ser colocados no repositório ou servidos pela rota de desafio.

O endpoint de submissão devolve um erro explícito se o gabarito não existir. Isso impede que um deployment recém-criado invente pontuação.

## Fluxo de avaliação

- Diagnóstico: até 70 pontos, calculados a partir de gabarito privado.
- Teste funcional: até 30 pontos extras quando os testes ocultos realmente executam e passam. Testes falhando recebem zero pontos funcionais.
- Nota final: nula quando não há validação funcional; nenhum score incompleto deve ser confundido com 100 pontos.
- Resultados salvos por sessão para que o agente possa consultar o próprio histórico.

## Segurança operacional

O envio de código não confiável é uma fronteira de segurança. O executor está desligado por padrão. Antes de ligá-lo num serviço público:

- execute-o numa VM/worker descartável sem segredos, sem socket Docker exposto à API web e sem credenciais de nuvem;
- não monte pastas do host além da fixture candidata e da pasta exclusiva de testes;
- mantenha rede desabilitada, limites de CPU/memória/processos, filesystem read-only e usuário não privilegiado;
- aplique rate limiting também no gateway e limite tamanho de request;
- mantenha logs sem código completo submetido, informações sensíveis ou conteúdo de testes privados;
- trate qualquer avaliação automatizada como sinal de benchmark, não como certificação de segurança.

A contenção Docker no mesmo host não garante isolamento absoluto contra escapes de kernel/runtime. Para executar código hostil de terceiros, a recomendação é worker separado em VM descartável e, quando disponível, sandbox mais forte.
