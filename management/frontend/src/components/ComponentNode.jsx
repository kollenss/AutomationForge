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
    idle:     { label: 'INACTIVE',          cls: '' },
    active:   { label: `PHASE ${phase + 1}/4`, cls: 'active' },
    failed:   { label: 'FAILED',           cls: 'failed' },
    unlocked: { label: 'UNLOCKED',         cls: 'unlocked' },
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

function RfidStatus({ readerId }) {
  const [uid, setUid] = useState('')
  const [flash, setFlash] = useState(false)
  const timerRef = useRef(null)

  useEffect(() => {
    function onState(s) {
      if (String(s.reader_id) !== String(readerId)) return
      setUid(s.uid)
      setFlash(true)
      if (timerRef.current) clearTimeout(timerRef.current)
      timerRef.current = setTimeout(() => setFlash(false), 1500)
    }
    socket.on('rfid_state', onState)
    return () => {
      socket.off('rfid_state', onState)
      if (timerRef.current) clearTimeout(timerRef.current)
    }
  }, [readerId])

  if (!uid) return null
  return (
    <div className={`cn-text-input-status ${flash ? 'cn-text-input-flash' : ''}`}>
      <span className="cn-text-input-label">Last:</span>
      <span className="cn-text-input-value" style={{fontFamily:'monospace'}}>{uid}</span>
    </div>
  )
}

function RfidSim({ readerId }) {
  const [uid, setUid] = useState('')

  function scan() {
    if (!uid.trim()) return
    fetch('/engine/hardware_event', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ device_type: 'rfid_reader', event: 'card_read', value: { reader_id: readerId, uid: uid.trim().toUpperCase() } }),
    })
  }

  return (
    <div className="cn-encoder-sim cn-rfid-sim">
      <input
        className="cn-sim-uid"
        value={uid}
        onChange={e => setUid(e.target.value)}
        onMouseDown={e => e.stopPropagation()}
        onClick={e => e.stopPropagation()}
        onKeyDown={e => { e.stopPropagation(); if (e.key === 'Enter') scan() }}
        placeholder="UID"
        spellCheck={false}
      />
      <button
        className="cn-sim-btn cn-sim-scan"
        onMouseDown={e => e.stopPropagation()}
        onClick={e => { e.stopPropagation(); scan() }}
        title="Simulate card scan"
      >Scan</button>
    </div>
  )
}

function UsbSim() {
  const [kind,  setKind]  = useState('yubikey')
  const [mount, setMount] = useState('/media/pi/USB')

  function send(action) {
    const isYubi = kind === 'yubikey'
    const event  = isYubi
      ? (action === 'insert' ? 'yubikey_inserted' : 'yubikey_removed')
      : (action === 'insert' ? 'usb_memory_inserted' : 'usb_memory_removed')
    const value  = isYubi ? { vendor_id: '1050' } : { mount_point: mount }
    fetch('/engine/hardware_event', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ device_type: 'usb_device_detector', event, value }),
    })
  }

  return (
    <div className="cn-encoder-sim cn-usb-sim">
      <select
        className="cn-sim-select"
        value={kind}
        onChange={e => setKind(e.target.value)}
        onMouseDown={e => e.stopPropagation()}
        onClick={e => e.stopPropagation()}
      >
        <option value="yubikey">YubiKey</option>
        <option value="usb_memory">USB Memory</option>
      </select>
      {kind === 'usb_memory' && (
        <input
          className="cn-sim-uid"
          value={mount}
          onChange={e => setMount(e.target.value)}
          onMouseDown={e => e.stopPropagation()}
          onClick={e => e.stopPropagation()}
          onKeyDown={e => e.stopPropagation()}
          placeholder="mount point"
          spellCheck={false}
        />
      )}
      <div className="cn-sim-row">
        <button
          className="cn-sim-btn cn-sim-scan"
          onMouseDown={e => e.stopPropagation()}
          onClick={e => { e.stopPropagation(); send('insert') }}
        >Insert</button>
        <button
          className="cn-sim-btn"
          onMouseDown={e => e.stopPropagation()}
          onClick={e => { e.stopPropagation(); send('remove') }}
        >Remove</button>
      </div>
    </div>
  )
}

function Max7219Status({ nodeId }) {
  const [text,      setText]      = useState('')
  const [scrolling, setScrolling] = useState(false)

  useEffect(() => {
    function onState(s) {
      if (s.node_id !== nodeId) return
      setText(s.text)
      setScrolling(s.scrolling)
    }
    socket.on('max7219_state', onState)
    return () => socket.off('max7219_state', onState)
  }, [nodeId])

  return (
    <div className="cn-display-preview">
      {scrolling && <span className="cn-display-scroll-icon">▶</span>}
      <span className={`cn-display-text${text === '' ? ' cn-display-off' : ''}`}>
        {text === '' ? '--------' : text}
      </span>
    </div>
  )
}

function GateStatus({ nodeId, defaultOpen }) {
  const [open, setOpen] = useState(defaultOpen !== '0')

  useEffect(() => {
    setOpen(defaultOpen !== '0')
  }, [defaultOpen])

  useEffect(() => {
    function onState(s) {
      if (s.node_id !== nodeId) return
      setOpen(s.open)
    }
    socket.on('gate_state', onState)
    return () => socket.off('gate_state', onState)
  }, [nodeId])

  return (
    <div className={`cn-relay-status ${open ? 'on' : 'off'}`}>
      <span className="cn-relay-dot" />
      {open ? 'OPEN' : 'LOCKED'}
    </div>
  )
}

function TextInputStatus({ inputId }) {  const [text, setText] = useState('')
  const [flash, setFlash] = useState(false)
  const timerRef = useRef(null)

  useEffect(() => {
    function onState(s) {
      if (String(s.input_id) !== String(inputId)) return
      setText(s.text)
      setFlash(true)
      if (timerRef.current) clearTimeout(timerRef.current)
      timerRef.current = setTimeout(() => setFlash(false), 1500)
    }
    socket.on('text_input_state', onState)
    return () => {
      socket.off('text_input_state', onState)
      if (timerRef.current) clearTimeout(timerRef.current)
    }
  }, [inputId])

  if (!text) return null
  return (
    <div className={`cn-text-input-status ${flash ? 'cn-text-input-flash' : ''}`}>
      <span className="cn-text-input-label">Last:</span>
      <span className="cn-text-input-value">{text}</span>
    </div>
  )
}

function TextInputSim({ inputId }) {
  const [val, setVal] = useState('')

  function send() {
    if (!val.trim()) return
    fetch('/engine/hardware_event', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ device_type: 'text_input', event: 'text_received', value: { input_id: String(inputId), text: val.trim() } }),
    })
    setVal('')
  }

  return (
    <div className="cn-encoder-sim cn-rfid-sim">
      <input
        className="cn-sim-uid"
        value={val}
        onChange={e => setVal(e.target.value)}
        onMouseDown={e => e.stopPropagation()}
        onClick={e => e.stopPropagation()}
        onKeyDown={e => { e.stopPropagation(); if (e.key === 'Enter') send() }}
        placeholder="Type text…"
        spellCheck={false}
      />
      <button
        className="cn-sim-btn cn-sim-scan"
        onMouseDown={e => e.stopPropagation()}
        onClick={e => { e.stopPropagation(); send() }}
      >Send</button>
    </div>
  )
}

function EncoderSim({ encoderId }) {
  function send(event, value) {
    fetch('/engine/hardware_event', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ device_type: 'ky040_encoder', event, value: { encoder_id: encoderId, ...value } }),
    })
  }
  return (
    <div className="cn-encoder-sim">
      <button className="cn-sim-btn" onMouseDown={e => e.stopPropagation()} onClick={e => { e.stopPropagation(); send('delta', { delta: -1 }) }} title="Turn left">◀</button>
      <button className="cn-sim-btn cn-sim-click" onMouseDown={e => e.stopPropagation()} onClick={e => { e.stopPropagation(); send('click', {}) }} title="Click">●</button>
      <button className="cn-sim-btn" onMouseDown={e => e.stopPropagation()} onClick={e => { e.stopPropagation(); send('delta', { delta: 1 }) }} title="Turn right">▶</button>
    </div>
  )
}

// Generic "Last: value" badge — listens to node_event{node_id, label, ok}
function LastValue({ nodeId }) {
  const [last, setLast] = useState(null)
  const [ok,   setOk]   = useState(true)
  const [flash, setFlash] = useState(false)
  const timerRef = useRef(null)

  useEffect(() => {
    function onEvent(e) {
      if (e.node_id !== nodeId) return
      setLast(e.label)
      setOk(e.ok !== false)
      setFlash(true)
      if (timerRef.current) clearTimeout(timerRef.current)
      timerRef.current = setTimeout(() => setFlash(false), 800)
    }
    socket.on('node_event', onEvent)
    return () => { socket.off('node_event', onEvent); if (timerRef.current) clearTimeout(timerRef.current) }
  }, [nodeId])

  if (!last) return null
  return (
    <div className={`cn-text-input-status ${flash ? 'cn-text-input-flash' : ''} ${ok ? '' : 'cn-last-err'}`}>
      <span className="cn-text-input-label">Last:</span>
      <span className="cn-text-input-value">{last}</span>
    </div>
  )
}

function TimerStatus({ nodeId, duration }) {
  const [remaining, setRemaining] = useState(duration)
  const [running,   setRunning]   = useState(false)

  useEffect(() => {
    setRemaining(duration)
  }, [duration])

  useEffect(() => {
    function onState(s) {
      if (s.node_id !== nodeId) return
      setRemaining(s.remaining)
      setRunning(s.running)
    }
    socket.on('timer_state', onState)
    return () => socket.off('timer_state', onState)
  }, [nodeId])

  return (
    <div className={`cn-combo-status ${running ? 'cn-combo-active' : ''}`}>
      <span className="cn-combo-dot" />
      <span>{remaining}s</span>
    </div>
  )
}

export default function ComponentNode({ id, data, selected }) {
  const allInputs = data.inputHandles || []
  const inputs = data.componentType === 'checklist'
    ? allInputs.filter(h => {
        const m = h.key.match(/^step_(\d+)$/)
        return !m || parseInt(m[1]) <= parseInt(data.params?.length ?? 3)
      })
    : allInputs
  const outputs = data.outputHandles || []
  const tb = data.layoutDir === 'TB'

  const inPos  = tb ? Position.Top    : Position.Left
  const outPos = tb ? Position.Bottom : Position.Right
  const inClass  = tb ? 'cn-handle-top'    : 'cn-handle-left'
  const outClass = tb ? 'cn-handle-bottom' : 'cn-handle-right'
  const inSection  = tb ? 'cn-handles cn-inputs cn-handles-top'    : 'cn-handles cn-inputs'
  const outSection = tb ? 'cn-handles cn-outputs cn-handles-bottom' : 'cn-handles cn-outputs'

  const displayValue = data.displayParam ? data.params?.[data.displayParam] : null

  return (
    <div className={`cn-root ${selected ? 'cn-selected' : ''} ${data.isActive ? 'cn-active' : ''}`}
      style={{ '--node-color': data.color, '--pulse-dur': data.pulseDur || '600ms' }}>
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
      {data.componentType === 'ky040_encoder' && (
        <EncoderSim encoderId={data.params?.encoder_id ?? 1} />
      )}
      {data.componentType === 'rfid_reader' && (
        <RfidStatus readerId={data.params?.reader_id ?? 1} />
      )}
      {data.componentType === 'rfid_reader' && (
        <RfidSim readerId={data.params?.reader_id ?? 1} />
      )}
      {data.componentType === 'console_log' && (
        <LastValue nodeId={id} />
      )}
      {data.componentType === 'rfid_auth' && (
        <LastValue nodeId={id} />
      )}
      {data.componentType === 'dfplayer' && (
        <LastValue nodeId={id} />
      )}
      {data.componentType === 'servo' && (
        <LastValue nodeId={id} />
      )}
      {data.componentType === 'led_zone' && (
        <LastValue nodeId={id} />
      )}
      {data.componentType === 'checklist' && (
        <LastValue nodeId={id} />
      )}
      {data.componentType === 'usb_device_detector' && (
        <LastValue nodeId={id} />
      )}
      {data.componentType === 'usb_device_detector' && (
        <UsbSim />
      )}
      {data.componentType === 'max7219' && (
        <Max7219Status nodeId={id} />
      )}
      {data.componentType === 'timer' && (
        <TimerStatus nodeId={id} duration={data.params?.duration_s ?? 60} />
      )}
      {data.componentType === 'gate' && (
        <GateStatus nodeId={id} defaultOpen={data.params?.default_open ?? '1'} />
      )}
      {data.componentType === 'text_input' && (
        <TextInputStatus inputId={data.params?.input_id ?? '1'} />
      )}
      {data.componentType === 'text_input' && (
        <TextInputSim inputId={data.params?.input_id ?? '1'} />
      )}

      {inputs.length > 0 && (
        <div className={inSection}>
          {inputs.map(h => (
            <div key={h.key} className={`cn-handle-row ${inClass}`}>
              <Handle type="target" position={inPos} id={h.key} className="cn-handle" />
              <span className="cn-handle-label" title={h.description}>{h.label}</span>
            </div>
          ))}
        </div>
      )}

      {outputs.length > 0 && (
        <div className={outSection}>
          {outputs.map(h => (
            <div key={h.key} className={`cn-handle-row ${outClass}`}>
              <span className="cn-handle-label" title={h.description}>{h.label}</span>
              <Handle type="source" position={outPos} id={h.key} className="cn-handle" />
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
