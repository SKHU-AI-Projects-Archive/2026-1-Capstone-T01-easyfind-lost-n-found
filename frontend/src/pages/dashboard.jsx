import { useLocation, useNavigate } from 'react-router-dom'
import { useState, useEffect, useRef, useCallback } from 'react'

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL
const apiPort = import.meta.env.VITE_API_PORT
const launcherPort = import.meta.env.VITE_LAUNCHER_PORT

function Dashboard() {
  const location = useLocation()
  const navigate = useNavigate()
  const focusCam = location.state?.focusCam || null
  const [modalCam, setModalCam] = useState(null)
  const [zoom, setZoom] = useState(1)

  const [cams, setCams] = useState([])
  const [camStatus, setCamStatus] = useState({})
  const [isRunning, setIsRunning] = useState(false)
  const [launcherOnline, setLauncherOnline] = useState(false)
  const [actionLoading, setActionLoading] = useState(false)
  const [configs, setConfigs] = useState([])
  const [selectedConfig, setSelectedConfig] = useState('')

  const [position, setPosition] = useState({ x: 0, y: 0 })
  const [isDragging, setIsDragging] = useState(false)
  const dragStart = useRef({ x: 0, y: 0 })
  const positionRef = useRef({ x: 0, y: 0 })
  const videoContainerRef = useRef(null)

  useEffect(() => {
    const fetchCameras = async () => {
      try {
        const response = await fetch(`${apiBaseUrl}:${apiPort}/api/cameras`)
        const data = await response.json()
        const dynamicCams = data.cameras.map(name => ({
          id: name,
          name: name,
          status: 'Normal',
          statusColor: '#22c55e',
          msg: 'Live stream active'
        }))
        setCams(dynamicCams)
      } catch (error) {
        console.error("Failed to fetch cameras:", error)
      }
    }

    const fetchStatus = async () => {
      try {
        const res = await fetch(`${apiBaseUrl}:${apiPort}/api/status`)
        const data = await res.json()
        setCamStatus(data.pipelines || {})
      } catch (err) {}
    }

    const fetchLauncher = async () => {
      try {
        const res = await fetch(`${apiBaseUrl}:${launcherPort}/api/launcher/status`)
        if (res.ok) {
          const data = await res.json()
          setIsRunning(data.running)
          setSelectedConfig(data.config)
          setLauncherOnline(true)
          // configs가 비어있을 때만 다시 가져옴
          setConfigs(prev => {
            if (prev.length === 0) {
              fetch(`${apiBaseUrl}:${launcherPort}/api/launcher/configs`)
                .then(r => r.ok ? r.json() : null)
                .then(d => d && setConfigs(d.configs))
                .catch(() => {})
            }
            return prev
          })
        } else {
          setLauncherOnline(false)
        }
      } catch {
        setLauncherOnline(false)
      }
    }

    fetchCameras()
    fetchStatus()
    fetchLauncher()
    const interval = setInterval(fetchCameras, 5000)
    const statusInterval = setInterval(fetchStatus, 2000)
    const launcherInterval = setInterval(fetchLauncher, 3000)
    return () => { clearInterval(interval); clearInterval(statusInterval); clearInterval(launcherInterval) }
  }, [])

  useEffect(() => {
    if (focusCam && cams.length > 0) {
      const cam = cams.find(c => c.id === focusCam)
      if (cam) handleOpenModal(cam)
      navigate('/', { replace: true, state: {} })
    }
  }, [focusCam, cams])

  const handleZoomIn = useCallback(() => {
    setZoom(z => Math.min(3, parseFloat((z + 0.1).toFixed(2))))
  }, [])

  const handleZoomOut = useCallback(() => {
    setZoom(z => {
      const newZoom = Math.max(1, parseFloat((z - 0.1).toFixed(2)))
      if (newZoom === 1) {
        setPosition({ x: 0, y: 0 })
        positionRef.current = { x: 0, y: 0 }
      }
      return newZoom
    })
  }, [])

  const handleZoomReset = useCallback(() => {
    setZoom(1)
    setPosition({ x: 0, y: 0 })
    positionRef.current = { x: 0, y: 0 }
  }, [])

  useEffect(() => {
    const el = videoContainerRef.current
    if (!el) return
    const onWheel = (e) => {
      e.preventDefault()
      if (e.deltaY < 0) handleZoomIn()
      else handleZoomOut()
    }
    el.addEventListener('wheel', onWheel, { passive: false })
    return () => el.removeEventListener('wheel', onWheel)
  }, [modalCam, handleZoomIn, handleZoomOut])

  const handleStart = async () => {
    setActionLoading(true)
    try {
      await fetch(`${apiBaseUrl}:${launcherPort}/api/launcher/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ config: selectedConfig }),
      })
    } finally {
      setActionLoading(false)
    }
  }

  const handleStop = async () => {
    setActionLoading(true)
    try {
      await fetch(`${apiBaseUrl}:${launcherPort}/api/launcher/stop`, { method: 'POST' })
      setCams([])
      setIsRunning(false)
    } finally {
      setActionLoading(false)
    }
  }

  const handleOpenModal = (cam) => {
    setModalCam(cam)
    handleZoomReset()
  }

  const handleMouseDown = (e) => {
    if (zoom <= 1) return
    setIsDragging(true)
    dragStart.current = {
      x: e.clientX - positionRef.current.x,
      y: e.clientY - positionRef.current.y,
    }
  }

  const handleMouseMove = (e) => {
    if (!isDragging) return
    const newX = e.clientX - dragStart.current.x
    const newY = e.clientY - dragStart.current.y
    positionRef.current = { x: newX, y: newY }
    setPosition({ x: newX, y: newY })
  }

  const handleMouseUp = () => {
    setIsDragging(false)
  }

  return (
    <div style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '12px', height: '100%', overflow: 'auto' }}>

      {/* Stop 버튼 — 실행 중일 때만 표시 */}
      {launcherOnline && isRunning && (
        <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
          <button
            onClick={handleStop}
            disabled={actionLoading}
            style={{
              padding: '6px 16px',
              background: '#ef4444',
              color: 'white',
              border: 'none',
              borderRadius: '8px',
              fontSize: '13px',
              fontWeight: '600',
              cursor: actionLoading ? 'not-allowed' : 'pointer',
              opacity: actionLoading ? 0.6 : 1,
            }}
          >
            {actionLoading ? '...' : 'Stop System'}
          </button>
        </div>
      )}

      {/* Stat Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
        {[
          { label: <><span style={{ color: '#f59e0b' }}>Suspected</span> Lost Items</>, key: 'SUSPECTED', color: '#f59e0b' },
          { label: <><span style={{ color: '#ef4444' }}>Confirmed</span> Lost Items</>, key: 'LOST', color: '#ef4444' },
        ].map((card) => (
          <div key={card.key} style={{ background: 'var(--bg-card)', borderRadius: '10px', padding: '16px 20px', border: '1px solid var(--border-color)' }}>
            <div style={{ fontSize: '13px', fontWeight: '700', color: 'var(--text-secondary)', marginBottom: '10px' }}>{card.label}</div>
            {Object.entries(camStatus).sort(([a], [b]) => a.localeCompare(b)).map(([cam, counts]) => (
              <div key={cam} style={{ display: 'flex', justifyContent: 'space-between', fontSize: '14px', color: 'var(--text-secondary)', marginTop: '6px' }}>
                <span>{cam}</span>
                <span style={{ fontWeight: '700', fontSize: '16px', color: card.color }}>{counts[card.key] || 0}</span>
              </div>
            ))}
          </div>
        ))}
      </div>

      {/* CCTV Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', flex: 1 }}>
        {cams.map((cam) => (
          <div key={cam.id}
            onClick={() => handleOpenModal(cam)}
            style={{
              background: '#111827',
              borderRadius: '10px',
              padding: '12px',
              display: 'flex',
              flexDirection: 'column',
              gap: '8px',
              border: cam.status === 'Confirmed' ? '1px solid #ef4444' : '1px solid transparent',
              cursor: 'pointer',
            }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ color: '#9ca3af', fontSize: '12px' }}>{cam.name}</span>
              <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                {camStatus[cam.id]?.SUSPECTED > 0 && (
                  <span style={{ background: '#f59e0b', color: '#1a1f2e', fontSize: '10px', padding: '1px 6px', borderRadius: '8px', fontWeight: '600' }}>S {camStatus[cam.id].SUSPECTED}</span>
                )}
                {camStatus[cam.id]?.LOST > 0 && (
                  <span style={{ background: '#ef4444', color: 'white', fontSize: '10px', padding: '1px 6px', borderRadius: '8px', fontWeight: '600' }}>L {camStatus[cam.id].LOST}</span>
                )}
                <span style={{ background: '#22c55e', color: 'white', fontSize: '10px', padding: '2px 6px', borderRadius: '8px' }}>● LIVE</span>
              </div>
            </div>
            <div style={{
              width: '100%',
              aspectRatio: '4 / 3',
              background: '#1f2937',
              borderRadius: '6px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              overflow: 'hidden'
            }}>
              <img
                src={`${apiBaseUrl}:${apiPort}/video_feed/${cam.id}`}
                alt={cam.name}
                style={{ width: '100%', height: '100%', objectFit: 'contain' }}
              />
            </div>
          </div>
        ))}
        {cams.length === 0 && (
          <div style={{ gridColumn: 'span 2', textAlign: 'center', padding: '60px 40px', color: 'var(--text-secondary)' }}>
            {launcherOnline && !isRunning ? (
              <div>
                <div style={{ fontSize: '15px', fontWeight: '600', marginBottom: '16px' }}>Detection system is not running</div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px', justifyContent: 'center', marginBottom: '16px' }}>
                  <span style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>Config</span>
                  <select
                    value={selectedConfig}
                    onChange={e => setSelectedConfig(e.target.value)}
                    style={{
                      padding: '7px 10px',
                      borderRadius: '8px',
                      border: '1px solid var(--border-color)',
                      background: 'var(--bg-input)',
                      color: 'var(--text-primary)',
                      fontSize: '13px',
                      cursor: 'pointer',
                      minWidth: '200px',
                    }}
                  >
                    <option value=''>Select config...</option>
                    {configs.map(c => (
                      <option key={c} value={`configs/${c}`}>{c}</option>
                    ))}
                  </select>
                </div>
                <button
                  onClick={handleStart}
                  disabled={actionLoading || !selectedConfig}
                  style={{
                    padding: '10px 28px',
                    background: '#22c55e',
                    color: 'white',
                    border: 'none',
                    borderRadius: '8px',
                    fontSize: '14px',
                    fontWeight: '600',
                    cursor: actionLoading || !selectedConfig ? 'not-allowed' : 'pointer',
                    opacity: actionLoading || !selectedConfig ? 0.6 : 1,
                  }}
                >
                  {actionLoading ? 'Starting...' : 'Start System'}

                </button>
              </div>
            ) : (
              <div>No active camera streams found.</div>
            )}
          </div>
        )}
      </div>

      {/* 카메라 모달 */}
      {modalCam && (
        <div onClick={() => setModalCam(null)} style={{
          position: 'fixed', top: 0, left: 0, width: '100vw', height: '100vh',
          background: 'rgba(0,0,0,0.7)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000,
        }}>
          <div onClick={e => e.stopPropagation()} style={{
            background: '#111827', borderRadius: '12px', padding: '20px', width: '90vw', maxWidth: '1400px',
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <span style={{ color: 'white', fontWeight: '600', fontSize: '15px' }}>{modalCam.name}</span>
                <span style={{ background: '#22c55e', color: 'white', fontSize: '10px', padding: '2px 6px', borderRadius: '8px' }}>● LIVE</span>
              </div>
              <button onClick={() => setModalCam(null)} style={{ background: 'none', border: 'none', color: '#9ca3af', fontSize: '20px', cursor: 'pointer' }}>✕</button>
            </div>

            <div
              ref={videoContainerRef}
              onMouseDown={handleMouseDown}
              onMouseMove={handleMouseMove}
              onMouseUp={handleMouseUp}
              onMouseLeave={handleMouseUp}
              style={{
                background: '#1f2937',
                borderRadius: '8px',
                height: '70vh',
                overflow: 'hidden',
                marginBottom: '12px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                cursor: zoom > 1 ? (isDragging ? 'grabbing' : 'grab') : 'default',
                userSelect: 'none',
              }}>
              <div style={{
                transform: `scale(${zoom}) translate(${position.x / zoom}px, ${position.y / zoom}px)`,
                transition: isDragging ? 'none' : 'transform 0.2s',
                width: '100%',
                height: '100%',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
              }}>
                <img src={`${apiBaseUrl}:${apiPort}/video_feed/${modalCam.id}`} alt={modalCam.name} style={{ width: '100%', height: '100%', objectFit: 'contain' }} />
              </div>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ color: '#9ca3af', fontSize: '12px' }}>Zoom: {Math.round(zoom * 100)}%</span>
                <button onClick={handleZoomOut} style={{
                  background: '#374151', color: 'white', border: 'none', borderRadius: '6px',
                  width: '32px', height: '32px', fontSize: '18px', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center'
                }}>−</button>
                <button onClick={handleZoomIn} style={{
                  background: '#374151', color: 'white', border: 'none', borderRadius: '6px',
                  width: '32px', height: '32px', fontSize: '18px', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center'
                }}>+</button>
                <button onClick={handleZoomReset} style={{
                  background: '#374151', color: '#9ca3af', border: 'none', borderRadius: '6px',
                  padding: '0 10px', height: '32px', fontSize: '12px', cursor: 'pointer'
                }}>Reset</button>
              </div>
            </div>
          </div>
        </div>
      )}

    </div>
  )
}

export default Dashboard
