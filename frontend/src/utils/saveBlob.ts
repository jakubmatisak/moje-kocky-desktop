/**
 * Uloženie súboru (export, šablóna, moje údaje).
 *
 * Na webe cez dočasný odkaz, v desktope cez natívny dialóg „Uložiť ako“
 * (most do Pythonu), lebo okno appky sťahovanie cez odkaz nepodporuje.
 * Vráti false, keď používateľ dialóg zrušil.
 */
import { isDesktop, saveViaBridge } from '@/desktop/bridge'

export async function saveBlob (blob: Blob, filename: string): Promise<boolean> {
  if (isDesktop) {
    return saveViaBridge(blob, filename)
  }
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  link.click()
  // Uvoľniť až po spustení sťahovania, niektoré prehliadače si URL čítajú neskôr.
  setTimeout(() => URL.revokeObjectURL(url), 10_000)
  return true
}
