/**
 * Thin API client for the AEGIS-X backend.
 *
 * The base URL comes from VITE_API_BASE so the same build works against a
 * local uvicorn process, a compose service, or a deployed backend.
 */

export const API_BASE: string =
  import.meta.env.VITE_API_BASE ?? 'http://localhost:8000'

export interface HealthResponse {
  status: string
  service: string
}

export class ApiError extends Error {
  // Declared explicitly rather than as a constructor parameter property,
  // which TypeScript's `erasableSyntaxOnly` mode disallows.
  status?: number

  constructor(message: string, status?: number) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${API_BASE}${path}`, {
      headers: { 'Content-Type': 'application/json' },
      ...init,
    })
  } catch {
    // fetch only rejects on network-level failure, which for our purposes
    // means the backend is not reachable at all.
    throw new ApiError(`Cannot reach the backend at ${API_BASE}`)
  }

  if (!response.ok) {
    throw new ApiError(
      `Request to ${path} failed with ${response.status}`,
      response.status,
    )
  }

  return (await response.json()) as T
}

export const getHealth = () => request<HealthResponse>('/health')
