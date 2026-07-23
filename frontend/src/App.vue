<script setup>
import { computed, nextTick, onMounted, reactive, ref, watch } from 'vue'
import { call, getApi, onEvent } from './bridge'
import { THEMES, applyTheme, loadThemeId } from './themes'
import { APP_DISPLAY, APP_NAME, APP_NAME_EN, APP_VERSION } from './version'
import { vgConfirm } from './ui/dialog'
/** @type {import('vue').Ref<'dub'|'voices'|'settings'>} */
const page = ref('dub')

const navItems = [
  { id: 'dub', label: '配音', desc: '脚本表格、翻译与生成 MP3', icon: 'mic' },
  { id: 'voices', label: '音色', desc: '本地参考音色库', icon: 'voice' },
  { id: 'settings', label: '设置', desc: 'API、模型与外观', icon: 'setting' },
]

const themes = THEMES
const themeId = ref(loadThemeId())
const appVersion = ref(APP_VERSION)
const appDisplay = ref(APP_DISPLAY)
const appName = APP_NAME
const appNameEn = APP_NAME_EN

/** 配音表格列显示（本地记忆） */
const COL_STORAGE_KEY = 'voicegen_table_columns_v1'
const TABLE_COLUMN_DEFS = [
  { key: 'check', label: '选用', locked: true },
  { key: 'idx', label: '序号', locked: true },
  { key: 'speaker', label: '角色' },
  { key: 'voice', label: '音色' },
  { key: 'text', label: '原文' },
  { key: 'tts_text', label: '配音文本' },
  { key: 'speed', label: '语速' },
  { key: 'style', label: '风格' },
  { key: 'status', label: '状态' },
  { key: 'ops', label: '操作', locked: true },
]

function defaultColumnVisibility() {
  const o = {}
  for (const c of TABLE_COLUMN_DEFS) o[c.key] = true
  return o
}

function loadColumnVisibility() {
  const base = defaultColumnVisibility()
  try {
    const raw = localStorage.getItem(COL_STORAGE_KEY)
    if (!raw) return base
    const parsed = JSON.parse(raw)
    if (parsed && typeof parsed === 'object') {
      for (const c of TABLE_COLUMN_DEFS) {
        if (c.locked) base[c.key] = true
        else if (typeof parsed[c.key] === 'boolean') base[c.key] = parsed[c.key]
      }
    }
  } catch {
    /* ignore */
  }
  return base
}

const colVisible = reactive(loadColumnVisibility())
const colMenuOpen = ref(false)

function saveColumnVisibility() {
  try {
    const payload = {}
    for (const c of TABLE_COLUMN_DEFS) {
      payload[c.key] = c.locked ? true : Boolean(colVisible[c.key])
    }
    localStorage.setItem(COL_STORAGE_KEY, JSON.stringify(payload))
  } catch {
    /* ignore */
  }
}

function setColumnVisible(key, visible) {
  const def = TABLE_COLUMN_DEFS.find((c) => c.key === key)
  if (!def || def.locked) return
  colVisible[key] = Boolean(visible)
  // 至少保留原文或配音文本之一
  if (!colVisible.text && !colVisible.tts_text) {
    if (key === 'text') colVisible.tts_text = true
    else colVisible.text = true
  }
  saveColumnVisibility()
}

function resetColumns() {
  Object.assign(colVisible, defaultColumnVisibility())
  saveColumnVisibility()
}

function isCol(key) {
  return colVisible[key] !== false
}

const voices = ref([])
const voicesDir = ref('')
const languages = ref([])
const rows = ref([])
const config = reactive({
  api_key_set: false,
  api_key_masked: '',
  base_url: 'https://token-plan-cn.xiaomimimo.com/v1',
  model: 'mimo-v2.5-tts-voiceclone',
  llm_model: 'mimo-v2.5-pro',
  default_style: '自然清晰的配音，语气符合角色与语境。',
  default_speed: 1.0,
  gap_ms: 200,
  source_lang: 'zh-CN',
  target_lang: 'en-US',
  tts_workers: 4,
  translate_workers: 3,
  translate_batch_size: 8,
})

const settingsForm = reactive({
  api_key: '',
  base_url: '',
  model: '',
  llm_model: '',
  default_style: '',
  default_speed: 1.0,
  gap_ms: 200,
  source_lang: 'zh-CN',
  target_lang: 'en-US',
  tts_workers: 4,
  translate_workers: 3,
  translate_batch_size: 8,
})

const apiStatus = ref('unknown')
const apiStatusMsg = ref('')
const generating = ref(false)
const translating = ref(false)
const progress = reactive({
  index: 0,
  total: 0,
  status: '',
  message: '',
})
const lastOutput = ref(null)
const toast = ref(null)
const playingId = ref(null)
/** @type {HTMLAudioElement | null} */
let audioEl = null
let toastTimer = null

const pageTitle = computed(() => navItems.find((n) => n.id === page.value)?.label || 'VoiceGen')
const pageDesc = computed(() => navItems.find((n) => n.id === page.value)?.desc || '')

function showToast(message, type = 'info') {
  toast.value = { message, type }
  clearTimeout(toastTimer)
  toastTimer = setTimeout(() => {
    toast.value = null
  }, 3200)
  // mirror important UI messages into backend daily logs
  const level = type === 'error' ? 'error' : type === 'success' ? 'info' : 'info'
  call('client_log', level, String(message || ''), { source: 'toast', type })
}

function uiLog(level, message, context) {
  call('client_log', level || 'info', String(message || ''), context || {})
}

const progressPct = computed(() => {
  if (!progress.total) return 0
  if (progress.status === 'merging') return 96
  if (progress.status === 'done') return 100
  return Math.min(95, Math.round((progress.index / progress.total) * 100))
})

function speakText(row) {
  const tts = String(row?.tts_text || '').trim()
  if (tts) return tts
  return String(row?.text || '').trim()
}

const enabledCount = computed(
  () => rows.value.filter((r) => r.enabled && speakText(r)).length,
)

const allSelected = computed(
  () => rows.value.length > 0 && rows.value.every((r) => r.enabled),
)

function toggleSelectAll(checked) {
  const next = typeof checked === 'boolean' ? checked : !allSelected.value
  for (const row of rows.value) {
    row.enabled = next
  }
}

const translatedCount = computed(
  () => rows.value.filter((r) => r.enabled && String(r.tts_text || '').trim()).length,
)

const sourceCount = computed(
  () => rows.value.filter((r) => r.enabled && String(r.text || '').trim()).length,
)

const sameLang = computed(() => config.source_lang === config.target_lang)

const languageOptions = computed(() =>
  (languages.value || []).map((l) => ({
    value: l.code,
    label: `${l.name} · ${l.native}`,
  })),
)

const languageOptionsShort = computed(() =>
  (languages.value || []).map((l) => ({
    value: l.code,
    label: l.name,
  })),
)

const voiceOptions = computed(() =>
  (voices.value || []).map((v) => ({
    value: v.id,
    label: v.name,
  })),
)

const apiBadgeTone = computed(() => {
  if (apiStatus.value === 'ok') return 'ok'
  if (apiStatus.value === 'error') return 'warn'
  return ''
})

function blankRow(partial = {}) {
  return {
    id: Math.random().toString(36).slice(2, 10),
    speaker: '',
    voice: voices.value[0]?.id || '',
    text: '',
    tts_text: '',
    speed: config.default_speed || 1.0,
    style: '',
    enabled: true,
    status: 'idle',
    duration: null,
    error: '',
    segment_path: '',
    ...partial,
  }
}

function langLabel(code) {
  const item = languages.value.find((l) => l.code === code)
  if (!item) return code
  return item.native && item.native !== item.name ? `${item.name} · ${item.native}` : item.name
}

function go(id) {
  page.value = id
  if (id === 'settings') syncSettingsForm()
}

async function persistLangs() {
  await call('save_config', {
    source_lang: config.source_lang,
    target_lang: config.target_lang,
  })
}

async function refreshVoices() {
  const res = await call('list_voices')
  if (!res.ok) {
    showToast(res.error || '读取音色失败', 'error')
    return
  }
  voices.value = res.data.voices || []
  voicesDir.value = res.data.voices_dir || ''
}

async function refreshLanguages() {
  const res = await call('list_languages')
  if (res.ok) languages.value = res.data.languages || []
}

async function refreshConfig() {
  const res = await call('get_config')
  if (!res.ok) return
  Object.assign(config, res.data || {})
  apiStatus.value = config.api_key_set ? 'unknown' : 'error'
  apiStatusMsg.value = config.api_key_set ? '未检测' : '未配置 API Key'
  syncSettingsForm()
}

function syncSettingsForm() {
  settingsForm.api_key = ''
  settingsForm.base_url = config.base_url
  settingsForm.model = config.model
  settingsForm.llm_model = config.llm_model
  settingsForm.default_style = config.default_style
  settingsForm.default_speed = config.default_speed
  settingsForm.gap_ms = config.gap_ms
  settingsForm.source_lang = config.source_lang
  settingsForm.target_lang = config.target_lang
  settingsForm.tts_workers = config.tts_workers ?? 4
  settingsForm.translate_workers = config.translate_workers ?? 3
  settingsForm.translate_batch_size = config.translate_batch_size ?? 8
}

async function loadProject() {
  const res = await call('load_project')
  if (res.ok) {
    if (res.data?.source_lang) config.source_lang = res.data.source_lang
    if (res.data?.target_lang) config.target_lang = res.data.target_lang
    if (res.data?.rows?.length) {
      rows.value = res.data.rows.map((r) => blankRow(r))
      return
    }
  }
  if (!rows.value.length) {
    rows.value = [
      blankRow({ speaker: '旁白', text: '欢迎使用 VoiceGen 多人配音工具。' }),
      blankRow({ speaker: '角色A', text: '把音色样本放到 voices 文件夹，即可在这里选择。' }),
    ]
  }
}

async function saveProject() {
  const res = await call('save_project', rows.value, {
    source_lang: config.source_lang,
    target_lang: config.target_lang,
  })
  if (res.ok) showToast('项目已保存', 'success')
  else showToast(res.error || '保存失败', 'error')
}

function addRow() {
  rows.value.push(blankRow())
}

function insertRow(index) {
  rows.value.splice(index + 1, 0, blankRow())
}

function removeRow(index) {
  rows.value.splice(index, 1)
  if (!rows.value.length) addRow()
}

function moveRow(index, delta) {
  const next = index + delta
  if (next < 0 || next >= rows.value.length) return
  const copy = rows.value.slice()
  const [item] = copy.splice(index, 1)
  copy.splice(next, 0, item)
  rows.value = copy
}

async function saveSettings() {
  const updates = {
    base_url: settingsForm.base_url.trim() || config.base_url,
    model: settingsForm.model.trim() || config.model,
    llm_model: settingsForm.llm_model.trim() || config.llm_model,
    default_style: settingsForm.default_style,
    default_speed: Number(settingsForm.default_speed) || 1.0,
    gap_ms: Number(settingsForm.gap_ms) || 0,
    source_lang: settingsForm.source_lang || config.source_lang,
    target_lang: settingsForm.target_lang || config.target_lang,
    tts_workers: Math.max(1, Math.min(12, Number(settingsForm.tts_workers) || 4)),
    translate_workers: Math.max(1, Math.min(8, Number(settingsForm.translate_workers) || 3)),
    translate_batch_size: Math.max(1, Math.min(30, Number(settingsForm.translate_batch_size) || 8)),
  }
  if (settingsForm.api_key.trim()) {
    updates.api_key = settingsForm.api_key.trim()
  }
  const res = await call('save_config', updates)
  if (!res.ok) {
    showToast(res.error || '保存失败', 'error')
    return
  }
  Object.assign(config, res.data || {})
  settingsForm.api_key = ''
  showToast('设置已保存', 'success')
  await checkApi()
}

/**
 * @param {{ silent?: boolean }} [options]
 * silent: 启动自动检测时用，成功不弹 toast，失败仍提示
 */
async function checkApi(options = {}) {
  const silent = Boolean(options.silent)
  apiStatus.value = 'unknown'
  apiStatusMsg.value = '检测中…'
  const res = await call('check_api')
  if (res.ok) {
    apiStatus.value = 'ok'
    const tts = res.data?.tts?.model || config.model
    const llm = res.data?.llm?.model || config.llm_model
    apiStatusMsg.value = 'TTS+LLM 就绪'
    if (!silent) {
      showToast(`API 就绪 · TTS ${tts} · LLM ${llm}`, 'success')
    }
    return true
  }
  apiStatus.value = 'error'
  apiStatusMsg.value = res.error || '检测失败'
  showToast(res.error || 'API 检测失败', 'error')
  return false
}

/** 启动时若已配置 Key 则自动检测 */
async function autoCheckApiOnBoot() {
  // 等 pywebview 桥接就绪（最长 8s）
  await getApi()
  await refreshConfig()
  if (!config.api_key_set) {
    apiStatus.value = 'error'
    apiStatusMsg.value = '未配置 API Key'
    return
  }
  await checkApi({ silent: true })
}

async function importVoice() {
  const res = await call('pick_voice_file')
  if (!res.ok) {
    showToast(res.error || '导入失败', 'error')
    return
  }
  if (!res.data) return
  await refreshVoices()
  showToast(`已导入音色：${res.data.name}`, 'success')
}

async function deleteVoice(id) {
  const ok = await vgConfirm({
    title: '删除音色',
    message: `确定删除音色「${id}」？此操作不可恢复。`,
    confirmText: '删除',
    cancelText: '取消',
    tone: 'danger',
  })
  if (!ok) return
  const res = await call('delete_voice', id)
  if (!res.ok) {
    showToast(res.error || '删除失败', 'error')
    return
  }
  await refreshVoices()
  showToast('音色已删除', 'success')
}

async function openVoicesFolder() {
  await call('open_voices_folder')
}

async function importTable() {
  const res = await call('pick_import_file')
  if (!res.ok) {
    showToast(res.error || '导入失败', 'error')
    return
  }
  if (!res.data) return
  rows.value = (res.data.rows || []).map((r) => blankRow(r))
  if (res.data.source_lang) config.source_lang = res.data.source_lang
  if (res.data.target_lang) config.target_lang = res.data.target_lang
  if (!rows.value.length) rows.value = [blankRow()]
  showToast(`已导入 ${rows.value.length} 行`, 'success')
}

async function exportTable(fmt = 'csv') {
  const res = await call(
    'save_export_file',
    rows.value,
    fmt,
    { source_lang: config.source_lang, target_lang: config.target_lang },
  )
  if (!res.ok) {
    showToast(res.error || '导出失败', 'error')
    return
  }
  if (!res.data) return
  showToast(`已导出：${res.data.path}`, 'success')
}

/** 导出空白/示例表格模板（CSV），便于填写后导入 */
async function exportTableTemplate() {
  // 表头由后端 export_csv 使用中文：角色,音色,原文,配音文本,语速,风格,启用
  const templateRows = [
    {
      speaker: '旁白',
      voice: '',
      text: '在此填写原文台词',
      tts_text: '',
      speed: 1.0,
      style: '',
      enabled: true,
    },
    {
      speaker: '角色A',
      voice: '',
      text: '',
      tts_text: '',
      speed: 1.0,
      style: '',
      enabled: true,
    },
    {
      speaker: '角色B',
      voice: '',
      text: '',
      tts_text: '',
      speed: 1.0,
      style: '',
      enabled: true,
    },
  ]
  const res = await call(
    'save_export_file',
    templateRows,
    'csv',
    {
      source_lang: config.source_lang,
      target_lang: config.target_lang,
      is_template: true,
    },
  )
  if (!res.ok) {
    showToast(res.error || '导出模板失败', 'error')
    return
  }
  if (!res.data) return
  showToast(`已导出模板：${res.data.path}`, 'success')
}

/** 一键清空整表（保留一行空行） */
async function clearAllRows() {
  if (!rows.value.length) {
    rows.value = [blankRow()]
    return
  }
  const hasContent = rows.value.some(
    (r) => String(r.text || '').trim() || String(r.tts_text || '').trim() || String(r.speaker || '').trim(),
  )
  if (hasContent) {
    const ok = await vgConfirm({
      title: '清空整表',
      message: '确定清空整表？当前台词与译文将全部删除。',
      confirmText: '清空',
      cancelText: '取消',
      tone: 'danger',
    })
    if (!ok) return
  }
  stopPlayback()
  rows.value = [blankRow()]
  showToast('已清空表格', 'success')
  call('save_project', rows.value, {
    source_lang: config.source_lang,
    target_lang: config.target_lang,
  })
}

function applyTranslationResults(results) {
  if (!results?.length) return
  const map = new Map(results.map((r) => [String(r.id), r.tts_text]))
  let updated = 0
  for (const row of rows.value) {
    if (map.has(String(row.id))) {
      row.tts_text = map.get(String(row.id))
      updated += 1
    }
  }
  if (updated) {
    nextTick(() => resizeAllTextareas())
  }
}

async function runTranslate(mode) {
  if (translating.value || generating.value) return
  const count = rows.value.filter((r) => r.enabled && String(r.text || '').trim()).length
  if (!count) {
    showToast('没有可翻译的原文行', 'error')
    return
  }
  uiLog('info', mode === 'localize' ? '用户点击本土化翻译' : '用户点击直译', {
    mode,
    count,
    source_lang: config.source_lang,
    target_lang: config.target_lang,
  })
  translating.value = true
  progress.message =
    mode === 'localize'
      ? `本土化翻译中（${langLabel(config.source_lang)} → ${langLabel(config.target_lang)}）…`
      : `直译中（${langLabel(config.source_lang)} → ${langLabel(config.target_lang)}）…`
  progress.status = 'translating'
  const res = await call(
    'translate_rows',
    rows.value,
    mode,
    config.source_lang,
    config.target_lang,
    true,
  )
  if (!res.ok) {
    translating.value = false
    showToast(res.error || '翻译失败', 'error')
    progress.message = res.error || '翻译失败'
    progress.status = 'error'
  }
}

async function copySourceToTts() {
  for (const row of rows.value) {
    if (!row.enabled) continue
    const text = String(row.text || '').trim()
    if (text) row.tts_text = text
  }
  showToast('已将原文复制到配音文本', 'success')
}

async function clearTtsText() {
  for (const row of rows.value) {
    row.tts_text = ''
  }
  showToast('已清空配音文本', 'success')
}

async function startGenerate() {
  if (generating.value || translating.value) return
  if (!enabledCount.value) {
    showToast('没有可生成的行（需有原文或配音文本）', 'error')
    return
  }
  uiLog('info', '用户点击生成全部 MP3', { count: enabledCount.value, workers: config.tts_workers })
  for (const row of rows.value) {
    if (row.enabled && speakText(row)) {
      row.status = 'idle'
      row.error = ''
      row.duration = null
      row.segment_path = ''
    }
  }
  lastOutput.value = null
  progress.index = 0
  progress.total = enabledCount.value
  progress.status = 'starting'
  progress.message = '准备中…'
  generating.value = true

  const res = await call('generate_all', rows.value, {
    gap_ms: config.gap_ms,
    default_style: config.default_style,
    only_enabled: true,
    stop_on_error: false,
    target_lang: config.target_lang,
    tts_workers: config.tts_workers || 4,
    skip_final_merge: false,
  })
  if (!res.ok) {
    generating.value = false
    showToast(res.error || '启动失败', 'error')
  }
}

/** 单条重新生成（不合并整轨 MP3） */
async function regenerateRow(row) {
  if (generating.value || translating.value) return
  if (!speakText(row)) {
    showToast('该行没有可配音文本', 'error')
    return
  }
  if (!String(row.voice || '').trim()) {
    showToast('请先为该行选择音色', 'error')
    return
  }
  stopPlayback()
  row.status = 'idle'
  row.error = ''
  row.duration = null
  row.segment_path = ''
  progress.index = 0
  progress.total = 1
  progress.status = 'starting'
  progress.message = `重新生成：${row.speaker || ''} ${speakText(row).slice(0, 40)}`
  generating.value = true

  const one = { ...row, enabled: true }
  const res = await call('generate_all', [one], {
    gap_ms: config.gap_ms,
    default_style: config.default_style,
    only_enabled: true,
    stop_on_error: false,
    target_lang: config.target_lang,
    tts_workers: 1,
    skip_final_merge: true,
  })
  if (!res.ok) {
    generating.value = false
    showToast(res.error || '重新生成失败', 'error')
  }
}

async function cancelGenerate() {
  await call('cancel_generate')
  showToast('正在取消…')
}

async function openOutput() {
  if (lastOutput.value?.output) {
    await call('reveal_file', lastOutput.value.output)
  } else {
    await call('open_output_folder')
  }
}

function applyEvent(event, payload) {
  if (event === 'translate_start') {
    translating.value = true
    progress.status = 'translating'
    const modeLabel = payload.mode === 'localize' ? '本土化' : '直译'
    progress.message = `${modeLabel}中（${payload.source_lang} → ${payload.target_lang}）…`
  } else if (event === 'translate_progress') {
    translating.value = true
    progress.status = 'translating'
    progress.index = payload.done || 0
    progress.total = payload.total || progress.total
    progress.message =
      payload.message ||
      `翻译中 ${payload.done || 0}/${payload.total || 0}（批次 ${payload.batch}/${payload.total_batches}）`
    // 每批完成立即写入配音文本列
    if (payload.results?.length) {
      applyTranslationResults(payload.results)
    }
  } else if (event === 'translate_done') {
    translating.value = false
    // 兜底再合并一次全部结果
    applyTranslationResults(payload.results || [])
    const n = payload.count ?? payload.results?.length ?? 0
    const modeLabel = payload.mode === 'localize' ? '本土化' : '直译'
    progress.status = 'idle'
    progress.index = n
    progress.total = n
    progress.message = payload.note || `${modeLabel}完成 ${n} 行`
    showToast(
      payload.note || `${modeLabel}完成 ${n} 行 · ${payload.model || config.llm_model}`,
      'success',
    )
    call('save_project', rows.value, {
      source_lang: config.source_lang,
      target_lang: config.target_lang,
    })
    resizeAllTextareas()
  } else if (event === 'translate_error') {
    translating.value = false
    progress.status = 'error'
    progress.message = payload.error || '翻译失败'
    showToast(payload.error || '翻译失败', 'error')
  } else if (event === 'generate_start') {
    generating.value = true
    progress.total = payload.total || 0
    progress.index = 0
    progress.status = 'running'
    const w = payload.workers || config.tts_workers || 4
    progress.message = `共 ${payload.total} 段 · ${w} 线程并发`
  } else if (event === 'generate_progress') {
    progress.index = (payload.index ?? 0) + (payload.status === 'done' || payload.status === 'error' ? 1 : 0)
    progress.total = payload.total || progress.total
    progress.status = payload.status || 'running'
    if (payload.status === 'merging') {
      progress.message = '正在合并 MP3…'
    } else if (payload.text) {
      progress.message = `生成中：${payload.speaker || ''} ${payload.text}`
    } else if (payload.error) {
      progress.message = payload.error
    }
    if (payload.row_id) {
      const row = rows.value.find((r) => r.id === payload.row_id)
      if (row) {
        if (payload.status === 'running' || payload.status === 'done' || payload.status === 'error') {
          row.status = payload.status
        }
        if (payload.duration != null) row.duration = payload.duration
        if (payload.segment_path) row.segment_path = payload.segment_path
        if (payload.error) row.error = payload.error
      }
    }
  } else if (event === 'generate_done') {
    generating.value = false
    progress.status = 'done'
    progress.index = progress.total
    // Apply per-row results (full batch or single regen)
    for (const item of payload.results || []) {
      const row = rows.value.find((r) => r.id === item.row_id)
      if (!row) continue
      if (item.status) row.status = item.status
      if (item.duration != null) row.duration = item.duration
      if (item.segment_path) row.segment_path = item.segment_path
      if (item.error) row.error = item.error
    }
    if (payload.skip_final_merge) {
      progress.message = `单条生成完成 · ${Number(payload.duration || 0).toFixed(1)}s`
      showToast('单条重新生成完成，可点试听', 'success')
    } else {
      progress.message = `完成 · ${Number(payload.duration || 0).toFixed(1)}s`
      lastOutput.value = payload
      showToast('配音完成，已导出 MP3', 'success')
    }
    call('save_project', rows.value, {
      source_lang: config.source_lang,
      target_lang: config.target_lang,
    })
  } else if (event === 'generate_error') {
    generating.value = false
    progress.status = 'error'
    progress.message = payload.error || '生成失败'
    showToast(payload.error || '生成失败', 'error')
  } else if (event === 'generate_cancelled') {
    generating.value = false
    progress.status = 'cancelled'
    progress.message = '已取消'
    showToast('已取消生成')
  }
}

function formatDuration(sec) {
  if (sec == null || sec === '') return '—'
  const n = Number(sec)
  if (Number.isNaN(n)) return '—'
  return `${n.toFixed(1)}s`
}

function formatFileSize(bytes) {
  const n = Number(bytes) || 0
  if (n < 1024) return `${n} B`
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`
  return `${(n / (1024 * 1024)).toFixed(2)} MB`
}

function statusLabel(status) {
  return (
    {
      idle: '待生成',
      running: '生成中',
      done: '完成',
      error: '失败',
    }[status] || status || '待生成'
  )
}

function swapLangs() {
  const a = config.source_lang
  config.source_lang = config.target_lang
  config.target_lang = a
  persistLangs()
}

function setTheme(id) {
  themeId.value = applyTheme(id)
  showToast(`已切换主题：${themes.find((t) => t.id === id)?.name || id}`, 'success')
}

/** Auto-grow textarea height with content */
function autoResizeTextarea(el) {
  if (!el || el.tagName !== 'TEXTAREA') return
  el.style.height = 'auto'
  const max = 280
  const next = Math.min(Math.max(el.scrollHeight, 40), max)
  el.style.height = `${next}px`
  el.style.overflowY = el.scrollHeight > max ? 'auto' : 'hidden'
}

function onTextareaInput(e) {
  autoResizeTextarea(e?.target)
}

function resizeAllTextareas() {
  nextTick(() => {
    document.querySelectorAll('table.script textarea.auto-h').forEach((el) => {
      autoResizeTextarea(el)
    })
  })
}

function stopPlayback() {
  if (audioEl) {
    audioEl.pause()
    audioEl.onended = null
    audioEl.onerror = null
    audioEl.src = ''
  }
  playingId.value = null
}

async function playAudioPath(path, playKey) {
  if (!path) {
    showToast('没有可试听的音频', 'error')
    return
  }
  // Toggle pause if same item
  if (playingId.value === playKey && audioEl && !audioEl.paused) {
    audioEl.pause()
    playingId.value = null
    return
  }
  stopPlayback()
  const res = await call('get_audio_data_url', path)
  if (!res.ok) {
    showToast(res.error || '读取音频失败', 'error')
    return
  }
  if (!audioEl) audioEl = new Audio()
  audioEl.src = res.data.url
  audioEl.onended = () => {
    playingId.value = null
  }
  audioEl.onerror = () => {
    playingId.value = null
    showToast('播放失败', 'error')
  }
  try {
    await audioEl.play()
    playingId.value = playKey
  } catch (err) {
    playingId.value = null
    showToast(err?.message || '无法播放', 'error')
  }
}

async function playRow(row) {
  if (!row?.segment_path || row.status !== 'done') {
    showToast('该行尚未生成成功，无法试听', 'error')
    return
  }
  await playAudioPath(row.segment_path, row.id)
}

/** 音色库参考音频试听 */
async function playVoice(voice) {
  if (!voice?.path) {
    showToast('音色文件路径无效', 'error')
    return
  }
  await playAudioPath(voice.path, `voice:${voice.id}`)
}

watch(
  rows,
  () => {
    resizeAllTextareas()
  },
  { deep: true },
)

async function refreshVersion() {
  const res = await call('get_version')
  if (res.ok && res.data?.version) {
    appVersion.value = res.data.version
    appDisplay.value = res.data.display || `${APP_NAME} v${res.data.version}`
  }
}

function onDocCloseColMenu(e) {
  if (!colMenuOpen.value) return
  const wrap = e.target?.closest?.('.col-menu-wrap')
  if (!wrap) colMenuOpen.value = false
}

onMounted(async () => {
  themeId.value = applyTheme(loadThemeId())
  onEvent(applyEvent)
  document.addEventListener('mousedown', onDocCloseColMenu)
  apiStatusMsg.value = '初始化…'
  uiLog('info', 'UI 挂载完成', { page: page.value, theme: themeId.value })
  await refreshVersion()
  await refreshConfig()
  await refreshLanguages()
  await refreshVoices()
  await loadProject()
  resizeAllTextareas()
  // 已配置 API Key 时启动自动检测 TTS + 翻译模型
  await autoCheckApiOnBoot()
  const st = await call('get_runtime_status')
  if (st.ok) {
    uiLog('info', '运行时状态', {
      ffmpeg: st.data?.ffmpeg?.ffmpeg || null,
      ffprobe: st.data?.ffmpeg?.ffprobe || null,
      bundled: st.data?.ffmpeg?.bundled,
      log_dir: st.data?.log_dir,
    })
  }
})
</script>
<template>
  <div class="app" :data-theme="themeId">
    <aside class="nav-drawer">
      <div class="nav-brand">
        <div class="logo">VG</div>
        <div class="nav-brand-text">
          <strong>{{ appNameEn }}</strong>
          <span>{{ appName }}</span>
        </div>
      </div>

      <nav class="nav-list">
        <div class="nav-section-label">工作区</div>
        <button
          v-for="item in navItems"
          :key="item.id"
          type="button"
          class="nav-item"
          :class="{ active: page === item.id }"
          @click="go(item.id)"
        >
          <span class="nav-icon">
            <AliIcon :name="item.icon" :size="15" />
          </span>
          <span class="nav-item-text">
            <span class="nav-item-label">{{ item.label }}</span>
            <span class="nav-item-desc">{{ item.desc }}</span>
          </span>
        </button>
      </nav>

      <div class="nav-footer">
        <div class="theme-mini" title="马卡龙换肤">
          <button
            v-for="t in themes"
            :key="'mini-' + t.id"
            type="button"
            class="theme-dot"
            :class="{ active: themeId === t.id }"
            :title="t.name"
            :style="{ background: t.swatch[2] }"
            @click="setTheme(t.id)"
          />
        </div>
        <VgBadge :tone="apiBadgeTone" dot>{{ apiStatusMsg || 'API' }}</VgBadge>
        <div class="nav-footer-meta">{{ langLabel(config.source_lang) }} → {{ langLabel(config.target_lang) }}</div>
        <div class="nav-version" :title="appDisplay">v{{ appVersion }}</div>
      </div>
    </aside>

    <main class="workspace">
      <header class="header">
        <div class="brand">
          <div>
            <h1>{{ pageTitle }}</h1>
            <p>{{ pageDesc }}</p>
          </div>
        </div>
        <div class="header-actions">
          <template v-if="page === 'dub'">
            <VgButton variant="ghost" icon="save" :icon-size="15" title="保存项目" @click="saveProject">保存</VgButton>
            <VgButton v-if="generating" variant="danger" icon="stop" :icon-size="15" @click="cancelGenerate">取消</VgButton>
            <VgButton
              variant="primary"
              icon="play"
              :icon-size="15"
              :disabled="generating || translating || !enabledCount"
              @click="startGenerate"
            >
              {{ generating ? '生成中…' : `生成 MP3（${enabledCount}）` }}
            </VgButton>
          </template>
          <template v-else-if="page === 'voices'">
            <VgButton variant="ghost" icon="folder" :icon-size="15" @click="openVoicesFolder">打开目录</VgButton>
            <VgButton variant="ghost" icon="refresh" :icon-size="15" @click="refreshVoices">刷新</VgButton>
            <VgButton variant="primary" icon="upload" :icon-size="15" @click="importVoice">导入音色</VgButton>
          </template>
          <template v-else-if="page === 'settings'">
            <VgButton variant="ghost" icon="link" :icon-size="15" @click="checkApi()">检测 API</VgButton>
            <VgButton variant="ghost" icon="refresh" :icon-size="15" @click="syncSettingsForm">重置</VgButton>
          </template>
        </div>
      </header>

      <!-- 配音页 -->
      <section v-if="page === 'dub'" class="page page-dub">
        <div class="toolbar toolbar-wrap">
          <div class="toolbar-group">
            <VgButton size="sm" icon="plus" :icon-size="14" @click="addRow">添加行</VgButton>
            <VgButton size="sm" icon="import" :icon-size="14" title="从文件导入台词表" @click="importTable">导入表格</VgButton>
            <VgButton size="sm" icon="export" :icon-size="14" title="导出当前表格为文件" @click="exportTable('csv')">导出表格</VgButton>
            <VgButton size="sm" variant="ghost" icon="export" :icon-size="14" title="导出 JSON 格式" @click="exportTable('json')">导出 JSON</VgButton>
            <VgButton
              size="sm"
              variant="ghost"
              icon="export"
              :icon-size="14"
              title="导出空白示例表格，填写后可再导入"
              @click="exportTableTemplate"
            >
              导出模板
            </VgButton>
            <VgButton
              size="sm"
              variant="danger"
              icon="clear"
              :icon-size="14"
              title="清空整表"
              @click="clearAllRows"
            >
              一键清空
            </VgButton>
            <VgButton size="sm" variant="ghost" icon="folder" :icon-size="14" @click="openOutput">输出目录</VgButton>
            <div class="col-menu-wrap">
              <VgButton
                size="sm"
                variant="ghost"
                icon="setting"
                :icon-size="14"
                title="显示 / 隐藏表格列"
                @click="colMenuOpen = !colMenuOpen"
              >
                显示列
              </VgButton>
              <div v-if="colMenuOpen" class="col-menu" @mousedown.stop>
                <div class="col-menu-title">表格列显示</div>
                <label
                  v-for="c in TABLE_COLUMN_DEFS"
                  :key="c.key"
                  class="col-menu-item"
                  :class="{ locked: c.locked }"
                >
                  <input
                    type="checkbox"
                    :checked="isCol(c.key)"
                    :disabled="c.locked"
                    @change="setColumnVisible(c.key, $event.target.checked)"
                  />
                  <span>{{ c.label }}</span>
                  <span v-if="c.locked" class="col-menu-tag">固定</span>
                </label>
                <div class="col-menu-actions">
                  <VgButton size="sm" variant="ghost" @click="resetColumns">全部显示</VgButton>
                  <VgButton size="sm" variant="ghost" @click="colMenuOpen = false">关闭</VgButton>
                </div>
              </div>
            </div>
          </div>

          <div class="toolbar-group lang-toolbar">
            <VgSelect
              v-model="config.source_lang"
              :options="languageOptionsShort"
              size="sm"
              inline
              searchable
              placeholder="源语言"
              @change="persistLangs"
            />
            <VgButton size="sm" variant="ghost" icon="swap" :icon-size="14" icon-only title="交换语言" @click="swapLangs" />
            <VgSelect
              v-model="config.target_lang"
              :options="languageOptionsShort"
              size="sm"
              inline
              searchable
              placeholder="目标语言"
              @change="persistLangs"
            />
            <VgButton
              size="sm"
              variant="primary"
              icon="translate"
              :icon-size="14"
              :disabled="translating || generating"
              title="忠实直译到目标语言"
              @click="runTranslate('literal')"
            >
              {{ translating ? '翻译中…' : '直译' }}
            </VgButton>
            <VgButton
              size="sm"
              variant="primary"
              icon="global"
              :icon-size="14"
              :disabled="translating || generating"
              title="本土化翻译"
              @click="runTranslate('localize')"
            >
              本土化
            </VgButton>
            <VgButton
              size="sm"
              variant="ghost"
              icon="copy"
              :icon-size="14"
              :disabled="translating || generating"
              title="复制原文到配音文本"
              @click="copySourceToTts"
            >
              复制原文
            </VgButton>
            <VgButton
              size="sm"
              variant="ghost"
              icon="clear"
              :icon-size="14"
              :disabled="translating || generating"
              title="清空配音文本"
              @click="clearTtsText"
            >
              清空译文
            </VgButton>
            <VgBadge v-if="translatedCount">已译 {{ translatedCount }}</VgBadge>
          </div>
        </div>

        <div class="table-wrap">
          <table class="script">
            <thead>
              <tr>
                <th v-if="isCol('check')" class="check" title="全选 / 取消全选">
                  <VgCheckbox :model-value="allSelected" @update:model-value="toggleSelectAll" />
                </th>
                <th v-if="isCol('idx')" class="idx">#</th>
                <th v-if="isCol('speaker')" class="speaker-cell">角色</th>
                <th v-if="isCol('voice')" class="voice-cell">音色</th>
                <th v-if="isCol('text')" class="text-col">原文（{{ config.source_lang }}）</th>
                <th v-if="isCol('tts_text')" class="text-col">配音文本（{{ config.target_lang }}）</th>
                <th v-if="isCol('speed')" class="speed-cell">语速</th>
                <th v-if="isCol('style')" class="style-col">风格</th>
                <th v-if="isCol('status')" class="status-cell">状态</th>
                <th v-if="isCol('ops')" class="ops-cell">操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(row, index) in rows" :key="row.id" :class="{ disabled: !row.enabled }">
                <td v-if="isCol('check')" class="check">
                  <VgCheckbox v-model="row.enabled" />
                </td>
                <td v-if="isCol('idx')" class="idx">{{ index + 1 }}</td>
                <td v-if="isCol('speaker')" class="speaker-cell">
                  <VgInput v-model="row.speaker" bare size="sm" placeholder="角色名" />
                </td>
                <td v-if="isCol('voice')" class="voice-cell">
                  <VgSelect
                    v-model="row.voice"
                    :options="voiceOptions"
                    bare
                    size="sm"
                    searchable
                    placeholder="选择音色"
                  />
                </td>
                <td v-if="isCol('text')" class="text-col">
                  <VgTextarea
                    v-model="row.text"
                    bare
                    auto-height
                    placeholder="源语言原文…"
                  />
                </td>
                <td v-if="isCol('tts_text')" class="text-col">
                  <VgTextarea
                    v-model="row.tts_text"
                    bare
                    auto-height
                    :placeholder="sameLang ? '可留空=用原文' : '译文 / 可手改'"
                  />
                </td>
                <td v-if="isCol('speed')" class="speed-cell">
                  <VgInput
                    v-model="row.speed"
                    type="number"
                    bare
                    size="sm"
                    :min="0.5"
                    :max="2"
                    :step="0.05"
                  />
                </td>
                <td v-if="isCol('style')" class="style-col">
                  <VgTextarea
                    v-model="row.style"
                    bare
                    auto-height
                    placeholder="默认风格"
                  />
                </td>
                <td v-if="isCol('status')" class="status-cell">
                  <VgStatus :status="row.status || 'idle'" :title="row.error || ''">
                    {{ statusLabel(row.status) }}
                    <template v-if="row.duration"> · {{ formatDuration(row.duration) }}</template>
                  </VgStatus>
                </td>
                <td v-if="isCol('ops')" class="ops-cell">
                  <VgButton
                    size="sm"
                    :variant="playingId === row.id ? 'primary' : 'ghost'"
                    :icon="playingId === row.id ? 'pause' : 'listen'"
                    :icon-size="13"
                    icon-only
                    :disabled="row.status !== 'done' || !row.segment_path"
                    :title="row.status === 'done' && row.segment_path ? (playingId === row.id ? '暂停' : '试听') : '生成成功后可试听'"
                    @click="playRow(row)"
                  />
                  <VgButton
                    size="sm"
                    variant="ghost"
                    icon="refresh"
                    :icon-size="13"
                    icon-only
                    title="重新生成本条"
                    :disabled="generating || translating || !speakText(row)"
                    @click="regenerateRow(row)"
                  />
                  <VgButton size="sm" variant="ghost" icon="arrow-up" :icon-size="13" icon-only title="上移" @click="moveRow(index, -1)" />
                  <VgButton size="sm" variant="ghost" icon="arrow-down" :icon-size="13" icon-only title="下移" @click="moveRow(index, 1)" />
                  <VgButton size="sm" variant="ghost" icon="plus" :icon-size="13" icon-only title="下方插入" @click="insertRow(index)" />
                  <VgButton size="sm" variant="danger" icon="delete" :icon-size="13" icon-only title="删除" @click="removeRow(index)" />
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <footer class="footer">
          <div class="progress-block">
            <div class="progress-meta">
              <span>{{ progress.message || '就绪' }}</span>
              <span v-if="progress.total && !translating">
                {{ Math.min(progress.index, progress.total) }}/{{ progress.total }} · {{ progressPct }}%
              </span>
            </div>
            <div class="progress-bar"><i :style="{ width: (translating ? 40 : progressPct) + '%' }" /></div>
          </div>
          <div class="footer-result" v-if="lastOutput?.output">
            输出：
            <a @click.prevent="openOutput">{{ lastOutput.output }}</a>
            · {{ formatDuration(lastOutput.duration) }}
          </div>
        </footer>
      </section>

      <!-- 音色页 -->
      <section v-else-if="page === 'voices'" class="page page-voices">
        <div class="toolbar">
          <VgButton size="sm" variant="primary" icon="upload" :icon-size="14" @click="importVoice">导入音色</VgButton>
          <VgButton size="sm" icon="refresh" :icon-size="14" @click="refreshVoices">刷新</VgButton>
          <VgButton size="sm" variant="ghost" icon="folder" :icon-size="14" @click="openVoicesFolder">打开目录</VgButton>
          <div class="spacer" />
          <VgBadge>共 {{ voices.length }} 个</VgBadge>
          <span class="hint voices-dir-hint" :title="voicesDir">{{ voicesDir || 'voices/' }}</span>
        </div>

        <div v-if="!voices.length" class="empty-state voices-empty">
          <p>暂无音色</p>
          <p class="hint">把参考音频（wav / mp3 等）放入 voices 文件夹，或点「导入音色」。</p>
          <VgButton variant="primary" icon="upload" :icon-size="15" @click="importVoice">导入音色</VgButton>
        </div>

        <div v-else class="table-wrap voices-table-wrap">
          <table class="script voices-table">
            <thead>
              <tr>
                <th class="idx">#</th>
                <th class="voice-name-col">音色名</th>
                <th class="voice-file-col">文件名</th>
                <th class="voice-ext-col">格式</th>
                <th class="voice-size-col">大小</th>
                <th class="voice-ops-col">操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(v, index) in voices" :key="v.id">
                <td class="idx">{{ index + 1 }}</td>
                <td class="voice-name-col">
                  <div class="voice-name-cell">
                    <span class="voice-list-icon">
                      <AliIcon name="voice" :size="14" />
                    </span>
                    <span class="name">{{ v.name }}</span>
                  </div>
                </td>
                <td class="voice-file-col" :title="v.filename">{{ v.filename }}</td>
                <td class="voice-ext-col">{{ (v.ext || '').replace(/^\./, '').toUpperCase() || '—' }}</td>
                <td class="voice-size-col">{{ formatFileSize(v.size) }}</td>
                <td class="voice-ops-col">
                  <VgButton
                    size="sm"
                    :variant="playingId === `voice:${v.id}` ? 'primary' : 'ghost'"
                    :icon="playingId === `voice:${v.id}` ? 'pause' : 'listen'"
                    :icon-size="13"
                    icon-only
                    :title="playingId === `voice:${v.id}` ? '暂停' : '试听参考音'"
                    @click="playVoice(v)"
                  />
                  <VgButton size="sm" variant="danger" icon="delete" :icon-size="13" @click="deleteVoice(v.id)">删除</VgButton>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <!-- 设置页 -->
      <section v-else-if="page === 'settings'" class="page page-scroll page-settings">
        <div class="settings-layout">
          <VgCard title="API 连接">
            <VgField label="MiMo API Key" hint="也可通过环境变量 MIMO_API_KEY 注入；仅保存在本地 data/config.json">
              <VgInput
                v-model="settingsForm.api_key"
                type="password"
                :placeholder="config.api_key_set ? `已保存 ${config.api_key_masked}（留空不修改）` : 'tp-... 或 sk-...'"
              />
            </VgField>
            <VgField label="Base URL" hint="Token Plan 中国：https://token-plan-cn.xiaomimimo.com/v1">
              <VgInput v-model="settingsForm.base_url" />
            </VgField>
            <div class="row-actions">
              <VgButton icon="link" :icon-size="14" @click="checkApi()">检测 API</VgButton>
              <VgBadge :tone="apiBadgeTone" dot>{{ apiStatusMsg || '未检测' }}</VgBadge>
            </div>
          </VgCard>

          <VgCard title="模型">
            <VgField label="TTS 模型（配音）" hint="默认 mimo-v2.5-tts-voiceclone">
              <VgInput v-model="settingsForm.model" />
            </VgField>
            <VgField label="翻译 / 本土化模型" hint="默认 mimo-v2.5-pro（与 TTS 共用 Base URL 与 API Key）">
              <VgInput v-model="settingsForm.llm_model" />
            </VgField>
          </VgCard>

          <VgCard title="默认语言">
            <VgField label="默认源语言">
              <VgSelect v-model="settingsForm.source_lang" :options="languageOptions" searchable placeholder="选择语言" />
            </VgField>
            <VgField label="默认目标语言">
              <VgSelect v-model="settingsForm.target_lang" :options="languageOptions" searchable placeholder="选择语言" />
            </VgField>
          </VgCard>

          <VgCard title="配音默认参数">
            <VgField label="默认风格提示">
              <VgTextarea v-model="settingsForm.default_style" :rows="3" />
            </VgField>
            <VgField label="默认语速" hint="每行可单独覆盖；合成后用 ffmpeg atempo 变速">
              <VgInput v-model="settingsForm.default_speed" type="number" :min="0.5" :max="2" :step="0.05" />
            </VgField>
            <VgField label="句间静音 (ms)">
              <VgInput v-model="settingsForm.gap_ms" type="number" :min="0" :max="3000" :step="50" />
            </VgField>
          </VgCard>

          <VgCard title="并发性能">
            <VgField
              label="TTS 并发生成线程数"
              hint="默认 4。过大可能触发 API 限流；相同音色会缓存参考音频。"
            >
              <VgInput v-model="settingsForm.tts_workers" type="number" :min="1" :max="12" :step="1" />
            </VgField>
            <VgField
              label="翻译并发线程数"
              hint="直译/本土化走 mimo-v2.5-pro 的 /chat/completions，多批并行更慢会变成更快。"
            >
              <VgInput v-model="settingsForm.translate_workers" type="number" :min="1" :max="8" :step="1" />
            </VgField>
            <VgField
              label="翻译每批行数"
              hint="默认 8。批次越小首屏越快，过大单请求更慢。"
            >
              <VgInput v-model="settingsForm.translate_batch_size" type="number" :min="1" :max="30" :step="1" />
            </VgField>
          </VgCard>

          <VgCard title="外观 · 马卡龙换肤">
            <p class="hint" style="margin: -6px 0 12px">Linear 风格界面，一键切换马卡龙配色（本地记忆）</p>
            <div class="theme-grid">
              <button
                v-for="t in themes"
                :key="t.id"
                type="button"
                class="theme-card"
                :class="{ active: themeId === t.id }"
                @click="setTheme(t.id)"
              >
                <div class="theme-swatch">
                  <span v-for="(c, i) in t.swatch" :key="i" :style="{ background: c }" />
                </div>
                <div class="theme-card-name">{{ t.name }}</div>
                <div class="theme-card-desc">{{ t.desc }}</div>
              </button>
            </div>
          </VgCard>

          <VgCard title="关于">
            <div class="about-version">
              <div class="about-name">{{ appName }}</div>
              <div class="about-meta">{{ appNameEn }} · 版本 <strong>v{{ appVersion }}</strong></div>
              <p class="hint" style="margin: 10px 0 0">
                pywebview + Vue · MiMo VoiceClone / Pro · 本地音色克隆配音
              </p>
              <p class="hint" style="margin: 6px 0 0">
                日志目录：data/log（每天一个文件，最多保留 7 天）
              </p>
              <div class="row-actions" style="margin-top: 12px">
                <VgButton size="sm" variant="ghost" icon="folder" :icon-size="14" @click="call('open_log_folder')">
                  打开日志目录
                </VgButton>
              </div>
            </div>
          </VgCard>
        </div>

        <VgButton fab variant="primary" icon="save" :icon-size="18" title="保存设置" @click="saveSettings">
          保存设置
        </VgButton>
      </section>
    </main>

    <div v-if="toast" class="toast" :class="toast.type">{{ toast.message }}</div>
    <VgDialog />
  </div>
</template>

