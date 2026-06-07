import type { WsMessage, WsMessageType } from '@/types/game'

export type { WsMessageType } from '@/types/game'

type EventHandler = (payload: unknown) => void

class WebSocketService {
  private ws: WebSocket | null = null
  private handlers: Map<string, Set<EventHandler>> = new Map()
  private reconnectTimer: number | null = null
  private heartbeatTimer: number | null = null
  private url: string = ''
  private reconnectAttempts = 0
  private maxReconnectAttempts = 5
  private reconnectDelay = 3000
  private isManualClose = false

  /** 连接 WebSocket */
  connect(url: string) {
    this.url = url
    this.isManualClose = false
    this.createConnection()
  }

  private createConnection() {
    if (this.ws) {
      this.ws.close()
    }

    this.ws = new WebSocket(this.url)

    this.ws.onopen = () => {
      console.log('[WS] Connected')
      this.reconnectAttempts = 0
      this.startHeartbeat()
    }

    this.ws.onmessage = (event: MessageEvent) => {
      try {
        const raw = JSON.parse(event.data)
        // Backend sends {type, data}, frontend internally uses {type, payload}
        const message: WsMessage = {
          type: raw.type,
          payload: raw.data ?? raw.payload,
          timestamp: raw.timestamp ?? new Date().toISOString(),
        }
        this.emit(message.type, message.payload)
      } catch (error) {
        console.error('[WS] Failed to parse message:', error)
      }
    }

    this.ws.onerror = (error) => {
      console.error('[WS] Error:', error)
    }

    this.ws.onclose = () => {
      console.log('[WS] Disconnected')
      this.stopHeartbeat()
      if (!this.isManualClose) {
        this.attemptReconnect()
      }
    }
  }

  /** 监听事件 */
  on(type: WsMessageType | string, handler: EventHandler) {
    if (!this.handlers.has(type)) {
      this.handlers.set(type, new Set())
    }
    this.handlers.get(type)!.add(handler)
  }

  /** 取消监听 */
  off(type: WsMessageType | string, handler: EventHandler) {
    const handlers = this.handlers.get(type)
    if (handlers) {
      handlers.delete(handler)
    }
  }

  /** 触发事件 */
  private emit(type: string, payload: unknown) {
    const handlers = this.handlers.get(type)
    if (handlers) {
      handlers.forEach((handler) => {
        try {
          handler(payload)
        } catch (error) {
          console.error(`[WS] Error in handler for ${type}:`, error)
        }
      })
    }
  }

  /** 发送消息 */
  send(type: WsMessageType | string, payload: unknown) {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      console.error('[WS] Not connected')
      return false
    }

    const message: WsMessage = {
      type: type as WsMessageType,
      payload,
      timestamp: new Date().toISOString(),
    }

    this.ws.send(JSON.stringify(message))
    return true
  }

  /** 断开连接 */
  disconnect() {
    this.isManualClose = true
    this.stopHeartbeat()
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer)
      this.reconnectTimer = null
    }
    if (this.ws) {
      this.ws.close()
      this.ws = null
    }
  }

  /** 尝试重连 */
  private attemptReconnect() {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('[WS] Max reconnect attempts reached')
      return
    }

    this.reconnectAttempts++
    console.log(`[WS] Reconnecting... (${this.reconnectAttempts}/${this.maxReconnectAttempts})`)

    this.reconnectTimer = window.setTimeout(() => {
      this.createConnection()
    }, this.reconnectDelay * this.reconnectAttempts)
  }

  /** 心跳检测 */
  private startHeartbeat() {
    this.stopHeartbeat()
    this.heartbeatTimer = window.setInterval(() => {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        this.ws.send(JSON.stringify({ type: 'ping', timestamp: new Date().toISOString() }))
      }
    }, 30000)
  }

  private stopHeartbeat() {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer)
      this.heartbeatTimer = null
    }
  }

  /** 连接状态 */
  get connected(): boolean {
    return this.ws !== null && this.ws.readyState === WebSocket.OPEN
  }
}

export const wsService = new WebSocketService()
export default wsService
