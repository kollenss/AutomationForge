import { useState, useEffect, useCallback, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import Dagre from '@dagrejs/dagre'
import {
  ReactFlow, Background, Controls, MiniMap,
  useNodesState, useEdgesState, addEdge, ReactFlowProvider, useReactFlow,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'

import { api } from '../api'
import { socket } from '../socket'
import ComponentLibrary from '../components/ComponentLibrary'
import ComponentNode from '../components/ComponentNode'
import NodeModal from '../components/NodeModal'
import './SceneEditorPage.css'

const nodeTypes = { component: ComponentNode }

function uid() {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, c => {
    const r = Math.random() * 16 | 0
    return (c === 'x' ? r : (r & 0x3 | 0x8)).toString(16)
  })
}

// Node size estimates for Dagre (actual DOM size unknown at layout time)
const DAGRE_NODE_W = 220
const DAGRE_NODE_H = 160

function computeLayout(nodes, edges, direction) {
  const g = new Dagre.graphlib.Graph().setDefaultEdgeLabel(() => ({}))
  g.setGraph({ rankdir: direction, nodesep: 60, ranksep: 100, marginx: 40, marginy: 40 })
  edges.forEach(e => g.setEdge(e.source, e.target))
  nodes.forEach(n => g.setNode(n.id, { width: DAGRE_NODE_W, height: DAGRE_NODE_H }))
  Dagre.layout(g)
  return nodes.map(n => {
    const pos = g.node(n.id)
    return { ...n, position: { x: pos.x - DAGRE_NODE_W / 2, y: pos.y - DAGRE_NODE_H / 2 } }
  })
}


function EditorInner({ project, scene, library }) {
  const navigate = useNavigate()
  const reactFlowWrapper = useRef(null)
  const { screenToFlowPosition, fitView } = useReactFlow()
  const [nodes, setNodes, onNodesChange] = useNodesState(scene.nodes || [])
  const [edges, setEdges, onEdgesChange] = useEdgesState(scene.edges || [])
  const [modalNode, setModalNode] = useState(null)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(true)

  // ── Layout direction ───────────────────────────────────────────────────────
  const [layoutDir, setLayoutDir] = useState(() => localStorage.getItem('gf_layout') || 'LR')
  const layoutSkip = useRef(false)

  function applyLayout(dir) {
    layoutSkip.current = true   // don't mark dirty from the setNodes call
    setNodes(ns => computeLayout(ns, edges, dir))
    setTimeout(() => {
      fitView({ padding: 0.12, duration: 400 })
      layoutSkip.current = false
    }, 50)
    setSaved(false)
  }

  function toggleLayout() {
    const next = layoutDir === 'LR' ? 'TB' : 'LR'
    setLayoutDir(next)
    localStorage.setItem('gf_layout', next)
    applyLayout(next)
  }

  // ── Signal flow visualization ─────────────────────────────────────────────
  const [debugMode, setDebugMode] = useState(() => localStorage.getItem('gf_debug') === 'true')
  const [activeEdges, setActiveEdges] = useState(new Set())
  const [activeNodes, setActiveNodes] = useState(new Set())
  const pulseTimers  = useRef({})
  const [logEntries, setLogEntries] = useState([])
  const [logVisible, setLogVisible] = useState(false)
  const [replaying,  setReplaying]  = useState(false)
  const [replaySpeed, setReplaySpeed] = useState(0.3)
  const logRef        = useRef([])
  const logStartRef   = useRef(Date.now())
  const replayTimers  = useRef([])

  function toggleDebug() {
    const next = !debugMode
    setDebugMode(next)
    localStorage.setItem('gf_debug', String(next))
    if (!next) { setActiveEdges(new Set()); setActiveNodes(new Set()) }
  }

  function pulse(setFn, id, duration = 2200) {
    setFn(s => new Set([...s, id]))
    clearTimeout(pulseTimers.current[id])
    pulseTimers.current[id] = setTimeout(() =>
      setFn(s => { const n = new Set(s); n.delete(id); return n }), duration)
  }

  function addLog(type, id, value, targetHandle) {
    const entry = { t: Date.now() - logStartRef.current, type, id, value, targetHandle }
    const next  = [...logRef.current.slice(-499), entry]
    logRef.current = next
    setLogEntries(next)
  }

  useEffect(() => {
    if (!debugMode) return
    const onEdgePulse = ({ edge_id, value, target_handle }) => { pulse(setActiveEdges, edge_id); addLog('edge', edge_id, value, target_handle) }
    const onNodePulse = ({ node_id }) => { pulse(setActiveNodes, node_id); addLog('node', node_id) }
    const onConsoleLog = ({ node_id, label, value }) => {
      pulse(setActiveNodes, node_id)
      addLog('console', node_id, value, label)
      if (!logVisible) setLogVisible(true)
    }
    socket.on('edge_pulse',   onEdgePulse)
    socket.on('node_pulse',   onNodePulse)
    socket.on('console_log',  onConsoleLog)
    return () => {
      socket.off('edge_pulse',  onEdgePulse)
      socket.off('node_pulse',  onNodePulse)
      socket.off('console_log', onConsoleLog)
    }
  }, [debugMode, logVisible])

  function startReplay() {
    if (replaying || logRef.current.length === 0) return
    setReplaying(true)
    replayTimers.current.forEach(clearTimeout)
    replayTimers.current = []
    const entries  = [...logRef.current]
    const first    = entries[0].t
    const scale    = 1 / replaySpeed
    const pulseDur = Math.round(800 * scale)
    entries.forEach(entry => {
      const t = setTimeout(() => {
        if (entry.type === 'node') pulse(setActiveNodes, entry.id, pulseDur)
        else                       pulse(setActiveEdges, entry.id, pulseDur)
      }, (entry.t - first) * scale)
      replayTimers.current.push(t)
    })
    const total = (entries[entries.length - 1].t - first) * scale + pulseDur + 200
    replayTimers.current.push(setTimeout(() => setReplaying(false), total))
  }

  function clearLog() {
    logRef.current    = []
    logStartRef.current = Date.now()
    setLogEntries([])
  }

  function labelFor(entry) {
    if (entry.type === 'console') {
      const n = nodes.find(n => n.id === entry.id)
      const name = n ? n.data.label : entry.id.slice(-8)
      return `[${entry.targetHandle || 'log'}] ${name}`
    }
    if (entry.type === 'node') {
      const n = nodes.find(n => n.id === entry.id)
      return n ? n.data.label : entry.id.slice(-8)
    }
    const e  = edges.find(e => e.id === entry.id)
    if (!e) return entry.id.slice(-8)
    const src = nodes.find(n => n.id === e.source)
    const tgt = nodes.find(n => n.id === e.target)
    const tgtLabel = tgt?.data.label ?? '?'
    const handle   = entry.targetHandle
    const handleLabel = handle
      ? tgt?.data.inputHandles?.find(h => h.key === handle)?.label ?? handle
      : null
    return `${src?.data.label ?? '?'} → ${tgtLabel}${handleLabel ? ` (${handleLabel})` : ''}`
  }

  const onConnect = useCallback(params => setEdges(eds => addEdge(
    { ...params, type: 'smoothstep', animated: true }, eds)), [setEdges])

  // Native DOM listeners bypass React Flow's internal event handling
  useEffect(() => {
    const el = reactFlowWrapper.current
    if (!el) return

    const handleDragOver = e => { e.preventDefault(); e.dataTransfer.dropEffect = 'copy' }
    const handleDrop = e => {
      e.preventDefault()
      const raw = e.dataTransfer.getData('application/gameforge')
      if (!raw) return
      try {
        const def = JSON.parse(raw)
        const pos = screenToFlowPosition({ x: e.clientX, y: e.clientY })
        setNodes(ns => [...ns, {
          id: uid(),
          type: 'component',
          position: pos,
          data: {
            componentType: def.type,
            label: def.label,
            subtitle: def.subtitle,
            color: def.color,
            icon: def.icon,
            displayParam: def.display_param || null,
            params: Object.fromEntries((def.params || []).map(p => [p.key, p.default])),
            inputHandles:  def.inputs  || [],
            outputHandles: def.outputs || [],
          },
        }])
        setSaved(false)
      } catch (err) { console.error('drop error', err) }
    }

    el.addEventListener('dragover', handleDragOver)
    el.addEventListener('drop', handleDrop)
    return () => {
      el.removeEventListener('dragover', handleDragOver)
      el.removeEventListener('drop', handleDrop)
    }
  }, [screenToFlowPosition, setNodes])

  function onNodeClick(_, node) { setModalNode(node) }

  function deleteNode(nodeId) {
    setNodes(ns => ns.filter(n => n.id !== nodeId))
    setEdges(eds => eds.filter(e => e.source !== nodeId && e.target !== nodeId))
    setModalNode(null)
    setSaved(false)
  }

  function updateParam(nodeId, key, value) {
    setNodes(ns => ns.map(n =>
      n.id === nodeId
        ? { ...n, data: { ...n.data, params: { ...n.data.params, [key]: value } } }
        : n
    ))
    setModalNode(prev =>
      prev?.id === nodeId
        ? { ...prev, data: { ...prev.data, params: { ...prev.data.params, [key]: value } } }
        : prev
    )
    setSaved(false)
  }

  async function save() {
    setSaving(true)
    try {
      await api.updateScene(project.id, scene.id, { nodes, edges })
      setSaved(true)
    } finally { setSaving(false) }
  }

  function syncNodes() {
    // Build type → definition lookup from the component library
    const defByType = {}
    for (const cat of (library.categories || [])) {
      for (const comp of (cat.components || [])) {
        defByType[comp.type] = comp
      }
    }
    setNodes(ns => ns.map(node => {
      const def = defByType[node.data?.componentType]
      if (!def) return node          // unknown type — leave untouched
      return {
        ...node,
        data: {
          ...node.data,
          inputHandles:  def.inputs  || [],
          outputHandles: def.outputs || [],
        },
      }
    }))
    setSaved(false)
  }

  // Mark dirty whenever nodes/edges change after initial load
  const isFirst = useRef(true)
  useEffect(() => {
    if (isFirst.current) { isFirst.current = false; return }
    if (layoutSkip.current) return
    setSaved(false)
  }, [nodes, edges])

  const pulseDur = replaying ? `${Math.round(2200 / replaySpeed)}ms` : '2200ms'
  const displayEdges = edges.map(e => ({
    ...e,
    type: 'smoothstep',
    ...(activeEdges.has(e.id)
      ? { animated: true, style: { ...e.style, stroke: '#c4b5fd', strokeWidth: 3.5 } }
      : {}),
  }))
  const displayNodes = nodes.map(n => ({
    ...n,
    data: { ...n.data, isActive: activeNodes.has(n.id), pulseDur, layoutDir },
  }))

  return (
    <div className="se-layout">
      <header className="se-header">
        <button className="se-back" onClick={() => navigate(`/projects/${project.id}`)}>
          ← {project.name}
        </button>
        <span className="se-sep">/</span>
        <span className="se-scene-name">{scene.name}</span>
        <div className="se-header-right">
          {!saved && <span className="se-unsaved">Unsaved changes</span>}
          <button className="se-sync-btn" onClick={syncNodes}
            title="Update all nodes to the latest component definition">
            ↺ Sync nodes
          </button>
          <button
            className="se-layout-btn"
            onClick={toggleLayout}
            title={layoutDir === 'LR' ? 'Switch to vertical layout' : 'Switch to horizontal layout'}>
            {layoutDir === 'LR' ? '↔ Horizontal' : '↕ Vertical'}
          </button>
          <button
            className={`se-debug-btn ${debugMode ? 'se-debug-on' : ''}`}
            onClick={toggleDebug}
            title="Toggle signal flow visualization">
            🔍 Debug{debugMode ? ' ON' : ''}
          </button>
          <button className="primary" onClick={save} disabled={saving || saved}>
            {saving ? 'Saving…' : saved ? '✓ Saved' : 'Save'}
          </button>
        </div>
      </header>

      <div className="se-body">
        <div className="se-canvas-wrap">
          <div className="se-canvas-rf" ref={reactFlowWrapper}>
          <ReactFlow
            nodes={displayNodes}
            edges={displayEdges}
            onNodesChange={e => { onNodesChange(e) }}
            onEdgesChange={e => { onEdgesChange(e) }}
            onConnect={onConnect}
            onNodeClick={onNodeClick}
            nodeTypes={nodeTypes}
            defaultEdgeOptions={{ type: 'smoothstep', animated: true }}
            fitView
            deleteKeyCode="Delete"
          >
            <Background color="#2a2a35" gap={20} />
            <Controls />
            <MiniMap
              nodeColor={n => n.data?.color || '#7c5cbf'}
              maskColor="rgba(0,0,0,.6)"
              style={{ background: '#18181b', border: '1px solid #2e2e35' }}
            />
          </ReactFlow>

          {nodes.length === 0 && (
            <div className="se-canvas-hint">
              <div>Drag components from the panel →</div>
            </div>
          )}
          </div>

          {debugMode && (
            <div className="se-log-panel">
              <div className="se-log-header" onClick={() => setLogVisible(v => !v)}>
                <span>🔍 Signal Log ({logEntries.length})</span>
                <div className="se-log-actions" onClick={e => e.stopPropagation()}>
                  <label className="se-log-speed">
                    {replaySpeed}×
                    <input type="range" min="0.1" max="1" step="0.1"
                      value={replaySpeed}
                      onChange={e => setReplaySpeed(parseFloat(e.target.value))} />
                  </label>
                  <button onClick={startReplay} disabled={replaying || logEntries.length === 0}>
                    {replaying ? '⏵ Replaying…' : '▶ Replay'}
                  </button>
                  <button onClick={clearLog} disabled={logEntries.length === 0}>✕ Clear</button>
                  <span className="se-log-chevron">{logVisible ? '▼' : '▲'}</span>
                </div>
              </div>
              {logVisible && (
                <div className="se-log-entries">
                  {logEntries.slice(-80).reverse().map((e, i) => (
                    <div key={i} className={`se-log-entry se-log-${e.type}`}>
                      <span className="se-log-t">+{e.t}ms</span>
                      <span className="se-log-icon">{e.type === 'node' ? '◈' : e.type === 'console' ? '📝' : '→'}</span>
                      <span className="se-log-label">{labelFor(e)}</span>
                      {(e.type === 'edge' || e.type === 'console') && e.value != null && (
                        <span className="se-log-value">
                          {String(e.value).length > 20
                            ? String(e.value).slice(0, 20) + '…'
                            : String(e.value)}
                        </span>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        <div className="se-right-panel">
          <ComponentLibrary library={library} />
        </div>
      </div>

      <NodeModal
        node={modalNode}
        library={library}
        scenes={project.scenes || []}
        onChange={updateParam}
        onClose={() => setModalNode(null)}
        onDelete={deleteNode}
      />
    </div>
  )
}

export default function SceneEditorPage() {
  const { projectId, sceneId } = useParams()
  const navigate = useNavigate()
  const [project, setProject] = useState(null)
  const [scene,   setScene]   = useState(null)
  const [library, setLibrary] = useState(null)
  const [error,   setError]   = useState('')

  useEffect(() => {
    Promise.all([api.getProject(projectId), api.getComponents()])
      .then(([p, lib]) => {
        setProject(p)
        setLibrary(lib)
        const s = (p.scenes || []).find(s => s.id === sceneId)
        if (!s) { setError('Scene not found'); return }
        setScene(s)
      })
      .catch(err => setError(err.message))
  }, [projectId, sceneId])

  if (error) return (
    <div style={{ padding: 32, color: 'var(--danger)' }}>
      {error} — <button onClick={() => navigate('/projects')}>Back</button>
    </div>
  )
  if (!project || !scene || !library) return (
    <div style={{ padding: 32, color: 'var(--muted)' }}>Loading…</div>
  )

  return (
    <ReactFlowProvider>
      <EditorInner project={project} scene={scene} library={library} />
    </ReactFlowProvider>
  )
}
