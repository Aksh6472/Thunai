// The only place that calls fetch (CLAUDE.md §4). Maps the error envelope (API_SPEC §2.1).
import { tokenStore } from './tokenStore'

export interface ApiErrorBody {
  code: string
  message: string
  details?: Record<string, unknown>
  request_id?: string | null
}

export class ApiError extends Error {
  readonly status: number
  readonly code: string
  readonly details: Record<string, unknown>
  readonly requestId: string | null

  constructor(status: number, body: ApiErrorBody) {
    super(body.message)
    this.status = status
    this.code = body.code
    this.details = body.details ?? {}
    this.requestId = body.request_id ?? null
  }

  /** 422 field errors as { fieldName: message } (DESIGN §10). */
  fieldErrors(): Record<string, string> {
    const fields = (this.details.fields as { loc: string[]; msg: string }[] | undefined) ?? []
    return Object.fromEntries(fields.map((f) => [f.loc[f.loc.length - 1], f.msg]))
  }
}

export interface ApiResponse<T> {
  data: T
  status: number
  headers: Headers
}

export interface ApiClient {
  get<T>(path: string): Promise<T>
  post<T>(path: string, body?: unknown): Promise<T>
  patch<T>(path: string, body: unknown): Promise<T>
  request<T>(method: string, path: string, body?: unknown): Promise<ApiResponse<T>>
}

export function createHttpClient(baseUrl: string): ApiClient {
  async function request<T>(method: string, path: string, body?: unknown): Promise<ApiResponse<T>> {
    const headers: Record<string, string> = { Accept: 'application/json' }
    if (body !== undefined) headers['Content-Type'] = 'application/json'
    const token = tokenStore.get()
    if (token) headers.Authorization = `Bearer ${token}`
    let response: Response
    try {
      response = await fetch(`${baseUrl}${path}`, {
        method,
        headers,
        body: body === undefined ? undefined : JSON.stringify(body),
      })
    } catch {
      throw new ApiError(0, { code: 'NETWORK_ERROR', message: "Can't reach the server." })
    }
    const text = await response.text()
    const json = text ? (JSON.parse(text) as unknown) : null
    if (!response.ok) {
      const envelope = (json as { error?: ApiErrorBody } | null)?.error
      const error = new ApiError(
        response.status,
        envelope ?? { code: 'HTTP_ERROR', message: response.statusText },
      )
      if (response.status === 401 && !path.startsWith('/auth/login')) tokenStore.expire()
      throw error
    }
    return { data: json as T, status: response.status, headers: response.headers }
  }

  return {
    request,
    get: async (path) => (await request(`GET`, path)).data as never,
    post: async (path, body) => (await request(`POST`, path, body ?? {})).data as never,
    patch: async (path, body) => (await request(`PATCH`, path, body)).data as never,
  }
}
