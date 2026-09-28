/**
 * V desktope nahradí fetch mostom, skôr než vznikne klient API.
 * Musí to byť prvý import v main.ts.
 */
import { installDesktopFetch, isDesktop } from './bridge'

if (isDesktop) {
  installDesktopFetch()
}
