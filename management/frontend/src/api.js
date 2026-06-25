const BASE = '/api'

async function req(method, path, body) {
  const res = await fetch(BASE + path, {
    method,
    headers: body ? { 'Content-Type': 'application/json' } : {},
    body: body ? JSON.stringify(body) : undefined,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: res.statusText }))
    throw new Error(err.error || res.statusText)
  }
  return res.json()
}

async function engine(path, body) {
  const res = await fetch(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body || {}),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: res.statusText }))
    throw new Error(err.error || res.statusText)
  }
  return res.json()
}

export const api = {
  getComponents:              ()           => req('GET',    '/components'),
  restartHardware:            ()           => req('POST',   '/hardware/restart'),
  hardwareStatus:             ()           => req('GET',    '/hardware/status'),
  getRelayState:              ()           => req('GET',    '/hardware/relay'),
  setRelay:   (channel, action)            => req('POST',   `/hardware/relay/${channel}/${action}`),
  listProjects:               ()           => req('GET',    '/projects'),
  createProject:              (data)       => req('POST',   '/projects', data),
  getProject:                 (id)         => req('GET',    `/projects/${id}`),
  updateProject:              (id, data)   => req('PUT',    `/projects/${id}`, data),
  deleteProject:              (id)         => req('DELETE', `/projects/${id}`),
  importProjects:             (data)       => req('POST',   '/projects/import', data),
  exportProjectsUrl:          ()           => `${BASE}/projects/export`,
  createScene:                (pid, data)  => req('POST',   `/projects/${pid}/scenes`, data),
  updateScene:                (pid, sid, data) => req('PUT', `/projects/${pid}/scenes/${sid}`, data),
  deleteScene:                (pid, sid)   => req('DELETE', `/projects/${pid}/scenes/${sid}`),
  activateScene:   (pid, sid) => engine('/engine/activate_scene',   { project_id: pid, scene_id: sid }),
  deactivateScene: (pid, sid) => engine('/engine/deactivate_scene', { project_id: pid, scene_id: sid }),
}
