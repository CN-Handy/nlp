import axios, { type AxiosInstance, type AxiosRequestConfig } from 'axios'
import type { ApiResponse, Room, GameState, CreateRoomRequest, JoinRoomRequest } from '@/types/game'

const apiClient: AxiosInstance = axios.create({
  baseURL: '/api/v1',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// 请求拦截器
apiClient.interceptors.request.use(
  (config) => {
    const playerId = localStorage.getItem('playerId')
    if (playerId) {
      config.headers['X-Player-Id'] = playerId
    }
    return config
  },
  (error) => Promise.reject(error),
)

// 响应拦截器
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const message = error.response?.data?.message || '网络请求失败'
    console.error('[API Error]', message)
    return Promise.reject(error)
  },
)

/** 通用 GET 请求 */
export async function get<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
  const response = await apiClient.get<ApiResponse<T>>(url, config)
  if (response.data.code !== 0) {
    throw new Error(response.data.message)
  }
  return response.data.data
}

/** 通用 POST 请求 */
export async function post<T>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T> {
  const response = await apiClient.post<ApiResponse<T>>(url, data, config)
  if (response.data.code !== 0) {
    throw new Error(response.data.message)
  }
  return response.data.data
}

/** 一键开局（观战模式） */
export async function quickStart(): Promise<{ room_id: string; game_id: string; player_count: number }> {
  const response = await apiClient.post('/quick/start')
  return response.data
}

/** 创建房间 */
export async function createRoom(request: CreateRoomRequest): Promise<Room> {
  return post<Room>('/rooms', request)
}

/** 加入房间 */
export async function joinRoom(request: JoinRoomRequest): Promise<Room> {
  return post<Room>('/rooms/join', request)
}

/** 获取房间信息 */
export async function getRoom(roomId: string): Promise<Room> {
  return get<Room>(`/rooms/${roomId}`)
}

/** 获取游戏状态 */
export async function getGameState(roomId: string): Promise<GameState> {
  return get<GameState>(`/rooms/${roomId}/game`)
}

/** 开始游戏 */
export async function startGame(roomId: string): Promise<GameState> {
  return post<GameState>(`/rooms/${roomId}/start`)
}

/** 提交夜晚操作 */
export async function submitNightAction(
  roomId: string,
  action: { role: string; targetId?: string },
): Promise<void> {
  return post<void>(`/rooms/${roomId}/night-action`, action)
}

/** 提交投票 */
export async function submitVote(roomId: string, targetId: string): Promise<void> {
  return post<void>(`/rooms/${roomId}/vote`, { targetId })
}

/** 发送聊天/发言 */
export async function sendChat(roomId: string, content: string): Promise<void> {
  return post<void>(`/rooms/${roomId}/chat`, { content })
}

export default apiClient
