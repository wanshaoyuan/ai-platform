import { defineStore } from 'pinia'
import { ref, watch } from 'vue'

export type ThemeMode = 'light' | 'dark' | 'system'

const THEME_KEY = 'ai_platform_theme'
const TITLE_KEY = 'ai_platform_title'

export const useSettingsStore = defineStore('settings', () => {
  const themeMode = ref<ThemeMode>(
    (localStorage.getItem(THEME_KEY) as ThemeMode) || 'system'
  )
  const siteTitle = ref(localStorage.getItem(TITLE_KEY) || 'AI 中台')

  // 监听系统主题变化
  const systemDark = window.matchMedia('(prefers-color-scheme: dark)')

  function applyTheme(mode: ThemeMode) {
    const isDark =
      mode === 'dark' || (mode === 'system' && systemDark.matches)
    document.documentElement.classList.toggle('dark', isDark)
  }

  function setTheme(mode: ThemeMode) {
    themeMode.value = mode
    localStorage.setItem(THEME_KEY, mode)
    applyTheme(mode)
  }

  function setTitle(title: string) {
    const t = title.trim() || 'AI 中台'
    siteTitle.value = t
    localStorage.setItem(TITLE_KEY, t)
    document.title = t
  }

  // 系统主题切换时自动响应
  systemDark.addEventListener('change', () => {
    if (themeMode.value === 'system') applyTheme('system')
  })

  // 初始化
  applyTheme(themeMode.value)
  document.title = siteTitle.value

  return { themeMode, siteTitle, setTheme, setTitle }
})
