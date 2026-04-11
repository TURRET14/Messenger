import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { ModalChrome } from "../components/ui/ModalChrome";

type AlertState = {
  title?: string;
  message: string;
  onClose: () => void;
} | null;

type ConfirmState = {
  title?: string;
  message: string;
  confirmLabel?: string;
  cancelLabel?: string;
  danger?: boolean;
  onResult: (v: boolean) => void;
} | null;

type DialogsContextValue = {
  alert: (message: string, title?: string) => Promise<void>;
  confirm: (opts: {
    message: string;
    title?: string;
    confirmLabel?: string;
    cancelLabel?: string;
    danger?: boolean;
  }) => Promise<boolean>;
};

const DialogsContext = createContext<DialogsContextValue | null>(null);

export function DialogsProvider({ children }: { children: ReactNode }) {
  const [alertState, setAlertState] = useState<AlertState>(null);
  const [confirmState, setConfirmState] = useState<ConfirmState>(null);

  const alertFn = useCallback((message: string, title?: string) => {
    return new Promise<void>((resolve) => {
      setAlertState({
        title,
        message,
        onClose: () => {
          setAlertState(null);
          resolve();
        },
      });
    });
  }, []);

  const confirmFn = useCallback(
    (opts: {
      message: string;
      title?: string;
      confirmLabel?: string;
      cancelLabel?: string;
      danger?: boolean;
    }) => {
      return new Promise<boolean>((resolve) => {
        setConfirmState({
          ...opts,
          onResult: (v) => {
            setConfirmState(null);
            resolve(v);
          },
        });
      });
    },
    [],
  );

  const value = useMemo(
    () => ({ alert: alertFn, confirm: confirmFn }),
    [alertFn, confirmFn],
  );

  return (
    <DialogsContext.Provider value={value}>
      {children}
      {alertState ? (
        <ModalChrome
          title={alertState.title ?? "Сообщение"}
          onClose={alertState.onClose}
          narrow
        >
          <p style={{ margin: "0 0 16px", whiteSpace: "pre-wrap" }}>
            {alertState.message}
          </p>
          <button
            type="button"
            className="ui-btn ui-btn--primary"
            onClick={alertState.onClose}
          >
            ОК
          </button>
        </ModalChrome>
      ) : null}
      {confirmState ? (
        <ModalChrome
          title={confirmState.title ?? "Подтверждение"}
          onClose={() => confirmState.onResult(false)}
          narrow
        >
          <p style={{ margin: "0 0 16px", whiteSpace: "pre-wrap" }}>
            {confirmState.message}
          </p>
          <div className="ui-modal-actions">
            <button
              type="button"
              className="ui-btn ui-btn--ghost"
              onClick={() => confirmState.onResult(false)}
            >
              {confirmState.cancelLabel ?? "Отмена"}
            </button>
            <button
              type="button"
              className={
                confirmState.danger
                  ? "ui-btn ui-btn--danger"
                  : "ui-btn ui-btn--primary"
              }
              onClick={() => confirmState.onResult(true)}
            >
              {confirmState.confirmLabel ?? "Да"}
            </button>
          </div>
        </ModalChrome>
      ) : null}
    </DialogsContext.Provider>
  );
}

export function useDialogs(): DialogsContextValue {
  const ctx = useContext(DialogsContext);
  if (!ctx) throw new Error("useDialogs outside DialogsProvider");
  return ctx;
}
