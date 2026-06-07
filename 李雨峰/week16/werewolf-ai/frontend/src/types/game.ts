/** 玩家角色 */
export enum PlayerRole {
  Werewolf = 'Werewolf',
  Villager = 'Villager',
  Seer = 'Seer',
  Witch = 'Witch',
  Hunter = 'Hunter',
  Idiot = 'Idiot',
}

/** 游戏阶段 */
export enum GamePhase {
  Night = 'Night',
  Day = 'Day',
  Discussion = 'Discussion',
  Vote = 'Vote',
  GameOver = 'GameOver',
}

/** 角色中文名称映射 */
export const ROLE_LABELS: Record<PlayerRole, string> = {
  [PlayerRole.Werewolf]: '狼人',
  [PlayerRole.Villager]: '村民',
  [PlayerRole.Seer]: '预言家',
  [PlayerRole.Witch]: '女巫',
  [PlayerRole.Hunter]: '猎人',
  [PlayerRole.Idiot]: '白痴',
}

/** 阶段中文名称映射 */
export const PHASE_LABELS: Record<GamePhase, string> = {
  [GamePhase.Night]: '夜晚',
  [GamePhase.Day]: '白天',
  [GamePhase.Discussion]: '讨论',
  [GamePhase.Vote]: '投票',
  [GamePhase.GameOver]: '游戏结束',
}

/** 玩家信息 */
export interface Player {
  id: string
  name: string
  role: PlayerRole | null // null 表示游戏尚未开始或角色未揭示
  isAlive: boolean
  isHuman: boolean
  avatar?: string
}

/** 游戏事件（事件流） */
export interface GameEvent {
  id: string
  phase: GamePhase
  type: string // 事件类型，如 'night_action', 'death', 'speech', 'vote_result' 等
  timestamp: string // ISO 8601
  content: string // 事件描述/文本
  actorId?: string // 触发事件的玩家 ID
  targetId?: string // 事件目标玩家 ID
  data?: Record<string, unknown> // 额外数据
}

/** 房间信息 */
export interface Room {
  id: string
  code: string // 房间号/邀请码
  hostId: string
  players: Player[]
  maxPlayers: number
  status: 'waiting' | 'playing' | 'finished'
  createdAt: string
}

/** 游戏状态 */
export interface GameState {
  roomId: string
  phase: GamePhase
  currentDay: number
  alivePlayers: Player[]
  deadPlayers: Player[]
  events: GameEvent[]
  currentPlayerTurn?: string // 当前发言/操作的玩家 ID
  voteOptions?: string[] // 可投票的目标 ID 列表
  nightActions?: NightAction[] // 夜晚可执行的操作
}

/** 夜晚操作类型 */
export interface NightAction {
  role: PlayerRole
  label: string
  canTarget: boolean // 是否需要选择目标
  description: string
}

/** 投票结果 */
export interface VoteResult {
  targetId: string
  votes: number
  eliminated: boolean
}

/** API 响应包装 */
export interface ApiResponse<T = unknown> {
  code: number
  message: string
  data: T
}

/** 创建房间请求 */
export interface CreateRoomRequest {
  hostName: string
  maxPlayers?: number
}

/** 加入房间请求 */
export interface JoinRoomRequest {
  playerName: string
  roomCode: string
}

/** WebSocket 消息类型 */
export enum WsMessageType {
  Join = 'join',
  Leave = 'leave',
  GameStart = 'game_start',
  PhaseChange = 'phase_change',
  Event = 'event',
  Vote = 'vote',
  NightAction = 'night_action',
  Chat = 'chat',
  GameOver = 'game_over',
  Error = 'error',
}

/** WebSocket 消息基础 */
export interface WsMessage<T = unknown> {
  type: WsMessageType
  payload: T
  timestamp: string
}
