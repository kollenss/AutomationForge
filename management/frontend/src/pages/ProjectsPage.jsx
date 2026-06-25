import { useState, useEffect, useRef } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { api } from '../api'
import { socket } from '../socket'
import './ProjectsPage.css'

function formatDate(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('sv-SE', { day: 'numeric', month: 'short', year: 'numeric' })
}

export default function ProjectsPage() {
  const { projectId } = useParams()
  const navigate = useNavigate()

  const [projects, setProjects]         = useState([])
  const [activeProject, setActiveProject] = useState(null)
  const [loading, setLoading]           = useState(true)
  const [newProjectName, setNewProjectName]   = useState('')
  const [newProjectDesc, setNewProjectDesc]   = useState('')
  const [showNewProject, setShowNewProject]   = useState(false)
  const [newSceneName, setNewSceneName]       = useState('')
  const [showNewScene, setShowNewScene]       = useState(false)
  const [error, setError]               = useState('')
  const [notice, setNotice]             = useState('')
  const importInputRef                  = useRef(null)
  const [sceneStates, setSceneStates]   = useState({}) // scene_id → bool
  const [editingScene, setEditingScene] = useState(null) // scene_id being renamed
  const [editingName,  setEditingName]  = useState('')
  const [autostart, setAutostart]       = useState({ project_id: null, scene_id: null })

  useEffect(() => {
    api.listProjects().then(setProjects).catch(console.error).finally(() => setLoading(false))
    api.getAutostart().then(setAutostart).catch(() => {})
  }, [])

  useEffect(() => {
    if (projectId) {
      api.getProject(projectId).then(p => {
        setActiveProject(p)
        const states = {}
        for (const s of (p.scenes || [])) states[s.id] = s.active || false
        setSceneStates(states)
      }).catch(() => setActiveProject(null))
    } else {
      setActiveProject(null)
    }
  }, [projectId])

  useEffect(() => {
    const handler = ({ scene_id, active }) =>
      setSceneStates(prev => ({ ...prev, [scene_id]: active }))
    socket.on('scene_state', handler)
    return () => socket.off('scene_state', handler)
  }, [])

  function exportProjects() {
    if (projects.length === 0) { setError('No projects to export'); return }
    // Content-Disposition makes this a download, not a navigation.
    window.location.href = api.exportProjectsUrl()
  }

  async function onImportFile(e) {
    const file = e.target.files?.[0]
    e.target.value = ''                       // allow re-importing the same file
    if (!file) return
    setError(''); setNotice('')
    let bundle
    try {
      bundle = JSON.parse(await file.text())
    } catch {
      setError('Could not read file — not valid JSON')
      return
    }
    const incoming = Array.isArray(bundle.projects)
      ? bundle.projects
      : (bundle && bundle.id ? [bundle] : null)
    if (!incoming || incoming.length === 0) {
      setError('Not a GameForge project export')
      return
    }
    const existingIds = new Set(projects.map(p => p.id))
    const conflicts = incoming.filter(p => p && existingIds.has(p.id))
    let mode = 'skip'
    if (conflicts.length > 0) {
      mode = confirm(
        `${conflicts.length} of ${incoming.length} project(s) already exist here.\n\n` +
        'OK = overwrite them with the imported version\n' +
        'Cancel = keep existing, import only new projects'
      ) ? 'overwrite' : 'skip'
    }
    try {
      const r = await api.importProjects({ projects: incoming, mode })
      const list = await api.listProjects()
      setProjects(list)
      const parts = []
      if (r.added) parts.push(`${r.added} added`)
      if (r.overwritten) parts.push(`${r.overwritten} overwritten`)
      if (r.skipped) parts.push(`${r.skipped} skipped`)
      setNotice(`Imported: ${parts.join(', ') || 'nothing new'}`)
    } catch (err) { setError(err.message) }
  }

  async function createProject(e) {
    e.preventDefault()
    if (!newProjectName.trim()) return
    try {
      const p = await api.createProject({ name: newProjectName.trim(), description: newProjectDesc.trim() })
      setProjects(prev => [{ ...p, scene_count: 0 }, ...prev])
      setNewProjectName('')
      setNewProjectDesc('')
      setShowNewProject(false)
      navigate(`/projects/${p.id}`)
    } catch (err) { setError(err.message) }
  }

  async function deleteProject(id, e) {
    e.stopPropagation()
    if (!confirm('Delete this project?')) return
    await api.deleteProject(id)
    setProjects(prev => prev.filter(p => p.id !== id))
    if (projectId === id) navigate('/projects')
  }

  async function createScene(e) {
    e.preventDefault()
    if (!newSceneName.trim() || !activeProject) return
    try {
      const scene = await api.createScene(activeProject.id, { name: newSceneName.trim() })
      const updated = { ...activeProject, scenes: [...(activeProject.scenes || []), scene] }
      setActiveProject(updated)
      setNewSceneName('')
      setShowNewScene(false)
      navigate(`/projects/${activeProject.id}/scenes/${scene.id}`)
    } catch (err) { setError(err.message) }
  }

  async function deleteScene(sceneId, e) {
    e.stopPropagation()
    if (!confirm('Delete this scene?')) return
    await api.deleteScene(activeProject.id, sceneId)
    setActiveProject(prev => ({ ...prev, scenes: prev.scenes.filter(s => s.id !== sceneId) }))
  }

  async function renameScene(sceneId, newName) {
    const trimmed = newName.trim()
    if (!trimmed) return
    const scene = activeProject.scenes.find(s => s.id === sceneId)
    if (!scene || scene.name === trimmed) return
    try {
      await api.updateScene(activeProject.id, sceneId, { name: trimmed })
      setActiveProject(prev => ({
        ...prev,
        scenes: prev.scenes.map(s => s.id === sceneId ? { ...s, name: trimmed } : s)
      }))
    } catch (err) { setError(err.message) }
  }

  async function toggleSceneActive(sceneId, currentlyActive, e) {
    e.stopPropagation()
    try {
      if (currentlyActive) {
        await api.deactivateScene(activeProject.id, sceneId)
      } else {
        await api.activateScene(activeProject.id, sceneId)
      }
    } catch (err) { setError(err.message) }
  }

  function isStartupScene(sceneId) {
    return autostart.project_id === activeProject?.id && autostart.scene_id === sceneId
  }

  async function toggleStartup(sceneId, e) {
    e.stopPropagation()
    const next = isStartupScene(sceneId)
      ? { project_id: null, scene_id: null }                 // clear
      : { project_id: activeProject.id, scene_id: sceneId }  // set (replaces any other)
    try {
      setAutostart(await api.setAutostart(next))
    } catch (err) { setError(err.message) }
  }

  return (
    <div className="pp-layout">
      <header className="pp-header">
        <div className="pp-logo">
          <span className="pp-logo-mark">⬡</span>
          <span className="pp-logo-name">GameForge</span>
        </div>
        {error && <span className="pp-error">{error}</span>}
        {notice && <span className="pp-notice">{notice}</span>}
      </header>

      <div className="pp-body">
        {/* ── Projects column ── */}
        <aside className="pp-projects-col">
          <div className="pp-col-head">
            <h2>Projects</h2>
            <div className="pp-col-actions">
              <button title="Download all projects as a backup file" onClick={exportProjects}>Export</button>
              <button title="Restore projects from a backup file" onClick={() => importInputRef.current?.click()}>Import</button>
              <button className="primary" onClick={() => setShowNewProject(v => !v)}>+ New</button>
            </div>
            <input
              ref={importInputRef} type="file" accept="application/json,.json"
              style={{ display: 'none' }} onChange={onImportFile}
            />
          </div>

          {showNewProject && (
            <form className="pp-new-form" onSubmit={createProject}>
              <input
                autoFocus type="text" placeholder="Project name"
                value={newProjectName} onChange={e => setNewProjectName(e.target.value)}
              />
              <input
                type="text" placeholder="Description (optional)"
                value={newProjectDesc} onChange={e => setNewProjectDesc(e.target.value)}
              />
              <div className="pp-new-form-actions">
                <button type="submit" className="primary">Create</button>
                <button type="button" onClick={() => setShowNewProject(false)}>Cancel</button>
              </div>
            </form>
          )}

          {loading
            ? <p className="pp-muted">Loading…</p>
            : projects.length === 0
              ? <p className="pp-muted">No projects yet.</p>
              : projects.map(p => (
                  <div
                    key={p.id}
                    className={`pp-project-card ${projectId === p.id ? 'active' : ''}`}
                    onClick={() => navigate(`/projects/${p.id}`)}
                  >
                    <div className="pp-project-name">{p.name}</div>
                    {p.description && <div className="pp-project-desc">{p.description}</div>}
                    <div className="pp-project-meta">
                      <span>{p.scene_count} scene{p.scene_count !== 1 ? 's' : ''}</span>
                      <span>{formatDate(p.updated_at)}</span>
                    </div>
                    <button className="pp-delete-btn danger" onClick={e => deleteProject(p.id, e)}>✕</button>
                  </div>
                ))
          }
        </aside>

        {/* ── Scenes column ── */}
        <main className="pp-scenes-col">
          {!activeProject ? (
            <div className="pp-empty-state">
              <div className="pp-empty-icon">⬡</div>
              <div className="pp-empty-title">Select or create a project</div>
              <div className="pp-empty-sub">Projects group your hardware scenes together</div>
            </div>
          ) : (
            <>
              <div className="pp-col-head">
                <div>
                  <h2>{activeProject.name}</h2>
                  {activeProject.description && <p className="pp-project-desc">{activeProject.description}</p>}
                </div>
                <button className="primary" onClick={() => setShowNewScene(v => !v)}>+ New Scene</button>
              </div>

              {showNewScene && (
                <form className="pp-new-form" onSubmit={createScene}>
                  <input
                    autoFocus type="text" placeholder="Scene name, e.g. Floor 1 – The Plan"
                    value={newSceneName} onChange={e => setNewSceneName(e.target.value)}
                  />
                  <div className="pp-new-form-actions">
                    <button type="submit" className="primary">Create</button>
                    <button type="button" onClick={() => setShowNewScene(false)}>Cancel</button>
                  </div>
                </form>
              )}

              {(activeProject.scenes || []).length === 0
                ? <p className="pp-muted">No scenes yet. Add one to start designing.</p>
                : (
                  <div className="pp-scene-grid">
                    {activeProject.scenes.map(s => {
                      const active = sceneStates[s.id] || false
                      return (
                        <div
                          key={s.id}
                          className={`pp-scene-card ${active ? 'pp-scene-active' : ''}`}
                          onClick={() => navigate(`/projects/${activeProject.id}/scenes/${s.id}`)}
                        >
                          <div className="pp-scene-header">
                            <span className="pp-scene-icon">◈</span>
                            <button
                              className={`pp-startup-btn ${isStartupScene(s.id) ? 'pp-startup-on' : ''}`}
                              title={isStartupScene(s.id)
                                ? 'Starts on launch — click to unset'
                                : 'Start on launch (auto-activate when GameForge boots)'}
                              onMouseDown={e => e.stopPropagation()}
                              onClick={e => toggleStartup(s.id, e)}
                            >🚀</button>
                            <span className={`pp-scene-dot ${active ? 'pp-dot-on' : 'pp-dot-off'}`} title={active ? 'Active' : 'Inactive'} />
                          </div>
                          {editingScene === s.id ? (
                            <input
                              className="pp-scene-name-input"
                              autoFocus
                              value={editingName}
                              onChange={e => setEditingName(e.target.value)}
                              onBlur={() => { renameScene(s.id, editingName); setEditingScene(null) }}
                              onKeyDown={e => {
                                if (e.key === 'Enter') { renameScene(s.id, editingName); setEditingScene(null) }
                                if (e.key === 'Escape') setEditingScene(null)
                              }}
                              onClick={e => e.stopPropagation()}
                              onMouseDown={e => e.stopPropagation()}
                            />
                          ) : (
                            <div
                              className="pp-scene-name"
                              title="Click to rename"
                              onClick={e => { e.stopPropagation(); setEditingScene(s.id); setEditingName(s.name) }}
                            >{s.name}</div>
                          )}
                          <div className="pp-scene-meta">{(s.nodes || []).length} component{(s.nodes || []).length !== 1 ? 's' : ''}</div>
                          <button
                            className={`pp-activate-btn ${active ? 'pp-activate-on' : ''}`}
                            onMouseDown={e => e.stopPropagation()}
                            onClick={e => toggleSceneActive(s.id, active, e)}
                          >
                            {active ? 'Deactivate' : 'Activate'}
                          </button>
                          <button className="pp-delete-btn danger" onClick={e => deleteScene(s.id, e)}>✕</button>
                        </div>
                      )
                    })}
                  </div>
                )
              }
            </>
          )}
        </main>
      </div>
    </div>
  )
}
