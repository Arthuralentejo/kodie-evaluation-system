import { useEffect } from 'react';
import { STAGES } from '../config';

const PROTECTED_STAGES = new Set([STAGES.QUESTIONS, STAGES.REVIEW]);

/**
 * Ativa proteção de seleção/cópia de texto nos estágios QUESTIONS e REVIEW.
 *
 * @param {string} stage - Estágio atual do fluxo (valor do enum STAGES)
 * @param {React.RefObject<HTMLElement>} containerRef - Ref para o elemento raiz (app-shell)
 */
export function useTextSelectionGuard(stage, containerRef) {
  const isProtected = PROTECTED_STAGES.has(stage);

  useEffect(() => {
    const el = containerRef.current;
    if (el) {
      if (isProtected) {
        el.classList.add('no-select');
      } else {
        el.classList.remove('no-select');
      }
    }

    if (!isProtected) return;

    function handleKeyDown(event) {
      const isProtectedKey = ['c', 'a', 'x'].includes(event.key.toLowerCase());
      const isModified = event.ctrlKey || event.metaKey;
      if (isModified && isProtectedKey) {
        event.preventDefault();
      }
    }

    function handleContextMenu(event) {
      const isInteractive = event.target.closest('input, button') !== null;
      if (!isInteractive) {
        event.preventDefault();
      }
    }

    document.addEventListener('keydown', handleKeyDown);
    document.addEventListener('contextmenu', handleContextMenu);

    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      document.removeEventListener('contextmenu', handleContextMenu);
    };
  }, [isProtected, containerRef]);
}
