# Plano de Implementação: disable-text-selection

## Visão Geral

Implementar proteção de seleção e cópia de texto nas telas de avaliação (`QUESTIONS` e `REVIEW`) via CSS e event listeners encapsulados em um hook React, sem alterações no backend.

## Tasks

- [x] 1. Adicionar classe CSS `no-select` ao `styles.css`
  - Inserir ao final de `frontend/src/styles.css` o bloco `.no-select` com `user-select: none` e a exceção para `input` e `button` com `user-select: auto`
  - Incluir `-webkit-user-select` como fallback para compatibilidade com Safari/WebKit
  - _Requirements: 1.1, 1.2, 1.3, 1.4_

- [x] 2. Criar o hook `useTextSelectionGuard`
  - [x] 2.1 Implementar o hook em `frontend/src/hooks/useTextSelectionGuard.js`
    - Definir a constante interna `PROTECTED_STAGES = new Set([STAGES.QUESTIONS, STAGES.REVIEW])`
    - Usar `useEffect` para adicionar/remover a classe `no-select` no `containerRef.current` com base no `stage`
    - Registrar listener `keydown` no `document` que bloqueia `Ctrl/Cmd + C/A/X` nos estágios protegidos
    - Registrar listener `contextmenu` no `document` que bloqueia o menu em elementos não-interativos nos estágios protegidos
    - Retornar cleanup completo dos listeners no return do `useEffect`
    - _Requirements: 1.1, 1.2, 2.1, 2.2, 2.3, 2.4, 3.1, 3.2, 4.4_

  - [ ]* 2.2 Escrever testes de exemplo para o hook
    - Verificar que a classe `no-select` é adicionada quando `stage=QUESTIONS`
    - Verificar que a classe `no-select` é adicionada quando `stage=REVIEW`
    - Verificar que a classe `no-select` é removida quando `stage=AUTH`, `INTRO` ou `COMPLETED`
    - Verificar que os event listeners são removidos ao desmontar
    - _Requirements: 1.1, 1.2, 4.1, 4.2, 4.3_

  - [ ]* 2.3 Escrever teste de propriedade — Property 1: proteção ativa ↔ estágio protegido
    - **Property 1: Proteção ativa se e somente se o estágio for protegido**
    - Usar `fc.constantFrom(...Object.values(STAGES))` para gerar qualquer estágio
    - Verificar que `no-select` está presente ↔ `stage ∈ {QUESTIONS, REVIEW}`
    - Tag: `// Feature: disable-text-selection, Property 1`
    - **Validates: Requirements 1.1, 1.2, 4.1, 4.2, 4.3, 4.4**

  - [ ]* 2.4 Escrever teste de propriedade — Property 2: atalhos de cópia bloqueados
    - **Property 2: Atalhos de cópia são bloqueados nos estágios protegidos**
    - Usar `fc.constantFrom(STAGES.QUESTIONS, STAGES.REVIEW)`, `fc.constantFrom('c','a','x')` e `fc.boolean()` para `ctrlKey`/`metaKey`
    - Verificar que `preventDefault()` é chamado quando `(ctrlKey || metaKey) && key ∈ {c,a,x}`
    - Tag: `// Feature: disable-text-selection, Property 2`
    - **Validates: Requirements 2.1, 2.2, 2.3, 2.4**

  - [ ]* 2.5 Escrever teste de propriedade — Property 3: teclas não protegidas não são interceptadas
    - **Property 3: Teclas não protegidas não são interceptadas**
    - Usar `fc.string({ minLength: 1, maxLength: 1 }).filter(k => !['c','a','x'].includes(k.toLowerCase()))`
    - Verificar que `preventDefault()` não é chamado para teclas fora do conjunto protegido
    - Tag: `// Feature: disable-text-selection, Property 3`
    - **Validates: Requirements 2.5**

  - [ ]* 2.6 Escrever teste de propriedade — Property 4: contextmenu em interativos vs. não-interativos
    - **Property 4: Menu de contexto bloqueado em não-interativos, permitido em interativos**
    - Usar `fc.constantFrom(STAGES.QUESTIONS, STAGES.REVIEW)` e `fc.boolean()` para `isInteractive`
    - Verificar que `preventDefault()` é chamado ↔ elemento não é `input` nem `button`
    - Tag: `// Feature: disable-text-selection, Property 4`
    - **Validates: Requirements 3.1, 3.2, 3.3**

- [ ] 3. Checkpoint — Garantir que todos os testes passam
  - Garantir que todos os testes passam; perguntar ao usuário se houver dúvidas.

- [x] 4. Integrar o hook em `App.jsx`
  - [x] 4.1 Adicionar `useRef` e `useTextSelectionGuard` em `App.jsx`
    - Importar `useRef` do React e `useTextSelectionGuard` do hook criado
    - Criar `const containerRef = useRef(null)` dentro do componente `App`
    - Chamar `useTextSelectionGuard(flow.stage, containerRef)` logo após `useAssessmentFlow()`
    - Adicionar `ref={containerRef}` ao elemento `<main className="app-shell">` em todos os retornos do componente
    - _Requirements: 1.1, 1.2, 2.1, 2.2, 2.3, 2.4, 3.1, 3.2, 4.1, 4.2, 4.3, 4.4_

  - [ ]* 4.2 Escrever teste de integração para `App.jsx`
    - Verificar com React Testing Library que a classe `no-select` está presente no `<main>` durante o estágio `QUESTIONS`
    - Verificar que a classe não está presente durante o estágio `AUTH`
    - _Requirements: 1.1, 4.1_

  - [ ]* 4.3 Escrever teste de propriedade — Property 5: controles interativos preservam `user-select`
    - **Property 5: Controles interativos preservam user-select**
    - Verificar que `input` e `button` descendentes de `.no-select` têm `user-select` computado como `auto`
    - Tag: `// Feature: disable-text-selection, Property 5`
    - **Validates: Requirements 1.3**

- [ ] 5. Checkpoint final — Garantir que todos os testes passam
  - Garantir que todos os testes passam; perguntar ao usuário se houver dúvidas.

## Notas

- Tasks marcadas com `*` são opcionais e podem ser puladas para um MVP mais rápido
- Cada task referencia requisitos específicos para rastreabilidade
- Os testes de propriedade usam `fast-check` com `numRuns: 100`
- Não há mudanças no backend
