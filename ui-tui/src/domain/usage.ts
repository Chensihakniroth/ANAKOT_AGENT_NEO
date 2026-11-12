import type { Usage } from '@anakot/shared/gateway-events'

export { usageFromTick } from '@anakot/shared/usage-tick'

export const ZERO: Usage = { calls: 0, input: 0, output: 0, total: 0 }
