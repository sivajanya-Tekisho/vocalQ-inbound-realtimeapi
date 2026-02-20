/**
 * WebSocket utility for real-time call updates
 */

export interface WebSocketMessage {
    type: 'call_started' | 'call_updated' | 'call_ended' | 'transcript_update';
    data: any;
}

export class CallWebSocket {
    private ws: WebSocket | null = null;
    private reconnectAttempts = 0;
    private maxReconnectAttempts = 5;
    private reconnectDelay = 3000;
    private listeners: Map<string, Set<(data: any) => void>> = new Map();

    constructor(private url: string) { }

    connect() {
        if (this.ws?.readyState === WebSocket.OPEN) {
            return; // Already connected
        }

        try {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${protocol}//${window.location.hostname}:8000/api/v1/stream`;

            this.ws = new WebSocket(wsUrl);

            this.ws.onopen = () => {
                console.log('✅ WebSocket connected');
                this.reconnectAttempts = 0;
            };

            this.ws.onmessage = (event) => {
                try {
                    const message: WebSocketMessage = JSON.parse(event.data);
                    this.notifyListeners(message.type, message.data);
                } catch (error) {
                    console.error('Failed to parse WebSocket message:', error);
                }
            };

            this.ws.onerror = (error) => {
                console.error('WebSocket error:', error);
            };

            this.ws.onclose = () => {
                console.log('WebSocket disconnected');
                this.attemptReconnect();
            };
        } catch (error) {
            console.error('Failed to create WebSocket:', error);
            this.attemptReconnect();
        }
    }

    private attemptReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            console.log(`Reconnecting... (${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
            setTimeout(() => this.connect(), this.reconnectDelay);
        }
    }

    on(eventType: string, callback: (data: any) => void) {
        if (!this.listeners.has(eventType)) {
            this.listeners.set(eventType, new Set());
        }
        this.listeners.get(eventType)!.add(callback);
    }

    off(eventType: string, callback: (data: any) => void) {
        const callbacks = this.listeners.get(eventType);
        if (callbacks) {
            callbacks.delete(callback);
        }
    }

    private notifyListeners(eventType: string, data: any) {
        const callbacks = this.listeners.get(eventType);
        if (callbacks) {
            callbacks.forEach(callback => callback(data));
        }
    }

    disconnect() {
        if (this.ws) {
            this.ws.close();
            this.ws = null;
        }
        this.listeners.clear();
    }

    send(message: WebSocketMessage) {
        if (this.ws?.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(message));
        } else {
            console.warn('WebSocket is not connected');
        }
    }
}

// Singleton instance
let wsInstance: CallWebSocket | null = null;

export const getWebSocket = (): CallWebSocket => {
    if (!wsInstance) {
        wsInstance = new CallWebSocket('');
        wsInstance.connect();
    }
    return wsInstance;
};
