# Documento de Requisitos

## Introdução

Esta funcionalidade impede que estudantes selecionem ou copiem conteúdo textual durante a realização de uma avaliação na plataforma Kodie. O objetivo é reduzir o risco de cópia de conteúdo das questões e alternativas, contribuindo para a integridade do processo avaliativo.

A proteção é aplicada via CSS (`user-select: none`) e bloqueio de eventos de teclado relacionados a cópia (`Ctrl+C`, `Ctrl+A`, `Ctrl+X`), sem impedir a interação normal do estudante com os controles da interface (campos de entrada, botões).

## Glossário

- **UI**: Interface do usuário da plataforma Kodie, construída em React 19 + Vite 7 com CSS puro.
- **Tela de Avaliação**: Qualquer tela exibida durante os estágios `QUESTIONS` e `REVIEW` do fluxo de avaliação.
- **Conteúdo Protegido**: Textos de questões, enunciados, alternativas de resposta e quaisquer outros textos estáticos exibidos nas telas de avaliação.
- **Controles Interativos**: Elementos que requerem interação do usuário: campos de entrada (`input`), botões (`button`) e áreas de rolagem.
- **Seleção de Texto**: Ação do usuário de destacar texto com o cursor do mouse ou teclado.
- **Cópia de Texto**: Ação do usuário de copiar texto selecionado para a área de transferência, via atalho de teclado ou menu de contexto.

## Requisitos

### Requisito 1: Desabilitar seleção de texto nas telas de avaliação

**User Story:** Como administrador da plataforma, quero impedir que estudantes selecionem texto durante a avaliação, para que o conteúdo das questões não seja facilmente copiado.

#### Critérios de Aceitação

1. WHILE o estágio da avaliação for `QUESTIONS`, THE UI SHALL aplicar `user-select: none` em todo o conteúdo protegido.
2. WHILE o estágio da avaliação for `REVIEW`, THE UI SHALL aplicar `user-select: none` em todo o conteúdo protegido.
3. THE UI SHALL preservar a capacidade de interação normal com controles interativos (campos `input` e botões `button`) mesmo quando a seleção de texto estiver desabilitada.
4. WHEN o estudante tentar selecionar texto com o mouse nas telas de avaliação, THE UI SHALL impedir que qualquer texto seja destacado visualmente.

### Requisito 2: Bloquear atalhos de teclado de cópia nas telas de avaliação

**User Story:** Como administrador da plataforma, quero bloquear os atalhos de teclado de cópia durante a avaliação, para que o conteúdo não seja transferido para a área de transferência do estudante.

#### Critérios de Aceitação

1. WHILE o estágio da avaliação for `QUESTIONS`, THE UI SHALL interceptar e cancelar o evento de teclado `Ctrl+C` (ou `Cmd+C` em macOS).
2. WHILE o estágio da avaliação for `QUESTIONS`, THE UI SHALL interceptar e cancelar o evento de teclado `Ctrl+A` (ou `Cmd+A` em macOS).
3. WHILE o estágio da avaliação for `QUESTIONS`, THE UI SHALL interceptar e cancelar o evento de teclado `Ctrl+X` (ou `Cmd+X` em macOS).
4. WHILE o estágio da avaliação for `REVIEW`, THE UI SHALL interceptar e cancelar os eventos de teclado `Ctrl+C`, `Ctrl+A` e `Ctrl+X` (e equivalentes macOS).
5. IF o estudante pressionar um atalho de teclado não relacionado a cópia, THEN THE UI SHALL processar o evento normalmente, sem interferência.

### Requisito 3: Desabilitar menu de contexto nas telas de avaliação

**User Story:** Como administrador da plataforma, quero desabilitar o menu de contexto do botão direito do mouse durante a avaliação, para remover o acesso à opção "Copiar" via interface do navegador.

#### Critérios de Aceitação

1. WHILE o estágio da avaliação for `QUESTIONS`, THE UI SHALL interceptar e cancelar o evento `contextmenu` acionado sobre conteúdo protegido.
2. WHILE o estágio da avaliação for `REVIEW`, THE UI SHALL interceptar e cancelar o evento `contextmenu` acionado sobre conteúdo protegido.
3. IF o evento `contextmenu` for acionado sobre um controle interativo (campo `input` ou botão `button`), THEN THE UI SHALL permitir que o menu de contexto padrão do navegador seja exibido normalmente.

### Requisito 4: Escopo restrito às telas de avaliação

**User Story:** Como estudante, quero que as restrições de seleção e cópia se apliquem apenas durante a avaliação, para que eu possa interagir normalmente com outras partes da plataforma.

#### Critérios de Aceitação

1. WHILE o estágio da avaliação for `AUTH`, THE UI SHALL permitir seleção de texto, cópia e menu de contexto sem restrições.
2. WHILE o estágio da avaliação for `INTRO`, THE UI SHALL permitir seleção de texto, cópia e menu de contexto sem restrições.
3. WHILE o estágio da avaliação for `COMPLETED`, THE UI SHALL permitir seleção de texto, cópia e menu de contexto sem restrições.
4. THE UI SHALL ativar as restrições exclusivamente nos estágios `QUESTIONS` e `REVIEW`.
