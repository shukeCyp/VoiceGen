/**
 * VoiceGen UI Kit
 * 统一导出：按钮 / 输入 / 自定义下拉 / 对话框 / 徽章 / 卡片 等
 */
import VgButton from './VgButton.vue'
import VgInput from './VgInput.vue'
import VgTextarea from './VgTextarea.vue'
import VgSelect from './VgSelect.vue'
import VgCheckbox from './VgCheckbox.vue'
import VgBadge from './VgBadge.vue'
import VgCard from './VgCard.vue'
import VgField from './VgField.vue'
import VgStatus from './VgStatus.vue'
import VgDialog from './VgDialog.vue'
import AliIcon from '../components/AliIcon.vue'
import { vgAlert, vgConfirm } from './dialog'

export {
  VgButton,
  VgInput,
  VgTextarea,
  VgSelect,
  VgCheckbox,
  VgBadge,
  VgCard,
  VgField,
  VgStatus,
  VgDialog,
  AliIcon,
  vgAlert,
  vgConfirm,
}

export default {
  install(app) {
    app.component('VgButton', VgButton)
    app.component('VgInput', VgInput)
    app.component('VgTextarea', VgTextarea)
    app.component('VgSelect', VgSelect)
    app.component('VgCheckbox', VgCheckbox)
    app.component('VgBadge', VgBadge)
    app.component('VgCard', VgCard)
    app.component('VgField', VgField)
    app.component('VgStatus', VgStatus)
    app.component('VgDialog', VgDialog)
    app.component('AliIcon', AliIcon)
    app.config.globalProperties.$vgConfirm = vgConfirm
    app.config.globalProperties.$vgAlert = vgAlert
  },
}
