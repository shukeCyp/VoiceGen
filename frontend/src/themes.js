/** Macaron palettes + Linear-inspired surface tokens */

export const THEMES = [
  {
    id: 'lilac',
    name: '紫丁香',
    desc: 'Linear 淡紫',
    swatch: ['#F7F5FF', '#E9E2FF', '#8B7CF6'],
  },
  {
    id: 'peach',
    name: '蜜桃',
    desc: '暖粉橘',
    swatch: ['#FFF7F4', '#FFD9CC', '#F08A6B'],
  },
  {
    id: 'mint',
    name: '薄荷绿',
    desc: '清新抹茶',
    swatch: ['#F3FBF7', '#C9F0DF', '#3DB88A'],
  },
  {
    id: 'sky',
    name: '天空蓝',
    desc: '柔和天蓝',
    swatch: ['#F4F9FF', '#D4E8FF', '#5B9DF0'],
  },
  {
    id: 'rose',
    name: '玫瑰',
    desc: '浅粉马卡龙',
    swatch: ['#FFF5F8', '#FFD6E3', '#E86B97'],
  },
  {
    id: 'lemon',
    name: '柠檬奶',
    desc: '奶油黄',
    swatch: ['#FFFEF6', '#FFF0B8', '#D4A017'],
  },
  {
    id: 'lavender',
    name: '雾灰紫',
    desc: '中性紫灰',
    swatch: ['#F6F6FA', '#E2E0EE', '#7A74A0'],
  },
  {
    id: 'ink',
    name: '墨夜',
    desc: 'Linear 深色',
    swatch: ['#0F1014', '#1C1E26', '#8B7CF6'],
    dark: true,
  },
]

const STORAGE_KEY = 'voicegen_theme'

export function loadThemeId() {
  try {
    const id = localStorage.getItem(STORAGE_KEY)
    if (id && THEMES.some((t) => t.id === id)) return id
  } catch {
    /* ignore */
  }
  return 'lilac'
}

export function saveThemeId(id) {
  try {
    localStorage.setItem(STORAGE_KEY, id)
  } catch {
    /* ignore */
  }
}

export function applyTheme(id) {
  const theme = THEMES.find((t) => t.id === id) || THEMES[0]
  document.documentElement.setAttribute('data-theme', theme.id)
  if (theme.dark) {
    document.documentElement.classList.add('theme-dark')
  } else {
    document.documentElement.classList.remove('theme-dark')
  }
  saveThemeId(theme.id)
  return theme.id
}
