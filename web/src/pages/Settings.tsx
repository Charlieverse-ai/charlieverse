import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'

export function SettingsPage() {
  const { data: health } = useQuery({
    queryKey: ['health'],
    queryFn: () => api.health(),
    refetchInterval: 5000,
  })

  const isHealthy = health?.status === 'healthy'

  return (
    <div>
      <div className="s-card">
        <div className="s-title">Server</div>
        <div className="s-row">
          <span className="s-label">Host</span>
          <span className="s-val">127.0.0.1</span>
        </div>
        <div className="s-row">
          <span className="s-label">Port</span>
          <span className="s-val">8765</span>
        </div>
        <div className="s-row">
          <span className="s-label">Status</span>
          <span className="s-status">
            <span
              className="s-status-dot"
              style={{ background: isHealthy ? '#12B76A' : '#F04438' }}
            />
            {isHealthy ? 'Running' : 'Disconnected'}
          </span>
        </div>
      </div>

      <div className="s-card">
        <div className="s-title">Data</div>
        <div className="s-row">
          <span className="s-label">Database</span>
          <span className="s-val">~/.charlieverse/charlie.db</span>
        </div>
        <div className="s-row">
          <span className="s-label">Embedding model</span>
          <span className="s-val">all-MiniLM-L6-v2</span>
        </div>
      </div>

      <div className="s-card">
        <div className="s-title">Maintenance</div>
        <div className="s-row">
          <span className="s-label">Rebuild all embeddings</span>
          <button className="s-btn secondary">Reembed</button>
        </div>
        <div className="s-row">
          <span className="s-label">Rebuild FTS indexes</span>
          <button className="s-btn secondary">Rebuild</button>
        </div>
        <div className="s-row">
          <span className="s-label">Export database</span>
          <button className="s-btn secondary">Export</button>
        </div>
      </div>
    </div>
  )
}
