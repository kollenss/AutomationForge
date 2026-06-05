import { useEffect, useState } from 'react'
import { api } from '../api'
import { socket } from '../socket'
import './NodeModal.css'

function RelayLive({ channel }) {
  const ch  = Number(channel) >= 1 ? Number(channel) : 1
  const chS = String(ch)
  const [state, setState] = useState(null)
  const [busy, setBusy]   = useState(false)
  const [err, setErr]     = useState('')

  useEffect(() => {
    api.getRelayState()
      .then(s => setState(s[chS]))
      .catch(() => setErr('Board not connected'))

    function onState(s) { if (chS in s) { setState(s[chS]); setErr('') } }
    socket.on('relay_state', onState)
    return () => socket.off('relay_state', onState)
  }, [ch, chS])

  async function toggle(action) {
    setBusy(true)
    setErr('')
    try {
      await api.setRelay(ch, action)
      // State update arrives via socket event
    } catch (e) {
      setErr(e.message)
    } finally {
      setBusy(false)
    }
  }

  const isOn = state === true

  return (
    <div className="nm-live">
      <div className="nm-live-title">Live — Channel {ch}</div>
      <div className="nm-live-row">
        <div className={`nm-live-status ${state === null ? 'unknown' : isOn ? 'on' : 'off'}`}>
          <span className="nm-live-dot" />
          {state === null ? 'Connecting…' : isOn ? 'ON' : 'OFF'}
        </div>
        <div className="nm-live-btns">
          <button
            className="nm-live-btn on"
            onClick={() => toggle('on')}
            disabled={busy || isOn}
          >ON</button>
          <button
            className="nm-live-btn off"
            onClick={() => toggle('off')}
            disabled={busy || !isOn}
          >OFF</button>
        </div>
      </div>
      {err && <div className="nm-live-err">{err}</div>}
    </div>
  )
}

function RfidLive({ params }) {
  const readerId = params?.reader_id ?? 1
  const [uid, setUid]       = useState(null)
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    function onState(s) {
      if (s.reader_id === readerId) setUid(s.uid)
    }
    socket.on('rfid_state', onState)
    return () => socket.off('rfid_state', onState)
  }, [readerId])

  function copy() {
    if (!uid) return
    navigator.clipboard?.writeText(uid)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="nm-live">
      <div className="nm-live-title">Live Scan — Reader {readerId}</div>
      <div className="nm-live-row">
        <span className={`nm-live-uid ${uid ? 'active' : 'idle'}`}>
          {uid ?? 'Hold card to reader…'}
        </span>
        <button className="nm-live-btn" onClick={copy} disabled={!uid}>
          {copied ? 'Copied!' : 'Copy UID'}
        </button>
      </div>
      <div className="nm-hint">Paste this UID into an RFID Auth "Valid UIDs" field.</div>
    </div>
  )
}

const LIVE_COMPONENTS = {
  relay_channel: ({ params }) => <RelayLive channel={params?.channel ?? 1} />,
  rfid_reader:   ({ params }) => <RfidLive  params={params} />,
}

export default function NodeModal({ node, library, scenes, onChange, onClose, onDelete }) {
  if (!node || !library) return null

  const allComps = library.categories.flatMap(c => c.components)
  const def = allComps.find(c => c.type === node.data.componentType)
  if (!def) return null

  const LiveSection = LIVE_COMPONENTS[node.data.componentType]

  useEffect(() => {
    const onKey = e => { if (e.key === 'Escape' || e.key === 'Enter') onClose() }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  return (
    <div className="nm-backdrop" onClick={onClose}>
      <div className="nm-modal" onClick={e => e.stopPropagation()}>

        <div className="nm-header" style={{ '--c': node.data.color }}>
          <span className="nm-icon">{node.data.icon}</span>
          <div className="nm-titles">
            <div className="nm-title">{node.data.label}</div>
            <div className="nm-sub">{node.data.subtitle}</div>
          </div>
          <button className="nm-delete" onClick={() => onDelete(node.id)} title="Ta bort">🗑</button>
          <button className="nm-close" onClick={onClose}>✕</button>
        </div>

        {def.params.length > 0 && (
          <div className="nm-body">
            {def.params.map(p => (
              <div key={p.key} className="nm-field">
                <label>{p.label}</label>
                {p.type === 'scene_select' ? (
                  <select
                    value={node.data.params?.[p.key] ?? ''}
                    onChange={e => onChange(node.id, p.key, e.target.value)}
                  >
                    <option value="">— select scene —</option>
                    {(scenes || []).map(s => (
                      <option key={s.id} value={s.name}>{s.name}</option>
                    ))}
                  </select>
                ) : p.type === 'select' ? (
                  <select
                    value={node.data.params?.[p.key] ?? p.default}
                    onChange={e => onChange(node.id, p.key, e.target.value)}
                  >
                    {p.options.map(o => (
                      <option key={o.value} value={o.value}>{o.label}</option>
                    ))}
                  </select>
                ) : p.type === 'boolean' ? (
                  <div className="nm-toggle">
                    <input
                      type="checkbox"
                      id={`param-${p.key}`}
                      checked={!!(node.data.params?.[p.key] ?? p.default)}
                      onChange={e => onChange(node.id, p.key, e.target.checked)}
                    />
                    <label htmlFor={`param-${p.key}`} className="nm-toggle-label">
                      {node.data.params?.[p.key] ?? p.default ? 'Enabled' : 'Disabled'}
                    </label>
                  </div>
                ) : (
                  <input
                    type={p.type === 'password' ? 'password' : p.type === 'number' || p.type === 'pin' ? 'number' : 'text'}
                    value={node.data.params?.[p.key] ?? p.default}
                    min={p.min != null ? p.min : undefined}
                    max={p.max != null ? p.max : undefined}
                    onChange={e => onChange(node.id, p.key,
                      p.type === 'number' || p.type === 'pin' ? Number(e.target.value) : e.target.value
                    )}
                  />
                )}
                {p.type === 'pin' && (
                  <span className="nm-hint">Physical board pin number (not GPIO number)</span>
                )}
              </div>
            ))}
          </div>
        )}

        {LiveSection && <LiveSection key={node.data.params?.channel} params={node.data.params} />}

        <div className="nm-node-id" title="Node ID" onClick={() => navigator.clipboard?.writeText(node.id)}>
          {node.id}
        </div>

      </div>
    </div>
  )
}
