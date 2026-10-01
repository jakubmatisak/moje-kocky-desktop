import type { paths } from '@/api/schema'
import createClient from 'openapi-fetch'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { DESKTOP_ORIGIN, desktopFetch } from './bridge'

function toBase64 (text: string): string {
  return btoa(String.fromCodePoint(...new TextEncoder().encode(text)))
}

function installBridge (answer: (method: string, path: string, headers: Record<string, string>, body: string | null) => unknown) {
  const request = vi.fn(async (method: string, path: string, headers: Record<string, string>, body: string | null) => answer(method, path, headers, body))
  ;(window as unknown as { pywebview: unknown }).pywebview = { api: { request, save_file: vi.fn(async () => true) } }
  return request
}

describe('desktop: fetch cez most namiesto siete', () => {
  afterEach(() => {
    delete (window as unknown as { pywebview?: unknown }).pywebview
  })

  it('požiadavku API pošle mostu s metódou, cestou, hlavičkami a telom', async () => {
    const request = installBridge(() => ({
      status: 201,
      headers: { 'content-type': 'application/json' },
      body: toBase64('{"ok":true}'),
    }))
    const response = await desktopFetch(new Request(`${DESKTOP_ORIGIN}/api/v1/items?x=1`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer t' },
      body: '{"a":1}',
    }))
    expect(response.status).toBe(201)
    expect(await response.json()).toEqual({ ok: true })
    const [method, path, headers, body] = request.mock.calls[0]!
    expect(method).toBe('POST')
    expect(path).toBe('/api/v1/items?x=1')
    expect(headers.authorization).toBe('Bearer t')
    expect(atob(body!)).toBe('{"a":1}')
  })

  it('binárnu odpoveď vráti ako blob bez poškodenia', async () => {
    const bytes = new Uint8Array([0, 255, 128, 7])
    installBridge(() => ({
      status: 200,
      headers: { 'content-type': 'image/jpeg' },
      body: btoa(String.fromCodePoint(...bytes)),
    }))
    const response = await desktopFetch(`${DESKTOP_ORIGIN}/api/v1/photos/1`)
    expect([...new Uint8Array(await response.arrayBuffer())]).toEqual([0, 255, 128, 7])
  })

  it('pole v dotaze (viac sérií) pošle mostu ako opakovaný parameter, celé', async () => {
    const request = installBridge(() => ({
      status: 200,
      headers: { 'content-type': 'application/json' },
      body: toBase64('[]'),
    }))
    const client = createClient<paths>({ baseUrl: `${DESKTOP_ORIGIN}/api/v1`, fetch: r => desktopFetch(r) })
    await client.GET('/wishlist/themes', { params: { query: { theme: ['Icons', 'Star Wars'], q: 'falcon' } } })
    const path = request.mock.calls[0]![1]
    const url = new URL(path, DESKTOP_ORIGIN)
    expect(url.pathname).toBe('/api/v1/wishlist/themes')
    expect(url.searchParams.getAll('theme')).toEqual(['Icons', 'Star Wars'])
    expect(url.searchParams.get('q')).toBe('falcon')
  })

  it('iné adresy (súbory appky) idú obyčajným fetch', async () => {
    const native = vi.fn(async () => new Response('wasm'))
    vi.stubGlobal('fetch', native)
    const request = installBridge(() => ({ status: 200, headers: {}, body: '' }))
    const { desktopFetch: patched } = await import('./bridge')
    await patched('./assets/zxing.wasm')
    expect(request).not.toHaveBeenCalled()
    vi.unstubAllGlobals()
  })
})
