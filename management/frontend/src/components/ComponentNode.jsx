import { useState, useEffect, useRef } from 'react'
import { Handle, Position } from '@xyflow/react'
import { socket } from '../socket'
import './ComponentNode.css'

function EncoderStatus({ encoderId }) {
  const [pos, setPos]     = useState(null)
  const [delta, setDelta] = useState(0)

  useEffect(() => {
    function onState(s) {
      if (s.encoder_id === encoderId) {
        setPos(s.position)
        setDelta(s.delta)
      }
    }
    socket.on('encoder_state', onState)
    return () => socket.off('encoder_state', onState)
  }, [encoderId])

  if (pos === null) return null
  return (
    <div className="cn-encoder-status">
      <span className="cn-encoder-arrow">{delta > 0 ? '▲' : '▼'}</span>
      <span className="cn-encoder-pos">{pos}</span>
    </div>
  )
}

function ComboLockStatus({ nodeId }) {
  // status: 'idle' | 'active' | 'failed' | 'unlocked'
  const [status, setStatus] = useState('idle')
  const [phase,  setPhase]  = useState(0)
  const timerRef = useRef(null)

  useEffect(() => {
    function onState(s) {
      if (s.node_id !== nodeId) return

      if (timerRef.current) clearTimeout(timerRef.current)

      if (s.unlocked) {
        setStatus('unlocked')
        timerRef.current = setTimeout(() => setStatus('idle'), 3000)
        return
      }
      if (s.failed) {
        setStatus('failed')
        timerRef.current = setTimeout(() => setStatus('active'), 2000)
        return
      }
      if (s.enabled) {
        setStatus('active')
        setPhase(0)
        return
      }
      // Phase advance or count update
      if (s.phase !== undefined) setPhase(s.phase)
      setStatus('active')
    }

    socket.on('combo_state', onState)
    return () => {
      socket.off('combo_state', onState)
      if (timerRef.current) clearTimeout(timerRef.current)
    }
  }, [nodeId])

  const cfg = {
    idle:     { label: 'INAKTIV',        cls: '' },
    active:   { label: `FAS ${phase + 1}/4`, cls: 'active' },
    failed:   { label: 'FEL',            cls: 'failed' },
    unlocked: { label: 'UPPLÅST',        cls: 'unlocked' },
  }[status]

  return (
    <div className={`cn-combo-status ${cfg.cls ? `cn-combo-${cfg.cls}` : ''}`}>
      <span className="cn-combo-dot" />
      <span>{cfg.label}</span>
    </div>
  )
}

function RelayStatus({ channel }) {
  const ch = String(channel)
  const [on, setOn] = useState(null)

  useEffect(() => {
    fetch('/api/hardware/relay')
      .then(r => r.json())
      .then(s => { if (ch in s) setOn(s[ch]) })
      .catch(() => {})

    function onState(s) { if (ch in s) setOn(s[ch]) }
    socket.on('relay_state', onState)
    return () => socket.off('relay_state', onState)
  }, [ch])

  if (on === null) return null
  return (
    <div className={`cn-relay-status ${on ? 'on' : 'off'}`}>
      <span className="cn-relay-dot" />
      {on ? 'ON' : 'OFF'}
    </div>
  )
}

export default function ComponentNode({ id, data, selected }) {
  const inputs  = data.inputHandles  || []
  const outputs = data.outputHandles || []

  const displayValue = data.displayParam ? data.params?.[data.displayParam] : null

  return (
    <div className={`cn-root ${selected ? 'cn-selected' : ''}`} style={{ '--node-color': data.color }}>
      <div className="cn-header">
        <span className="cn-icon">{data.icon}</span>
        <div className="cn-labels">
          <div className="cn-label">{data.label}</div>
          <div className="cn-subtitle">{data.params?.name || data.subtitle}</div>
        </div>
        {displayValue != null && (
          <span className="cn-badge">{displayValue}</span>
        )}
      </div>

      {data.componentType === 'combo_lock' && (
        <ComboLockStatus nodeId={id} />
      )}
      {data.componentType === 'relay_channel' && (
        <RelayStatus channel={data.params?.channel ?? 1} />
      )}
      {data.componentType === 'ky040_encoder' && (
        <EncoderStatus encoderId={data.params?.encoder_id ?? 1} />
      )}

      {inputs.length > 0 && (
        <div className="cn-handles cn-inputs">
          {inputs.map(h => (
            <div key={h.key} className="cn-handle-row cn-handle-left">
              <Handle type="target" position={Position.Left} id={h.key} className="cn-handle" />
              <span className="cn-handle-label">{h.label}</span>
            </div>
          ))}
        </div>
      )}

      {outputs.length > 0 && (
        <div className="cn-handles cn-outputs">
          {outputs.map(h => (
            <div key={h.key} className="cn-handle-row cn-handle-right">
              <span className="cn-handle-label">{h.label}</span>
              <Handle type="source" position={Position.Right} id={h.key} className="cn-handle" />
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
