import { WS_BASE_URL } from './config';

type ManagedSocketOptions = {
  path: string;
  enabled: boolean;
  protocols?: string | string[];
  reconnectDelayMs?: number;
  onMessage?: (event: MessageEvent) => void;
  onOpen?: () => void;
  onClose?: () => void;
};

export class ManagedSocket {
  private options: ManagedSocketOptions;
  private socket: WebSocket | null = null;
  private reconnectTimer: number | null = null;
  private destroyed = false;
  private manualClose = false;

  constructor(options: ManagedSocketOptions) {
    this.options = options;
    if (options.enabled) {
      this.connect();
    }
  }

  update(options: ManagedSocketOptions) {
    const pathChanged = options.path !== this.options.path;
    const enabledChanged = options.enabled !== this.options.enabled;
    this.options = options;

    if (!options.enabled) {
      this.disconnect();
      return;
    }

    if (pathChanged || enabledChanged || !this.socket || this.socket.readyState > WebSocket.OPEN) {
      this.disconnect(false);
      this.connect();
    }
  }

  private connect() {
    if (!this.options.enabled || this.destroyed) {
      return;
    }

    this.clearReconnectTimer();
    this.manualClose = false;
    this.socket = new WebSocket(`${WS_BASE_URL}${this.options.path}`, this.options.protocols);
    this.socket.onopen = () => this.options.onOpen?.();
    this.socket.onmessage = (event) => this.options.onMessage?.(event);
    this.socket.onclose = () => {
      this.options.onClose?.();
      this.socket = null;
      if (!this.destroyed && !this.manualClose && this.options.enabled) {
        this.reconnectTimer = window.setTimeout(() => this.connect(), this.options.reconnectDelayMs ?? 1500);
      }
    };
    this.socket.onerror = () => {
      if (!this.manualClose && this.socket?.readyState === WebSocket.OPEN) {
        this.socket.close();
      }
    };
  }

  disconnect(destroy = false) {
    this.destroyed = destroy;
    this.clearReconnectTimer();
    this.manualClose = true;
    if (this.socket) {
      this.socket.onopen = null;
      this.socket.onmessage = null;
      this.socket.onclose = null;
      this.socket.onerror = null;
    }
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      this.socket.close();
    }
    this.socket = null;
  }

  private clearReconnectTimer() {
    if (this.reconnectTimer !== null) {
      window.clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
  }
}
