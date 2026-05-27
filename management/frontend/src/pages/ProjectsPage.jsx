import { useState, useEffect } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { api } from '../api'
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

  useEffect(() => {
    api.listProjects().then(setProjects).catch(console.error).finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    if (projectId) {
      api.getProject(projectId).then(setActiveProject).catch(() => setActiveProject(null))
    } else {
      setActiveProject(null)
    }
  }, [projectId])

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

  return (
    <div className="pp-layout">
      <header className="pp-header">
        <div className="pp-logo">
          <span className="pp-logo-mark">⬡</span>
          <span className="pp-logo-name">GameForge</span>
        </div>
        {error && <span className="pp-error">{error}</span>}
      </header>

      <div className="pp-body">
        {/* ── Projects column ── */}
        <aside className="pp-projects-col">
          <div className="pp-col-head">
            <h2>Projects</h2>
            <button className="primary" onClick={() => setShowNewProject(v => !v)}>+ New</button>
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
                    {activeProject.scenes.map(s => (
                      <div
                        key={s.id}
                        className="pp-scene-card"
                        onClick={() => navigate(`/projects/${activeProject.id}/scenes/${s.id}`)}
                      >
                        <div className="pp-scene-icon">◈</div>
                        <div className="pp-scene-name">{s.name}</div>
                        <div className="pp-scene-meta">{(s.nodes || []).length} component{(s.nodes || []).length !== 1 ? 's' : ''}</div>
                        <button className="pp-delete-btn danger" onClick={e => deleteScene(s.id, e)}>✕</button>
                      </div>
                    ))}
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
