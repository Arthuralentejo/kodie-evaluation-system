# Bugfix Requirements Document

## Introduction

Após concluir uma avaliação do tipo "Geral", a tela de introdução (IntroScreen) não bloqueia o nível correspondente no seletor de nível nem exibe o histórico de avaliações concluídas corretamente. O resultado é que o estudante vê o nível "Geral" como disponível para iniciar novamente, e a lista de avaliações concluídas aparece vazia — mesmo quando há avaliações concluídas no histórico.

A causa raiz é um mismatch de campo: a API retorna cada avaliação concluída com o campo `assessment_type`, mas o frontend lê `level` (campo inexistente), resultando em um conjunto de níveis bloqueados sempre vazio.

## Bug Analysis

### Current Behavior (Defect)

1.1 WHEN o estudante conclui uma avaliação do tipo "Geral" e retorna à tela de introdução THEN o sistema exibe o nível "Geral" como disponível (não bloqueado) no seletor de nível

1.2 WHEN a API retorna a lista de avaliações concluídas com o campo `assessment_type` THEN o sistema lê o campo `level` (inexistente) e constrói um conjunto de níveis bloqueados vazio

1.3 WHEN o estudante possui avaliações concluídas no histórico THEN o sistema exibe a lista de avaliações concluídas vazia na IntroScreen

### Expected Behavior (Correct)

2.1 WHEN o estudante conclui uma avaliação de qualquer nível e retorna à tela de introdução THEN o sistema SHALL exibir o nível correspondente como bloqueado (disabled) no seletor de nível

2.2 WHEN a API retorna a lista de avaliações concluídas com o campo `assessment_type` THEN o sistema SHALL ler o campo `assessment_type` para identificar os níveis bloqueados

2.3 WHEN o estudante possui avaliações concluídas no histórico THEN o sistema SHALL exibir corretamente a lista de avaliações concluídas com nível e data na IntroScreen

### Unchanged Behavior (Regression Prevention)

3.1 WHEN o estudante não possui nenhuma avaliação concluída THEN o sistema SHALL CONTINUE TO exibir todos os níveis disponíveis e habilitados no seletor

3.2 WHEN o estudante possui uma avaliação em andamento (DRAFT) THEN o sistema SHALL CONTINUE TO redirecionar diretamente para a tela de questões sem exibir o seletor de nível

3.3 WHEN o estudante seleciona um nível não concluído e clica em "Iniciar avaliação" THEN o sistema SHALL CONTINUE TO iniciar a avaliação normalmente

3.4 WHEN o estudante tenta iniciar uma avaliação em um nível já concluído via API direta THEN o sistema SHALL CONTINUE TO retornar erro 409 com código `LEVEL_ALREADY_COMPLETED`

3.5 WHEN o modal de confirmação de substituição é exibido THEN o sistema SHALL CONTINUE TO arquivar a avaliação anterior e criar uma nova ao confirmar
