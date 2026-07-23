/**
 * Capture real UI screenshots for docs tutorial (browser + mock pywebview API).
 * Usage: node scripts/tutorial_screenshots.mjs
 * Requires: frontend dev server on 127.0.0.1:5173, playwright browsers.
 */
import { chromium } from 'playwright'
import { mkdirSync } from 'fs'
import { dirname, join } from 'path'
import { fileURLToPath } from 'url'

const __dirname = dirname(fileURLToPath(import.meta.url))
const ROOT = join(__dirname, '..')
const OUT = join(ROOT, 'docs', 'assets', 'screens')
const BASE = process.env.TUTORIAL_URL || 'http://127.0.0.1:5173'

mkdirSync(OUT, { recursive: true })

const mockApi = {
  get_version: async () => ({
    ok: true,
    data: {
      name: '多人配音工具',
      name_en: 'VoiceGen',
      version: '1.0.0',
      display: '多人配音工具 v1.0.0',
      window_title: '多人配音工具 v1.0.0',
    },
  }),
  get_config: async () => ({
    ok: true,
    data: {
      api_key_set: true,
      api_key_masked: 'tp-x...demo',
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
    },
  }),
  save_config: async () => mockApi.get_config(),
  check_api: async () => ({
    ok: true,
    data: {
      ok: true,
      base_url: 'https://token-plan-cn.xiaomimimo.com/v1',
      tts: { model: 'mimo-v2.5-tts-voiceclone', status: 'ready' },
      llm: { model: 'mimo-v2.5-pro', status: 'ready' },
      status: 'ready',
    },
  }),
  list_languages: async () => ({
    ok: true,
    data: {
      languages: [
        { code: 'zh-CN', name: '简体中文', native: '简体中文' },
        { code: 'en-US', name: '英语（美式）', native: 'English (US)' },
        { code: 'ja-JP', name: '日语', native: '日本語' },
        { code: 'de-DE', name: '德语', native: 'Deutsch' },
        { code: 'fr-FR', name: '法语', native: 'Français' },
      ],
    },
  }),
  list_voices: async () => ({
    ok: true,
    data: {
      voices_dir: '/Users/demo/VoiceGen/voices',
      voices: [
        { id: 'Alex', name: 'Alex', filename: 'Alex.mp3', ext: '.mp3', size: 271935, path: '/voices/Alex.mp3' },
        { id: 'Natasha', name: 'Natasha', filename: 'Natasha.mp3', ext: '.mp3', size: 303282, path: '/voices/Natasha.mp3' },
        { id: '德语', name: '德语', filename: '德语.mp3', ext: '.mp3', size: 371330, path: '/voices/德语.mp3' },
        { id: '法语', name: '法语', filename: '法语.mp3', ext: '.mp3', size: 232226, path: '/voices/法语.mp3' },
      ],
    },
  }),
  load_project: async () => ({
    ok: true,
    data: {
      source_lang: 'zh-CN',
      target_lang: 'en-US',
      rows: [
        {
          id: 'r1',
          speaker: '甲',
          voice: 'Alex',
          text: '各位观众朋友们，大家好！我们是四人相声组。',
          tts_text: '',
          speed: 1.0,
          style: '热情开场',
          enabled: true,
          status: 'done',
          duration: 2.4,
          segment_path: '/output/demo_a.wav',
          error: '',
        },
        {
          id: 'r2',
          speaker: '乙',
          voice: 'Natasha',
          text: '别吹了甲哥，你再这么自我介绍，观众以为我们在点名呢。',
          tts_text: '',
          speed: 1.05,
          style: '吐槽轻松',
          enabled: true,
          status: 'idle',
          duration: null,
          segment_path: '',
          error: '',
        },
        {
          id: 'r3',
          speaker: '丙',
          voice: '德语',
          text: '对啊，点完名还得交作业。今天主题是啥？',
          tts_text: '',
          speed: 1.0,
          style: '憨厚好奇',
          enabled: true,
          status: 'idle',
          duration: null,
          segment_path: '',
          error: '',
        },
        {
          id: 'r4',
          speaker: '丁',
          voice: '法语',
          text: '主题啊……人工智能能不能替代相声演员！',
          tts_text: '',
          speed: 1.05,
          style: '得意宣布',
          enabled: false,
          status: 'idle',
          duration: null,
          segment_path: '',
          error: '',
        },
      ],
    },
  }),
  save_project: async () => ({ ok: true, data: { path: 'data/project.json' } }),
  get_paths: async () => ({
    ok: true,
    data: {
      voices_dir: '/Users/demo/VoiceGen/voices',
      output_dir: '/Users/demo/VoiceGen/output',
      data_dir: '/Users/demo/VoiceGen/data',
      log_dir: '/Users/demo/VoiceGen/data/log',
    },
  }),
  get_runtime_status: async () => ({
    ok: true,
    data: {
      ffmpeg: {
        ffmpeg: 'vendor/ffmpeg/windows/ffmpeg.exe',
        ffprobe: 'vendor/ffmpeg/windows/ffprobe.exe',
        bundled: true,
      },
      log_dir: '/Users/demo/VoiceGen/data/log',
    },
  }),
  client_log: async () => ({ ok: true, data: true }),
  // unused stubs
  generate_all: async () => ({ ok: true, data: { started: true } }),
  translate_rows: async () => ({ ok: true, data: { started: true } }),
  cancel_generate: async () => ({ ok: true, data: true }),
  pick_import_file: async () => ({ ok: true, data: null }),
  save_export_file: async () => ({ ok: true, data: null }),
  pick_voice_file: async () => ({ ok: true, data: null }),
  open_voices_folder: async () => ({ ok: true, data: true }),
  open_output_folder: async () => ({ ok: true, data: true }),
  open_log_folder: async () => ({ ok: true, data: true }),
  get_audio_data_url: async () => ({ ok: false, error: 'demo' }),
  delete_voice: async () => ({ ok: true, data: true }),
  import_voice: async () => ({ ok: true, data: null }),
}

async function shot(page, name) {
  const path = join(OUT, `${name}.png`)
  await page.screenshot({ path, fullPage: false })
  console.log('saved', path)
}

async function main() {
  const browser = await chromium.launch({
    channel: 'chrome',
    headless: true,
  })
  const page = await browser.newPage({
    viewport: { width: 1360, height: 860 },
    deviceScaleFactor: 2,
  })

  await page.addInitScript((api) => {
    // Bind mock pywebview API before app boots
    const bound = {}
    for (const [k, v] of Object.entries(api)) {
      bound[k] = (...args) => Promise.resolve(v(...args))
    }
    window.pywebview = { api: bound }
  }, mockApi)

  await page.goto(BASE, { waitUntil: 'networkidle', timeout: 60000 })
  await page.waitForTimeout(1200)

  // Force API badge ready
  await page.evaluate(() => {
    // close any toast after auto check
  })
  await page.waitForTimeout(800)

  // 01 dubbing main
  await shot(page, '01-配音主界面')

  // 02 open column menu
  const colBtn = page.getByRole('button', { name: '显示列' })
  if (await colBtn.count()) {
    await colBtn.click()
    await page.waitForTimeout(400)
    await shot(page, '02-显示列菜单')
    await page.mouse.click(10, 10)
    await page.waitForTimeout(300)
  }

  // 03 voices page
  await page.getByRole('button', { name: /音色/ }).first().click()
  await page.waitForTimeout(600)
  await shot(page, '03-音色库')

  // 04 settings
  await page.getByRole('button', { name: /设置/ }).first().click()
  await page.waitForTimeout(600)
  await shot(page, '04-设置-API')

  // scroll for concurrent / about
  await page.evaluate(() => {
    const sc = document.querySelector('.page-settings') || document.querySelector('.page-scroll')
    if (sc) sc.scrollTop = 400
  })
  await page.waitForTimeout(400)
  await shot(page, '05-设置-并发与主题')

  await page.evaluate(() => {
    const sc = document.querySelector('.page-settings') || document.querySelector('.page-scroll')
    if (sc) sc.scrollTop = 2000
  })
  await page.waitForTimeout(400)
  await shot(page, '06-设置-关于与日志')

  // back to dub, open dialog via evaluate if possible - inject dialog
  await page.getByRole('button', { name: /配音/ }).first().click()
  await page.waitForTimeout(500)

  // Trigger clear dialog
  const clearBtn = page.getByRole('button', { name: '一键清空' })
  if (await clearBtn.count()) {
    await clearBtn.click()
    await page.waitForTimeout(500)
    await shot(page, '07-确认对话框')
    // cancel
    const cancel = page.getByRole('button', { name: '取消' })
    if (await cancel.count()) await cancel.click()
    await page.waitForTimeout(300)
  }

  // translate toolbar area focus - crop full window still fine
  await shot(page, '08-翻译工具栏')

  // select language dropdown open
  const langTriggers = page.locator('.vg-select__trigger')
  if (await langTriggers.count()) {
    await langTriggers.first().click()
    await page.waitForTimeout(400)
    await shot(page, '09-语言下拉')
    await page.keyboard.press('Escape')
    await page.waitForTimeout(200)
  }

  // ops area with regenerate buttons - already in main shot
  await browser.close()
  console.log('done')
}

main().catch((e) => {
  console.error(e)
  process.exit(1)
})
