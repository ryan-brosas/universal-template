/** Minimal send/close/listen surface. Real `WebSocket` objects satisfy this. */
export const WIRE_OPEN = 1;
export const WIRE_CLOSED = 3;

export type WireEvent = { data?: string };
export type WireListener = (ev: WireEvent) => void;
export type WireEventType = 'message' | 'close' | 'error' | 'open';

export type Wire = {
  readonly readyState: number;
  send(data: string): void;
  close(): void;
  addEventListener(type: WireEventType, listener: WireListener): void;
};
