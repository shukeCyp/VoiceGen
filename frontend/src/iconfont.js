/** Inject Alibaba-iconfont-style SVG symbols into document (offline). */
import symbolsUrl from './assets/iconfont-symbols.svg?raw'

let injected = false

export function injectIconfont() {
  if (injected || typeof document === 'undefined') return
  const wrap = document.createElement('div')
  wrap.setAttribute('aria-hidden', 'true')
  wrap.style.cssText = 'position:absolute;width:0;height:0;overflow:hidden'
  wrap.innerHTML = symbolsUrl
  document.body.prepend(wrap)
  injected = true
}
