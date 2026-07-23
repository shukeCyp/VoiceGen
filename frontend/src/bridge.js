/**
 * pywebview JS API bridge with graceful browser fallback for pure web preview.
 */

function waitForApi(timeoutMs = 8000) {
  return new Promise((resolve) => {
    if (window.pywebview?.api) {
      resolve(window.pywebview.api)
      return
    }
    const start = Date.now()
    const timer = setInterval(() => {
      if (window.pywebview?.api) {
        clearInterval(timer)
        resolve(window.pywebview.api)
      } else if (Date.now() - start > timeoutMs) {
        clearInterval(timer)
        resolve(null)
      }
    }, 50)
  })
}

let apiPromise = null

export function getApi() {
  if (!apiPromise) apiPromise = waitForApi()
  return apiPromise
}

export async function call(method, ...args) {
  const api = await getApi()
  if (!api || typeof api[method] !== 'function') {
    return {
      ok: false,
      error: '桌面桥接未就绪。请通过 python main.py 启动应用。',
    }
  }
  try {
    return await api[method](...args)
  } catch (err) {
    return { ok: false, error: err?.message || String(err) }
  }
}

export function onEvent(handler) {
  window.__voicegen_event = (event, payload) => {
    try {
      handler(event, payload)
    } catch (e) {
      console.error(e)
    }
  }
}
