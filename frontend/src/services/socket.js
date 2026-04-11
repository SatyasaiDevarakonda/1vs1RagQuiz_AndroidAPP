/**
 * WebSocket Service - Handles real-time communication
 */

class SocketService {
  constructor() {
    this.socket = null
    this.socketId = null
    this.connected = false
    this.connecting = false
    this.handlers = new Map()
    this.reconnectAttempts = 0
    this.maxReconnectAttempts = 5
    this.reconnectDelay = 1000
    this.connectionPromise = null
    this.serverTimeOffset = 0
  }

  connect() {
    // Return existing connection promise if already connecting
    if (this.connectionPromise) {
      return this.connectionPromise
    }

    // Return resolved promise if already connected
    if (this.connected && this.socket?.readyState === WebSocket.OPEN) {
      return Promise.resolve(true)
    }

    this.connectionPromise = new Promise((resolve, reject) => {
      try {
        // Determine WebSocket URL - use relative path for proxy
        const wsUrl = `/ws`

        console.log('🔌 Connecting to WebSocket:', wsUrl)
        this.connecting = true
        this.emit('connectionChange', { status: 'connecting' })

        // Close existing socket if any
        if (this.socket) {
          this.socket.close()
        }

        this.socket = new WebSocket(wsUrl)

        // Connection opened
        this.socket.onopen = () => {
          console.log('✅ WebSocket connection opened')
        }

        // Handle messages
        this.socket.onmessage = (event) => {
          try {
            const { event: eventName, data } = JSON.parse(event.data)
            
            // Handle connection confirmation
            if (eventName === 'connected') {
              this.socketId = data.socketId
              this.connected = true
              this.connecting = false
              this.reconnectAttempts = 0
              
              if (data.serverTime) {
                this.serverTimeOffset = Date.now() - data.serverTime
              }
              
              console.log('✅ WebSocket connected successfully, ID:', this.socketId)
              this.emit('connectionChange', { status: 'connected', socketId: this.socketId })
              resolve(true)
            }
            
            // Emit to registered handlers
            this.emit(eventName, data)
            
          } catch (e) {
            console.error('❌ Error parsing WebSocket message:', e)
          }
        }

        // Connection closed
        this.socket.onclose = (event) => {
          console.log('🔌 WebSocket closed:', event.code, event.reason)
          this.connected = false
          this.connecting = false
          this.connectionPromise = null
          
          this.emit('connectionChange', { 
            status: 'disconnected',
            code: event.code,
            reason: event.reason 
          })

          // Attempt reconnection if not a clean close
          if (event.code !== 1000 && this.reconnectAttempts < this.maxReconnectAttempts) {
            this.scheduleReconnect()
          }
        }

        // Connection error
        this.socket.onerror = (error) => {
          console.error('❌ WebSocket error:', error)
          this.connecting = false
          this.connectionPromise = null
          this.emit('connectionChange', { status: 'error', error })
          reject(error)
        }

        // Timeout for connection
        setTimeout(() => {
          if (this.connecting && !this.connected) {
            console.warn('⏱️ WebSocket connection timeout')
            this.socket?.close()
            this.connectionPromise = null
            reject(new Error('Connection timeout'))
          }
        }, 10000)

      } catch (error) {
        console.error('❌ Failed to create WebSocket:', error)
        this.connecting = false
        this.connectionPromise = null
        reject(error)
      }
    })

    return this.connectionPromise
  }



  scheduleReconnect() {
    this.reconnectAttempts++
    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1)
    
    console.log(`🔄 Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`)
    this.emit('connectionChange', { status: 'reconnecting', attempt: this.reconnectAttempts })
    
    setTimeout(() => {
      this.connect().catch(console.error)
    }, delay)
  }

  disconnect() {
    if (this.socket) {
      this.socket.close(1000, 'User disconnect')
      this.socket = null
    }
    this.connected = false
    this.connecting = false
    this.socketId = null
    this.connectionPromise = null
    this.reconnectAttempts = this.maxReconnectAttempts // Prevent auto-reconnect
  }

  send(event, data = {}) {
    if (!this.socket || this.socket.readyState !== WebSocket.OPEN) {
      console.warn('⚠️ Cannot send - WebSocket not connected')
      return false
    }

    try {
      this.socket.send(JSON.stringify({ event, data }))
      return true
    } catch (error) {
      console.error('❌ Failed to send message:', error)
      return false
    }
  }

  on(event, callback) {
    if (!this.handlers.has(event)) {
      this.handlers.set(event, new Set())
    }
    this.handlers.get(event).add(callback)
    
    // Return unsubscribe function
    return () => {
      this.handlers.get(event)?.delete(callback)
    }
  }

  off(event, callback) {
    if (callback) {
      this.handlers.get(event)?.delete(callback)
    } else {
      this.handlers.delete(event)
    }
  }

  emit(event, data) {
    const callbacks = this.handlers.get(event)
    if (callbacks) {
      callbacks.forEach(callback => {
        try {
          callback(data)
        } catch (e) {
          console.error(`Error in ${event} handler:`, e)
        }
      })
    }
  }

  isConnected() {
    return this.connected && this.socket?.readyState === WebSocket.OPEN
  }

  getStatus() {
    if (this.connected && this.socket?.readyState === WebSocket.OPEN) {
      return 'connected'
    }
    if (this.connecting) {
      return 'connecting'
    }
    return 'disconnected'
  }

  getServerTime() {
    return Date.now() - this.serverTimeOffset
  }
}

// Singleton instance
export const socketService = new SocketService()
export default socketService
