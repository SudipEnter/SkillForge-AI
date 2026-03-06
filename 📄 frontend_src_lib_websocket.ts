/**
 * SkillForge AI — WebSocket Client
 * Manages real-time WebSocket connections for Nova 2 Sonic voice streaming.
 */

type MessageHandler = (data: unknown) => void;
type AudioHandler = (chunk: ArrayBuffer) => void;
type StatusHandler = (status: string) => void;

interface WSOptions {
  onMessage?: MessageHandler;
  onAudio?: AudioHandler;
  onStatus?: StatusHandler;
  onError?: (error: Event) => void;
  onClose?: () => void;
}

export class SkillForgeWebSocket {
  private ws: WebSocket | null = null;
  private reconnectAttempts = 0;
  private maxReconnects = 3;
  private reconnectDelay = 2000;
  private options: WSOptions;
  private url: string;

  constructor(url: string, options: WSOptions = {}) {
    this.url = url;
    this.options = options;
  }

  connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      this.ws = new WebSocket(this.url);
      this.ws.binaryType = "arraybuffer";

      this.ws.onopen = () => {
        this.reconnectAttempts = 0;
        this.options.onStatus?.("connected");
        resolve();
      };

      this.ws.onerror = (error) => {
        this.options.onError?.(error);
        reject(error);
      };

      this.ws.onclose = () => {
        this.options.onStatus?.("disconnected");
        this.options.onClose?.();
        if (this.reconnectAttempts < this.maxReconnects) {
          this.reconnectAttempts++;
          setTimeout(() => this.connect(), this.reconnectDelay * this.reconnectAttempts);
        }
      };

      this.ws.onmessage = (event) => {
        if (event.data instanceof ArrayBuffer) {
          this.options.onAudio?.(event.data);
        } else {
          try {
            const data = JSON.parse(event.data as string) as unknown;
            this.options.onMessage?.(data);
          } catch {
            // Non-JSON text message — treat as raw transcript
            this.options.onMessage?.(event.data);
          }
        }
      };
    });
  }

  sendAudio(chunk: ArrayBuffer | Blob): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(chunk);
    }
  }

  sendJson(data: unknown): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
    }
  }

  sendControl(type: string, payload: Record<string, unknown> = {}): void {
    this.sendJson({ type, ...payload });
  }

  disconnect(): void {
    this.maxReconnects = 0; // Prevent reconnect on manual close
    this.ws?.close(1000, "Client disconnected");
    this.ws = null;
  }

  get isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }

  get readyState(): number {
    return this.ws?.readyState ?? WebSocket.CLOSED;
  }
}

// ── Audio Capture Utility ──────────────────────────────────────────
export class AudioCapture {
  private mediaStream: MediaStream | null = null;
  private audioContext: AudioContext | null = null;
  private processor: ScriptProcessorNode | null = null;
  private onChunk: (chunk: ArrayBuffer) => void;
  isRecording = false;

  constructor(onChunk: (chunk: ArrayBuffer) => void) {
    this.onChunk = onChunk;
  }

  async start(): Promise<void> {
    this.mediaStream = await navigator.mediaDevices.getUserMedia({
      audio: { sampleRate: 16000, channelCount: 1, echoCancellation: true, noiseSuppression: true },
    });

    this.audioContext = new AudioContext({ sampleRate: 16000 });
    const source = this.audioContext.createMediaStreamSource(this.mediaStream);
    this.processor = this.audioContext.createScriptProcessor(4096, 1, 1);

    this.processor.onaudioprocess = (e) => {
      if (!this.isRecording) return;
      const float32 = e.inputBuffer.getChannelData(0);
      const int16 = new Int16Array(float32.length);
      for (let i = 0; i < float32.length; i++) {
        int16[i] = Math.max(-32768, Math.min(32767, float32[i] * 32768));
      }
      this.onChunk(int16.buffer);
    };

    source.connect(this.processor);
    this.processor.connect(this.audioContext.destination);
    this.isRecording = true;
  }

  stop(): void {
    this.isRecording = false;
    this.processor?.disconnect();
    this.audioContext?.close();
    this.mediaStream?.getTracks().forEach(t => t.stop());
    this.mediaStream = null;
    this.audioContext = null;
    this.processor = null;
  }
}