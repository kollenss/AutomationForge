import { io } from 'socket.io-client'

// Single shared socket connection for the entire app.
export const socket = io({ autoConnect: true })
