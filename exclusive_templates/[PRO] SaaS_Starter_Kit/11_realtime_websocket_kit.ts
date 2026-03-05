// ============================================================
// ⚡ REAL-TIME WEBSOCKET KIT — Production Patterns
// DevVault Pro 2026 — Presence, Live Updates, Notifications
// ============================================================

// ── 1. WebSocket Server Setup ───────────────────

// lib/ws-server.ts — Works with Next.js API routes
import { WebSocketServer, WebSocket } from 'ws'

interface Client {
    ws: WebSocket
    userId: string
    rooms: Set<string>
    metadata: { name: string; avatar: string; color: string }
}

class RealtimeServer {
    private wss: WebSocketServer
    private clients = new Map<string, Client>()
    private rooms = new Map<string, Set<string>>()

    constructor(port = 3001) {
        this.wss = new WebSocketServer({ port })
        this.wss.on('connection', (ws, req) => this.handleConnection(ws, req))
        console.log(`⚡ WebSocket server running on port ${port}`)
    }

    private handleConnection(ws: WebSocket, req: any) {
        const userId = this.extractUserId(req) // From auth token
        const client: Client = {
            ws,
            userId,
            rooms: new Set(),
            metadata: { name: '', avatar: '', color: '' },
        }

        this.clients.set(userId, client)

        ws.on('message', (data) => this.handleMessage(client, data.toString()))
        ws.on('close', () => this.handleDisconnect(client))
        ws.on('error', console.error)

        // Send connection confirmation
        this.send(ws, { type: 'connected', userId })
    }

    private handleMessage(client: Client, raw: string) {
        const msg = JSON.parse(raw)

        switch (msg.type) {
            case 'join_room':
                this.joinRoom(client, msg.roomId)
                break
            case 'leave_room':
                this.leaveRoom(client, msg.roomId)
                break
            case 'presence_update':
                this.updatePresence(client, msg.data)
                break
            case 'cursor_move':
                this.broadcastToRoom(msg.roomId, {
                    type: 'cursor_update',
                    userId: client.userId,
                    data: msg.data,
                }, client.userId)
                break
            case 'broadcast':
                this.broadcastToRoom(msg.roomId, {
                    type: 'broadcast',
                    userId: client.userId,
                    event: msg.event,
                    data: msg.data,
                }, client.userId)
                break
            case 'typing':
                this.broadcastToRoom(msg.roomId, {
                    type: 'typing',
                    userId: client.userId,
                    isTyping: msg.isTyping,
                }, client.userId)
                break
        }
    }

    private joinRoom(client: Client, roomId: string) {
        client.rooms.add(roomId)
        if (!this.rooms.has(roomId)) this.rooms.set(roomId, new Set())
        this.rooms.get(roomId)!.add(client.userId)

        // Notify room members
        this.broadcastToRoom(roomId, {
            type: 'user_joined',
            userId: client.userId,
            metadata: client.metadata,
            members: this.getRoomMembers(roomId),
        })
    }

    private leaveRoom(client: Client, roomId: string) {
        client.rooms.delete(roomId)
        this.rooms.get(roomId)?.delete(client.userId)

        this.broadcastToRoom(roomId, {
            type: 'user_left',
            userId: client.userId,
            members: this.getRoomMembers(roomId),
        })
    }

    private updatePresence(client: Client, data: any) {
        client.metadata = { ...client.metadata, ...data }
        for (const roomId of client.rooms) {
            this.broadcastToRoom(roomId, {
                type: 'presence_update',
                userId: client.userId,
                metadata: client.metadata,
            }, client.userId)
        }
    }

    private handleDisconnect(client: Client) {
        for (const roomId of client.rooms) {
            this.leaveRoom(client, roomId)
        }
        this.clients.delete(client.userId)
    }

    private broadcastToRoom(roomId: string, message: any, excludeUserId?: string) {
        const members = this.rooms.get(roomId)
        if (!members) return

        for (const userId of members) {
            if (userId === excludeUserId) continue
            const client = this.clients.get(userId)
            if (client) this.send(client.ws, message)
        }
    }

    private getRoomMembers(roomId: string) {
        const members = this.rooms.get(roomId) || new Set()
        return Array.from(members).map(id => {
            const client = this.clients.get(id)
            return { userId: id, ...client?.metadata }
        })
    }

    private send(ws: WebSocket, data: any) {
        if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify(data))
        }
    }

    private extractUserId(req: any): string {
        // Extract from auth token in URL or headers
        const url = new URL(req.url!, `http://${req.headers.host}`)
        return url.searchParams.get('userId') || 'anonymous'
    }
}


// ── 2. Client-Side Hook ─────────────────────────

// hooks/useRealtime.ts — React hook for WebSocket connections

/*
import { useEffect, useRef, useState, useCallback } from 'react'

interface UseRealtimeOptions {
  url: string
  userId: string
  roomId?: string
  onMessage?: (data: any) => void
  reconnectAttempts?: number
}

export function useRealtime({ url, userId, roomId, onMessage, reconnectAttempts = 5 }: UseRealtimeOptions) {
  const wsRef = useRef<WebSocket | null>(null)
  const [connected, setConnected] = useState(false)
  const [members, setMembers] = useState<any[]>([])
  const [typingUsers, setTypingUsers] = useState<Set<string>>(new Set())
  const attemptsRef = useRef(0)

  const connect = useCallback(() => {
    const ws = new WebSocket(`${url}?userId=${userId}`)

    ws.onopen = () => {
      setConnected(true)
      attemptsRef.current = 0
      if (roomId) ws.send(JSON.stringify({ type: 'join_room', roomId }))
    }

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data)

      switch (data.type) {
        case 'user_joined':
        case 'user_left':
          setMembers(data.members)
          break
        case 'typing':
          setTypingUsers(prev => {
            const next = new Set(prev)
            data.isTyping ? next.add(data.userId) : next.delete(data.userId)
            return next
          })
          break
      }

      onMessage?.(data)
    }

    ws.onclose = () => {
      setConnected(false)
      // Reconnect with exponential backoff
      if (attemptsRef.current < reconnectAttempts) {
        setTimeout(() => {
          attemptsRef.current++
          connect()
        }, Math.min(1000 * 2 ** attemptsRef.current, 30000))
      }
    }

    wsRef.current = ws
  }, [url, userId, roomId])

  useEffect(() => {
    connect()
    return () => wsRef.current?.close()
  }, [connect])

  const send = useCallback((data: any) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data))
    }
  }, [])

  const sendTyping = useCallback((isTyping: boolean) => {
    send({ type: 'typing', roomId, isTyping })
  }, [send, roomId])

  const sendCursor = useCallback((position: { x: number; y: number }) => {
    send({ type: 'cursor_move', roomId, data: position })
  }, [send, roomId])

  return { connected, members, typingUsers, send, sendTyping, sendCursor }
}
*/


// ── 3. Server-Sent Events (SSE) Alternative ────

// app/api/events/route.ts — SSE for simpler use cases

/*
export async function GET(req: NextRequest) {
  const encoder = new TextEncoder()
  const userId = req.headers.get('x-user-id')!

  const stream = new ReadableStream({
    start(controller) {
      // Subscribe to events for this user
      const unsubscribe = eventBus.subscribe(userId, (event) => {
        controller.enqueue(
          encoder.encode(`event: ${event.type}\ndata: ${JSON.stringify(event.data)}\n\n`)
        )
      })

      // Heartbeat every 30s to keep connection alive
      const heartbeat = setInterval(() => {
        controller.enqueue(encoder.encode(': heartbeat\n\n'))
      }, 30000)

      // Cleanup on disconnect
      req.signal.addEventListener('abort', () => {
        unsubscribe()
        clearInterval(heartbeat)
        controller.close()
      })
    },
  })

  return new Response(stream, {
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      Connection: 'keep-alive',
    },
  })
}
*/


// ── 4. Pub/Sub Event Bus ────────────────────────

type EventHandler = (event: any) => void

class EventBus {
    private subscribers = new Map<string, Set<EventHandler>>()
    private globalSubscribers = new Set<EventHandler>()

    subscribe(channel: string, handler: EventHandler): () => void {
        if (!this.subscribers.has(channel)) {
            this.subscribers.set(channel, new Set())
        }
        this.subscribers.get(channel)!.add(handler)

        return () => {
            this.subscribers.get(channel)?.delete(handler)
        }
    }

    subscribeAll(handler: EventHandler): () => void {
        this.globalSubscribers.add(handler)
        return () => this.globalSubscribers.delete(handler)
    }

    publish(channel: string, event: any) {
        // Notify channel subscribers
        this.subscribers.get(channel)?.forEach(handler => handler(event))
        // Notify global subscribers
        this.globalSubscribers.forEach(handler => handler({ channel, ...event }))
    }

    // Broadcast to multiple channels
    broadcast(channels: string[], event: any) {
        channels.forEach(channel => this.publish(channel, event))
    }
}

export const eventBus = new EventBus()


// ── 5. Notification System ──────────────────────

interface Notification {
    id: string
    userId: string
    type: 'info' | 'success' | 'warning' | 'error'
    title: string
    message: string
    read: boolean
    createdAt: Date
    actionUrl?: string
}

class NotificationService {
    async send(userId: string, notification: Omit<Notification, 'id' | 'read' | 'createdAt'>) {
        const saved = await db.notification.create({
            data: {
                ...notification,
                read: false,
                createdAt: new Date(),
            },
        })

        // Push in real-time via WebSocket/SSE
        eventBus.publish(`user:${userId}`, {
            type: 'notification',
            data: saved,
        })

        return saved
    }

    async markAsRead(notificationId: string, userId: string) {
        await db.notification.update({
            where: { id: notificationId, userId },
            data: { read: true },
        })
    }

    async getUnreadCount(userId: string): Promise<number> {
        return db.notification.count({
            where: { userId, read: false },
        })
    }
}

export const notifications = new NotificationService()
