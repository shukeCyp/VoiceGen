import { createApp } from 'vue'
import App from './App.vue'
import { injectIconfont } from './iconfont'
import ui from './ui'
import './ui/styles.css'
import './styles.css'

injectIconfont()
createApp(App).use(ui).mount('#app')
