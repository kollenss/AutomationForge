import './ComponentLibrary.css'

function onDragStart(e, compDef) {
  e.dataTransfer.setData('application/gameforge', JSON.stringify(compDef))
  e.dataTransfer.effectAllowed = 'copy'
}

export default function ComponentLibrary({ library }) {
  if (!library) return <div className="cl-loading">Loading…</div>

  return (
    <div className="cl-root">
      <div className="cl-title">Components</div>
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
