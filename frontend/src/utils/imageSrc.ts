/**
 * Fotky setov z Rebrickable a Brickset idú cez vlastný server (`/img`).
 *
 * Keby si ich prehliadač ťahal sám, tie služby by videli IP adresu každého
 * návštevníka, aj na verejnom odkaze. Iné adresy (vlastné fotky kusov,
 * relatívne cesty) sa nemenia. Opakované použitie adresu nezmení.
 */

import { isDesktop } from '@/desktop/bridge'

const PROXIED_HOSTS = ['https://cdn.rebrickable.com/', 'https://images.brickset.com/']

export function imageSrc (url: string | null | undefined): string | null {
  if (!url) {
    return null
  }
  // Desktop: obrázky vidí len vlastník počítača, proxy netreba (a server nebeží).
  if (isDesktop) {
    return url
  }
  if (PROXIED_HOSTS.some(host => url.startsWith(host))) {
    return `/api/v1/img?u=${encodeURIComponent(url)}`
  }
  return url
}
