/**
 * 智慧学伴 国际化配置
 * 支持中文/英文双语
 */
import { createI18n } from 'vue-i18n'
import zhCN from '@/../public/locales/zh-CN.json'
import enUS from '@/../public/locales/en-US.json'

const i18n = createI18n({
  legacy: false,
  locale: localStorage.getItem('locale') || 'zh-CN',
  fallbackLocale: 'zh-CN',
  messages: {
    'zh-CN': zhCN,
    'en-US': enUS,
  },
})

export default i18n
