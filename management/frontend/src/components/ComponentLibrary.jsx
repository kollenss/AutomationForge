import { useState, useEffect, useCallback } from 'react'
import { api } from '../api'
import './ComponentLibrary.css'

function onDragStart(e, compDef) {
  e.dataTransfer.setData('application/gameforge', JSON.stringify(compDef))
  e.dataTransfer.effectAllowed = 'copy'
}

export default function ComponentLibrary({ library, onReload }) {
  const [restarting, setRestarting] = useState(false)
  const [status, setStatus] = useState(null)   // { kind: 'ok' | 'error', text }
  const [health, setHealth] = useState(null)   // { up, connected } | null

  const pollHealth = useCallback(async () => {
    try {
      setHealth(await api.hardwareStatus())
    } catch {
      setHealth({ up: false, connected: 0 })
    }
  }, [])

  // Poll the hardware service health on mount and every 5s
  useEffect(() => {
    pollHealth()
    const id = setInterval(pollHealth, 5000)
    return () => clearInterval(id)
  }, [pollHealth])

  async function restartHardware() {
    setRestarting(true)
    setStatus(null)
    try {
      const res = await api.restartHardware()
      const connected = (res.connected || []).filter(d => d.connected)
      setStatus({
        kind: 'ok',
        text: `Reloaded — ${connected.length} device${connected.length === 1 ? '' : 's'} connected`,
      })
      onReload?.()
    } catch (err) {
      setStatus({ kind: 'error', text: err.message || 'Restart failed' })
    } finally {
      setRestarting(false)
      pollHealth()
    }
  }

  if (!library) return <div className="cl-loading">Loading…</div>

  const healthState = (restarting || !health) ? 'wait' : health.up ? 'up' : 'down'
  const healthLabel = {
    wait: 'Checking…',
    up:   `Hardware online${health?.connected != null ? ` — ${health.connected} connected` : ''}`,
    down: 'Hardware offline',
  }[healthState]

  return (
    <div className="cl-root">
      <div className="cl-title">Components</div>

      <div className="cl-hw-restart">
        <div className="cl-hw-health">
          <span className={`cl-hw-dot cl-hw-dot-${healthState}`} />
          <span className="cl-hw-health-label">{healthLabel}</span>
        </div>
        <button
          className="cl-hw-restart-btn"
          onClick={restartHardware}
          disabled={restarting}
          title="Restart the hardware service to detect newly wired hardware">
          {restarting ? '⟳ Restarting…' : '⟳ Restart Hardware'}
        </button>
        {status && (
          <div className={`cl-hw-status cl-hw-${status.kind}`}>{status.text}</div>
        )}
      </div>

      {library.categories.map(cat => (
        <div key={cat.id} className="cl-category">
          <div className="cl-cat-label" style={{ color: cat.color }}>{cat.label}</div>
          {cat.components.map(comp => (
            <div
              key={comp.type}
              className="cl-item"
              draggable
              onDragStart={e => onDragStart(e, comp)}
              title={comp.subtitle}
            >
              <span className="cl-item-icon">{comp.icon}</span>
              <div className="cl-item-text">
                <div className="cl-item-label">{comp.label}</div>
                <div className="cl-item-sub">{comp.subtitle}</div>
              </div>
              <span className="cl-drag-hint" style={{ color: cat.color }}>⠿</span>
            </div>
          ))}
        </div>
      ))}
    </div>
  )
}
