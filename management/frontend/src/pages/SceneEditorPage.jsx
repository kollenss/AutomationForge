import { useState, useEffect, useCallback, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  ReactFlow, Background, Controls, MiniMap,
  useNodesState, useEdgesState, addEdge, ReactFlowProvider, useReactFlow,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'

import { api } from '../api'
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


function EditorInner({ project, scene, library }) {
  const navigate = useNavigate()
  const reactFlowWrapper = useRef(null)
  const { screenToFlowPosition } = useReactFlow()
  const [nodes, setNodes, onNodesChange] = useNodesState(scene.nodes || [])
  const [edges, setEdges, onEdgesChange] = useEdgesState(scene.edges || [])
  const [modalNode, setModalNode] = useState(null)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(true)

  const onConnect = useCallback(params => setEdges(eds => addEdge({ ...params, animated: true }, eds)), [setEdges])

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
    setSaved(false)
  }, [nodes, edges])

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
            title="Uppdatera alla noder till senaste komponentdefinition">
            ↺ Sync noder
          </button>
          <button className="primary" onClick={save} disabled={saving || saved}>
            {saving ? 'Saving…' : saved ? '✓ Saved' : 'Save'}
          </button>
        </div>
      </header>

      <div className="se-body">
        <div className="se-canvas-wrap" ref={reactFlowWrapper}>
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={e => { onNodesChange(e) }}
            onEdgesChange={e => { onEdgesChange(e) }}
            onConnect={onConnect}
            onNodeClick={onNodeClick}
            nodeTypes={nodeTypes}
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

        <div className="se-right-panel">
          <ComponentLibrary library={library} />
        </div>
      </div>

      <NodeModal
        node={modalNode}
        library={library}
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
