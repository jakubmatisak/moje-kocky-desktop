/**
 * Desktop: okno volá appku cez most (`window.pywebview.api`), nie cez sieť.
 *
 * Stránka sa načítava zo súborov na disku (file://) a žiadny server na porte
 * nebeží. Požiadavky API idú na vymyslenú adresu `DESKTOP_ORIGIN`; náhradný
 * `fetch` ich pošle mostu v Pythone a odpoveď poskladá späť do `Response`.
 * Ostatné adresy (súbory appky, napríklad wasm čítačky kódov) idú obyčajným
 * fetch. Telo aj odpoveď cestujú v base64, aby prešli aj fotky a ZIP.
 */

export const isDesktop = import.meta.env.VITE_DESKTOP === '1'

/** Adresa, ktorá nikam nevedie; spozná sa podľa nej požiadavka pre most. */
export const DESKTOP_ORIGIN = 'https://moje-kocky.desktop'

interface BridgeAnswer { status: number, headers: Record<string, string>, body: string }
interface BridgeApi {
  request: (method: string, path: string, headers: Record<string, string>, body: string | null) => Promise<BridgeAnswer>
  save_file: (filename: string, data: string) => Promise<boolean>
}

/** Pôvodný fetch; `installDesktopFetch` ho nahradí a sem odloží pôvodný. */
let nativeFetch: typeof fetch = (input, init) => globalThis.fetch(input, init)

/** V desktope zavolať ako prvé, skôr než vznikne klient API. */
export function installDesktopFetch (): void {
  nativeFetch = globalThis.fetch.bind(globalThis)
  globalThis.fetch = desktopFetch
}

/**
 * Most je k dispozícii až po udalosti `pywebviewready`. Udalosť môže prísť
 * skôr, než appka začne čakať, preto sa popri nej pravidelne pozerá aj priamo.
 */
let ready: Promise<BridgeApi> | null = null

function bridge (): Promise<BridgeApi> {
  const current = () => (window as unknown as { pywebview?: { api?: BridgeApi } }).pywebview?.api
  const now = current()
  if (now?.request) {
    return Promise.resolve(now)
  }
  ready ??= new Promise(resolve => {
    const done = () => {
      const api = current()
      if (!api?.request) {
        return false
      }
      clearInterval(timer)
      window.removeEventListener('pywebviewready', check)
      resolve(api)
      return true
    }
    const check = () => {
      done()
    }
    const timer = setInterval(check, 30)
    window.addEventListener('pywebviewready', check)
  })
  return ready
}

function toBase64 (bytes: Uint8Array): string {
  let binary = ''
  const chunk = 0x80_00
  for (let i = 0; i < bytes.length; i += chunk) {
    binary += String.fromCodePoint(...bytes.subarray(i, i + chunk))
  }
  return btoa(binary)
}

function fromBase64 (text: string): Uint8Array {
  const binary = atob(text)
  const bytes = new Uint8Array(binary.length)
  for (let i = 0; i < binary.length; i++) {
    bytes[i] = binary.codePointAt(i)!
  }
  return bytes
}

export async function desktopFetch (input: RequestInfo | URL, init?: RequestInit): Promise<Response> {
  const href = input instanceof Request ? input.url : (input instanceof URL ? input.href : input)
  if (!href.startsWith(DESKTOP_ORIGIN)) {
    return nativeFetch(input, init)
  }
  const request = input instanceof Request ? input : new Request(href, init)
  const url = new URL(request.url)
  const headers: Record<string, string> = {}
  for (const [key, value] of request.headers.entries()) {
    headers[key] = value
  }
  const raw = request.body ? new Uint8Array(await request.arrayBuffer()) : null
  const api = await bridge()
  const answer = await api.request(request.method, url.pathname + url.search, headers, raw ? toBase64(raw) : null)
  // 204 a 304 nesmú mať telo, inak Response vyhodí chybu.
  const body = answer.status === 204 || answer.status === 304 ? null : fromBase64(answer.body)
  return new Response(body as BodyInit | null, { status: answer.status, headers: answer.headers })
}

/** Uloží súbor cez natívny dialóg „Uložiť ako“; vráti false, keď ho používateľ zruší. */
export async function saveViaBridge (blob: Blob, filename: string): Promise<boolean> {
  const api = await bridge()
  return api.save_file(filename, toBase64(new Uint8Array(await blob.arrayBuffer())))
}
