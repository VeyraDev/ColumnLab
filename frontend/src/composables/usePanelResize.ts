type PointerResizeOptions = {
  event: PointerEvent
  onMove: (e: PointerEvent) => void
  onEnd?: () => void
  cursorClass?: string
  captureTarget?: HTMLElement | null
}

function bindPointerDrag(options: PointerResizeOptions) {
  const { event, onMove, onEnd, cursorClass, captureTarget } = options
  event.preventDefault()
  event.stopPropagation()

  const target = captureTarget ?? (event.currentTarget as HTMLElement | null)
  if (target?.setPointerCapture) {
    target.setPointerCapture(event.pointerId)
  }

  if (cursorClass) document.body.classList.add(cursorClass)
  document.body.style.userSelect = 'none'

  const move = (e: PointerEvent) => {
    if (e.pointerId !== event.pointerId) return
    onMove(e)
  }

  const up = (e: PointerEvent) => {
    if (e.pointerId !== event.pointerId) return
    if (target?.releasePointerCapture) {
      try {
        target.releasePointerCapture(event.pointerId)
      } catch {
        /* already released */
      }
    }
    if (cursorClass) document.body.classList.remove(cursorClass)
    document.body.style.userSelect = ''
    window.removeEventListener('pointermove', move)
    window.removeEventListener('pointerup', up)
    window.removeEventListener('pointercancel', up)
    onEnd?.()
  }

  window.addEventListener('pointermove', move)
  window.addEventListener('pointerup', up)
  window.addEventListener('pointercancel', up)
}

type HorizontalResizeOptions = {
  event: PointerEvent
  startSize: number
  min: number
  max: number
  invert?: boolean
  onMove: (size: number) => void
  onEnd?: () => void
  cursorClass?: string
  captureTarget?: HTMLElement | null
}

type VerticalResizeOptions = {
  event: PointerEvent
  startSize: number
  min: number
  max: number
  onMove: (size: number) => void
  onEnd?: () => void
  cursorClass?: string
  captureTarget?: HTMLElement | null
}

export function usePanelResize() {
  function startHorizontalResize(options: HorizontalResizeOptions) {
    const startX = options.event.clientX
    const sign = options.invert ? -1 : 1

    bindPointerDrag({
      event: options.event,
      cursorClass: options.cursorClass ?? 'is-resizing-col',
      captureTarget: options.captureTarget,
      onEnd: options.onEnd,
      onMove: (e) => {
        const delta = (e.clientX - startX) * sign
        const next = Math.max(options.min, Math.min(options.max, options.startSize + delta))
        options.onMove(next)
      },
    })
  }

  function startVerticalResize(options: VerticalResizeOptions) {
    const startY = options.event.clientY

    bindPointerDrag({
      event: options.event,
      cursorClass: options.cursorClass ?? 'is-resizing-row',
      captureTarget: options.captureTarget,
      onEnd: options.onEnd,
      onMove: (e) => {
        const delta = startY - e.clientY
        const next = Math.max(options.min, Math.min(options.max, options.startSize + delta))
        options.onMove(next)
      },
    })
  }

  return { startHorizontalResize, startVerticalResize }
}
