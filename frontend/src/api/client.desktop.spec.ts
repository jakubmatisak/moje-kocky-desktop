import type * as Bridge from '@/desktop/bridge'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

/**
 * Desktop: skutočný klient (openapi-fetch a middleware) cez most namiesto
 * siete. `desktopFetch` telo požiadavky prečíta (spotrebuje), preto po 401
 * klient opakuje z kópie urobenej pred odoslaním.
 */
vi.mock('@/desktop/bridge', async original => ({
  ...(await original<typeof Bridge>()),
  isDesktop: true,
}))

interface Seen { method: string, path: string, auth: string | undefined, body: string, status: number }

function toBase64 (text: string): string {
  return btoa(String.fromCodePoint(...new TextEncoder().encode(text)))
}

function fromBase64 (text: string): string {
  return new TextDecoder().decode(Uint8Array.from(atob(text), c => c.codePointAt(0)!))
}

function fakeBridge () {
  const state = { valid: 'po-zmene' }
  const seen: Seen[] = []
  const request = vi.fn(async (method: string, path: string, headers: Record<string, string>, body: string | null) => {
    const text = body ? fromBase64(body) : ''
    const auth = headers.authorization
    let status = 200
    let answer: unknown
    if (path === '/api/v1/auth/refresh') {
      answer = { access_token: state.valid, token_type: 'bearer', expires_in: 900 }
    } else if (auth === `Bearer ${state.valid}`) {
      answer = text ? JSON.parse(text) : { email: 'a@example.com' }
    } else {
      status = 401
      answer = { detail: 'Prihlásenie je potrebné' }
    }
    seen.push({ method, path, auth, body: text, status })
    return { status, headers: { 'content-type': 'application/json' }, body: toBase64(JSON.stringify(answer)) }
  })
  ;(window as unknown as { pywebview: unknown }).pywebview = { api: { request, save_file: vi.fn(async () => true) } }
  return { state, seen }
}

let bridge: ReturnType<typeof fakeBridge>
const originalFetch = globalThis.fetch

beforeEach(async () => {
  vi.resetModules()
  bridge = fakeBridge()
  const { installDesktopFetch } = await import('@/desktop/bridge')
  installDesktopFetch()
})

afterEach(() => {
  globalThis.fetch = originalFetch
  delete (window as unknown as { pywebview?: unknown }).pywebview
})

describe('desktop: obnova prístupového tokenu po 401 cez most', () => {
  it('požiadavku s telom zopakuje mostom s tým istým telom a novým tokenom', async () => {
    const { api, setAccessToken } = await import('./client')
    setAccessToken('pred-zmenou')

    const { data, response } = await api.PUT('/auth/me/preferences/{key}', {
      params: { path: { key: 'collection' } },
      body: { q: 'hrad' },
    })

    expect(response.status).toBe(200)
    expect(data).toEqual({ q: 'hrad' })
    const puts = bridge.seen.filter(s => s.method === 'PUT')
    expect(puts.map(s => [s.auth, s.status])).toEqual([
      ['Bearer pred-zmenou', 401],
      ['Bearer po-zmene', 200],
    ])
    expect(puts[1]!.body).toBe('{"q":"hrad"}')
    expect(bridge.seen.filter(s => s.path === '/api/v1/auth/refresh')).toHaveLength(1)
  })
})
