import { useEffect, useRef } from "react";

/**
 * Регистрирует «слой» в истории браузера, который закрывается по системной
 * кнопке «Назад» (или жесту на мобильном). Каждый активный слой добавляет
 * запись в history.state; нажатие Назад снимает верхний слой через
 * вызов его `onClose`.
 *
 * Реализация — общий модульный стек слоёв и единственный popstate-листенер.
 * Так несколько одновременно открытых слоёв не «дёргают» друг друга: каждое
 * нажатие Назад снимает ровно один (самый верхний) слой. Закрытие слоя
 * из UI (когда проп `open` стал false) откатывает свою запись из истории —
 * но только если она лежит на вершине, чтобы не выдернуть «балласт» из-под
 * других слоёв. Чтобы наш собственный `history.back()` не превратился в
 * каскадное закрытие следующего слоя, мы помечаем такой переход флагом и
 * пропускаем один popstate.
 */

type StackEntry = { token: number; close: () => void };

const stack: StackEntry[] = [];
let nextToken = 1;
let suppressNextPopstate = false;
let listenerInstalled = false;

function ensureListener(): void {
  if (listenerInstalled) return;
  listenerInstalled = true;
  window.addEventListener("popstate", () => {
    if (suppressNextPopstate) {
      suppressNextPopstate = false;
      return;
    }
    const top = stack.pop();
    if (top) top.close();
  });
}

export function useBackButton(open: boolean, onClose: () => void): void {
  const onCloseRef = useRef(onClose);
  onCloseRef.current = onClose;

  useEffect(() => {
    if (!open) return;
    ensureListener();
    const token = nextToken++;
    const entry: StackEntry = {
      token,
      close: () => onCloseRef.current(),
    };
    stack.push(entry);
    window.history.pushState({ __mb: token }, "");

    return () => {
      const idx = stack.findIndex((e) => e.token === token);
      if (idx === -1) {
        // Слой уже снят popstate — наш onClose уже отработал, история
        // уже откатилась браузером.
        return;
      }
      stack.splice(idx, 1);
      // length тут уже после splice. Если индекс совпал с новой длиной —
      // мы были вершиной, надо убрать свою запись из истории. Иначе
      // запись похоронена под более глубокими слоями: дёргать history.back
      // нельзя, иначе случайно сорвём чужой слой.
      const wasTop = idx === stack.length;
      if (wasTop) {
        suppressNextPopstate = true;
        window.history.back();
      }
    };
  }, [open]);
}
