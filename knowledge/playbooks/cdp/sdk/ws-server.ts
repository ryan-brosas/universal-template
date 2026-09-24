/**
 * Tiny RFC 6455 text WebSocket server. CDP is JSON text frames; we don't
 * take a `ws` dependency. Bound only as an upgrade on the existing REPL
 * HTTP server (loopback).
 */
import { createHash } from 'node:crypto';
import type { IncomingMessage } from 'node:http';
import type { Duplex } from 'node:stream';
import { WIRE_CLOSED, WIRE_OPEN } from './wire.ts';

const GUID = '258EAFA5-E914-47DA-95CA-C5AB0DC85B11';

export type TextSocket = {
  readonly readyState: number;
  send(text: string): void;
  close(code?: number, reason?: string): void;
  onMessage(fn: (text: string) => void): void;
  onClose(fn: () => void): void;
};

export function isExtensionUpgrade(req: IncomingMessage): boolean {
  const url = new URL(req.url ?? '/', 'http://127.0.0.1');
  if (url.pathname !== '/extension') return false;
  const upgrade = String(req.headers.upgrade ?? '').toLowerCase();
  const connection = String(req.headers.connection ?? '').toLowerCase();
  return upgrade === 'websocket'
    && connection.includes('upgrade')
    && typeof req.headers['sec-websocket-key'] === 'string';
}

export function acceptExtensionUpgrade(
  req: IncomingMessage,
  socket: Duplex,
  head: Buffer,
  onOpen: (ws: TextSocket) => void,
): void {
  const key = req.headers['sec-websocket-key'];
  if (typeof key !== 'string') {
    socket.destroy();
    return;
  }
  const accept = createHash('sha1').update(key + GUID).digest('base64');
  socket.write(
    'HTTP/1.1 101 Switching Protocols\r\n'
    + 'Upgrade: websocket\r\n'
    + 'Connection: Upgrade\r\n'
    + `Sec-WebSocket-Accept: ${accept}\r\n`
    + '\r\n',
  );
  const ws = new SocketText(socket);
  if (head.length) ws.push(head);
  onOpen(ws);
}

class SocketText implements TextSocket {
  private closed = false;
  private buf: Buffer = Buffer.alloc(0);
  private fragments: Buffer[] = [];
  private fragmentOpcode: number | undefined;
  private messageListeners: Array<(text: string) => void> = [];
  private closeListeners: Array<() => void> = [];
  private socket: Duplex;

  constructor(socket: Duplex) {
    this.socket = socket;
    socket.on('data', (chunk: Buffer) => this.push(chunk));
    socket.on('close', () => this.markClosed());
    socket.on('error', () => this.markClosed());
  }

  get readyState(): number {
    return this.closed ? WIRE_CLOSED : WIRE_OPEN;
  }

  onMessage(fn: (text: string) => void): void {
    this.messageListeners.push(fn);
  }

  onClose(fn: () => void): void {
    this.closeListeners.push(fn);
  }

  send(text: string): void {
    if (this.closed) return;
    this.socket.write(encodeFrame(0x1, Buffer.from(text, 'utf8')));
  }

  close(code = 1000, reason = ''): void {
    if (this.closed) return;
    const reasonBuf = Buffer.from(reason, 'utf8');
    const payload = Buffer.alloc(2 + reasonBuf.length);
    payload.writeUInt16BE(code, 0);
    reasonBuf.copy(payload, 2);
    try { this.socket.write(encodeFrame(0x8, payload)); } catch { /* ignore */ }
    this.markClosed();
    try { this.socket.end(); } catch { /* ignore */ }
  }

  push(chunk: Buffer): void {
    if (this.closed) return;
    this.buf = Buffer.concat([this.buf, chunk]);
    this.drain();
  }

  private drain(): void {
    while (!this.closed) {
      const parsed = decodeFrame(this.buf);
      if (!parsed) return;
      this.buf = parsed.rest;
      this.dispatch(parsed.opcode, parsed.payload, parsed.fin);
    }
  }

  private dispatch(opcode: number, payload: Buffer, fin: boolean): void {
    if (opcode === 0x8) {
      this.markClosed();
      try { this.socket.end(); } catch { /* ignore */ }
      return;
    }
    if (opcode === 0x9) {
      if (!this.closed) this.socket.write(encodeFrame(0xa, payload));
      return;
    }
    if (opcode === 0xa) return;
    const dataOpcode = opcode === 0x0 ? this.fragmentOpcode : opcode;
    if (dataOpcode !== 0x1) return;
    if (!fin) {
      if (opcode !== 0x0) this.fragmentOpcode = opcode;
      this.fragments.push(payload);
      return;
    }
    let data = payload;
    if (this.fragments.length) {
      this.fragments.push(payload);
      data = Buffer.concat(this.fragments);
      this.fragments = [];
      this.fragmentOpcode = undefined;
    }
    const text = data.toString('utf8');
    for (const fn of this.messageListeners) {
      try { fn(text); } catch { /* ignore */ }
    }
  }

  private markClosed(): void {
    if (this.closed) return;
    this.closed = true;
    for (const fn of this.closeListeners) {
      try { fn(); } catch { /* ignore */ }
    }
  }
}

function encodeFrame(opcode: number, payload: Buffer): Buffer {
  const len = payload.length;
  let header: Buffer;
  if (len < 126) {
    header = Buffer.alloc(2);
    header[0] = 0x80 | opcode;
    header[1] = len;
  } else if (len < 65536) {
    header = Buffer.alloc(4);
    header[0] = 0x80 | opcode;
    header[1] = 126;
    header.writeUInt16BE(len, 2);
  } else {
    header = Buffer.alloc(10);
    header[0] = 0x80 | opcode;
    header[1] = 127;
    header.writeBigUInt64BE(BigInt(len), 2);
  }
  return Buffer.concat([header, payload]);
}

function decodeFrame(buf: Buffer): { opcode: number; payload: Buffer; fin: boolean; rest: Buffer } | undefined {
  if (buf.length < 2) return undefined;
  const b0 = buf[0]!;
  const b1 = buf[1]!;
  const fin = (b0 & 0x80) !== 0;
  const opcode = b0 & 0x0f;
  const masked = (b1 & 0x80) !== 0;
  let len = b1 & 0x7f;
  let offset = 2;
  if (len === 126) {
    if (buf.length < 4) return undefined;
    len = buf.readUInt16BE(2);
    offset = 4;
  } else if (len === 127) {
    if (buf.length < 10) return undefined;
    const big = buf.readBigUInt64BE(2);
    if (big > BigInt(Number.MAX_SAFE_INTEGER)) return undefined;
    len = Number(big);
    offset = 10;
  }
  const maskLen = masked ? 4 : 0;
  if (buf.length < offset + maskLen + len) return undefined;
  let payload = buf.subarray(offset + maskLen, offset + maskLen + len);
  if (masked) {
    const mask = buf.subarray(offset, offset + 4);
    const out = Buffer.from(payload);
    for (let i = 0; i < out.length; i++) out[i] = out[i]! ^ mask[i % 4]!;
    payload = out;
  }
  return { opcode, payload, fin, rest: buf.subarray(offset + maskLen + len) };
}
