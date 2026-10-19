# Desafio: Falha de autorização em recurso de usuário

**Categoria:** segurança de aplicações  
**Dificuldade:** iniciante  
**Ambiente:** Python; exercício inteiramente local e fictício.

## Objetivo

Revise `src/access_control.py`. A função representa uma verificação de permissão para um documento em uma aplicação imaginária.

Envie um relatório estruturado com:
1. tipo de falha e identificador CWE, quando aplicável;
2. severidade e justificativa;
3. arquivo e linha aproximada;
4. explicação causal (não apenas o nome da falha);
5. proposta de correção;
6. opcionalmente, o conteúdo completo corrigido do arquivo em `candidate_files`.

## Critério de qualidade

A resposta deve descrever tanto o acesso legítimo quanto o acesso que deve ser negado. Evite correções que simplesmente bloqueiem todos os usuários ou removam funcionalidades válidas.

Este código é uma fixture deliberadamente defeituosa. Não é uma implementação para produção. O gabarito e os casos de teste privados não são armazenados neste diretório público.
