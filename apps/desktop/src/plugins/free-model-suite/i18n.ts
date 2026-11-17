import { type PluginLocaleBundles, type PluginTranslate, usePluginI18n } from '@anakot/plugin-sdk'
import { useMemo } from 'react'

const en = {
  apply: 'Apply',
  close: 'Close probe',
  current: 'Current',
  description: (count: number) => `Browse ${count} free models from providers already connected to this profile.`,
  empty: 'No free models found',
  emptyHelp: 'Connect a provider in Settings, then refresh this page.',
  failed: 'Free model probe failed',
  footer: 'A probe is stateless: it creates no session, runs no tools, and never changes your default model.',
  freeTier: 'Free tier',
  loading: 'Loading free models…',
  noResults: 'No free models match your search',
  open: 'Free Models: Open',
  probe: 'Test model',
  prompt: 'In one sentence, what is 2+2?',
  reasoning: 'Reasoning',
  refresh: 'Refresh catalog',
  run: 'Run test',
  running: 'Testing…',
  search: 'Search models or providers…',
  stealth: 'Stealth',
  stealthNote:
    'Unnamed preview SKUs. Free by convention, and rotated by the provider without notice — test one before switching to it.',
  switchFailed: 'Could not apply the model',
  switched: 'Default model updated',
  title: 'Free Model Suite',
  toolCalls: (count: number) => `${count} unrequested tool call${count === 1 ? '' : 's'}`,
  truncated: 'The reply reached the token limit and may be incomplete.',
  filtered: 'The provider filtered the reply.',
  emptyReply: 'The model returned no visible answer.',
  reasoningOnly: 'The model used the whole budget for reasoning and returned no visible answer.'
}

type Messages = typeof en

/**
 * Every leaf is resolved through `t()`, so a locale bundle actually localizes it. Spreading `...en`
 * instead — as this file used to — re-wraps only the keys it names and serves English for the rest,
 * which left every translation below dead.
 */
type Bound<T> = {
  [K in keyof T]: T[K] extends (...args: infer A) => string ? (...args: A) => string : string
}

function bind(t: PluginTranslate, template: Messages): Bound<Messages> {
  const out = {} as Record<string, unknown>

  for (const [key, value] of Object.entries(template)) {
    if (typeof value === 'function') {
      out[key] = (...args: unknown[]) => t(key, ...args)

      continue
    }

    // `translateFrom` answers with the key itself when no bundle is registered yet — an isolated
    // component test, or a render before the plugin's `register` runs. The English template is the
    // better fallback there, so `Current` never degrades into `current`.
    const resolved = t(key)

    out[key] = resolved === key ? value : resolved
  }

  return out as Bound<Messages>
}

export function useFreeModels(): Bound<Messages> {
  const t = usePluginI18n('free-model-suite')

  return useMemo(() => bind(t, en), [t])
}

const ja = {
  ...en,
  apply: '適用',
  applying: '適用中…',
  close: '閉じる',
  current: '現在',
  description: (count: number) => `このプロファイルに接続済みのプロバイダーから無料モデル ${count} 件を表示します。`,
  empty: '無料モデルが見つかりません',
  emptyHelp: '設定でプロバイダーを接続してから、このページを更新してください。',
  failed: '無料モデルのテストに失敗しました',
  freeTier: '無料枠',
  noResults: '検索条件に一致する無料モデルはありません',
  open: '無料モデル: 開く',
  probe: 'モデルをテスト',
  probeApply: 'テスト後に適用',
  reply: '返信',
  run: 'テスト',
  running: 'テスト中…',
  search: 'モデルまたはプロバイダーを検索…',
  stealth: 'ステルス',
  stealthNote:
    '名称未公開のプレビュー SKU。慣例的に無料ですが、プロバイダーが予告なく入れ替えます — 切り替える前にテストしてください。',
  switchFailed: 'モデルを適用できませんでした',
  switched: '既定モデルを更新しました',
  test: 'テスト',
  title: '無料モデルスイート',
  truncated: 'トークン上限に達したため、返信が不完全な可能性があります。'
}

const zh = {
  ...en,
  apply: '应用',
  applying: '应用中…',
  close: '关闭',
  current: '当前',
  description: (count: number) => `浏览此配置文件中已连接提供商提供的 ${count} 个免费模型。`,
  empty: '未找到免费模型',
  emptyHelp: '请先在设置中连接提供商，然后刷新此页面。',
  failed: '免费模型测试失败',
  freeTier: '免费额度',
  noResults: '没有免费模型符合搜索条件',
  open: '免费模型：打开',
  probe: '测试模型',
  probeApply: '测试后应用',
  reply: '回复',
  run: '测试',
  running: '测试中…',
  search: '搜索模型或提供商…',
  stealth: '隐身',
  stealthNote: '未公开名称的预览 SKU。按惯例免费,但提供商会随时替换 — 切换前请先测试。',
  switchFailed: '无法应用模型',
  switched: '默认模型已更新',
  test: '测试',
  title: '免费模型套件',
  truncated: '回复达到令牌上限，可能不完整。'
}

const zhHant = {
  ...zh,
  apply: '套用',
  applying: '套用中…',
  close: '關閉',
  current: '目前',
  description: (count: number) => `瀏覽此設定檔中已連線供應商提供的 ${count} 個免費模型。`,
  empty: '找不到免費模型',
  emptyHelp: '請先在設定中連線供應商，再重新整理此頁面。',
  failed: '免費模型測試失敗',
  freeTier: '免費額度',
  noResults: '沒有免費模型符合搜尋條件',
  open: '免費模型：開啟',
  search: '搜尋模型或供應商…',
  stealth: '隱身',
  stealthNote: '未公開名稱的預覽 SKU。依慣例免費,但供應商會隨時替換 — 切換前請先測試。',
  switchFailed: '無法套用模型',
  switched: '預設模型已更新',
  test: '測試',
  title: '免費模型套件',
  truncated: '回覆已達權杖上限，可能不完整。'
}

export const FREE_MODEL_SUITE_LOCALES: PluginLocaleBundles = {
  en,
  ja,
  zh,
  'zh-hant': zhHant
}
