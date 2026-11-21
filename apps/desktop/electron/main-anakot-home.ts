// The Anakot home the desktop main process runs against, resolved once at boot.
// Resolving it here also registers it with the file-preview read guard, so the
// home's (and every profile's) credential stores are refused before any IPC
// read can be served.

import { resolveDesktopAnakotHome } from './data-paths'
import { directoryExists } from './fs-probes'
import { setSensitiveAnakotHome } from './hardening'
import { readWindowsUserEnvVar } from './windows-user-env'

export function resolveMainAnakotHome(home: string): string {
  const anakotHome = resolveDesktopAnakotHome({
    home,
    directoryExists,
    readWindowsHome: (): string | null => readWindowsUserEnvVar('ANAKOT_HOME')
  })

  setSensitiveAnakotHome(anakotHome)

  return anakotHome
}
