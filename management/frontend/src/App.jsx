import { Routes, Route, Navigate } from 'react-router-dom'
import { Component } from 'react'
import ProjectsPage from './pages/ProjectsPage'
import SceneEditorPage from './pages/SceneEditorPage'

class ErrorBoundary extends Component {
  state = { error: null }
  static getDerivedStateFromError(e) { return { error: e } }
  render() {
    if (this.state.error) return (
      <div style={{ padding: 32, color: '#e05252', fontFamily: 'monospace' }}>
        <h2>Render error</h2>
        <pre style={{ marginTop: 12, whiteSpace: 'pre-wrap', fontSize: 12 }}>
          {this.state.error.message}{'\n\n'}{this.state.error.stack}
        </pre>
        <button style={{ marginTop: 16 }} onClick={() => this.setState({ error: null })}>
          Try again
        </button>
      </div>
    )
    return this.props.children
  }
}

export default function App() {
  return (
    <ErrorBoundary>
      <Routes>
        <Route path="/" element={<Navigate to="/projects" replace />} />
        <Route path="/projects" element={<ProjectsPage />} />
        <Route path="/projects/:projectId/scenes/:sceneId" element={<SceneEditorPage />} />
        <Route path="/projects/:projectId" element={<ProjectsPage />} />
      </Routes>
    </ErrorBoundary>
  )
}
