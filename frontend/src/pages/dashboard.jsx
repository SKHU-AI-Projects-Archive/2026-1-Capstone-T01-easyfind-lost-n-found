import { useLocation, useNavigate } from 'react-router-dom'
// insert useRef to move zoom in the video 
import { useState, useEffect, useRef, useCallback } from 'react'

function Dashboard() {
  const location = useLocation()
  const navigate = useNavigate()
  const focusCam = location.state?.focusCam || null
  const [modalCam, setModalCam] = useState(null)
  const [zoom, setZoom] = useState(1)
  // zoom in, zoom out
  
  // 실제 백엔드 YAML 설정(Office_Cam, Hallway_Cam)에 맞춘 카메라 리스트
  //camera list from yaml file 
  const [cams, setCams] = useState([])
  const [camStatus, setCamStatus] = useState({})

  // 줌 및 드래그 상태 관리
  const [position, setPosition] = useState({ x: 0, y: 0 })
  const [isDragging, setIsDragging] = useState(false)
  const dragStart = useRef({ x: 0, y: 0 })
  const positionRef = useRef({ x: 0, y: 0 })
  const videoContainerRef = useRef(null)

  useEffect(() => {
    const fetchCameras = async () => {
      try {
        const response = await fetch('http://localhost:5000/api/cameras')
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
        const res = await fetch('http://localhost:5000/api/status')
        const data = await res.json()
        setCamStatus(data.pipelines || {})
      } catch (err) {}
    }

    fetchCameras()
    fetchStatus()
    const interval = setInterval(fetchCameras, 5000)
    const statusInterval = setInterval(fetchStatus, 2000)
    return () => { clearInterval(interval); clearInterval(statusInterval) }
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

  // 마우스 휠 이벤트 처리 (passive: false를 위해 useEffect에서 직접 등록)
  useEffect(() => {
    const el = videoContainerRef.current
    if (!el) return

    const onWheel = (e) => {
      e.preventDefault() // 페이지 스크롤 방지
      if (e.deltaY < 0) {
        handleZoomIn()
      } else {
        handleZoomOut()
      }
    }

    el.addEventListener('wheel', onWheel, { passive: false })
    return () => el.removeEventListener('wheel', onWheel)
  }, [modalCam, handleZoomIn, handleZoomOut])

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

      {/* Stat Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
        {[
          { label: 'Suspected Lost Items', key: 'SUSPECTED', color: '#f59e0b' },
          { label: 'Lost Items', key: 'LOST', color: '#ef4444' },
        ].map((card) => (
          <div key={card.key} style={{ background: 'white', borderRadius: '10px', padding: '16px 20px', border: '1px solid #e5e7eb' }}>
            <div style={{ fontSize: '12px', color: '#6b7280', marginBottom: '10px' }}>{card.label}</div>
            {Object.entries(camStatus).sort(([a], [b]) => a.localeCompare(b)).map(([cam, counts]) => (
              <div key={cam} style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', color: '#6b7280', marginTop: '2px' }}>
                <span>{cam}</span>
                <span style={{ fontWeight: '600', color: card.color }}>{counts[card.key] || 0}</span>
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
            {/* 동적 스트리밍 경로 적용 */}
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
                src={`http://localhost:5000/video_feed/${cam.id}`} 
                alt={cam.name} 
                style={{ width: '100%', height: '100%', objectFit: 'contain' }} 
              />
            </div>
            <div style={{ fontSize: '11px', color: cam.statusColor }}>{cam.status} — {cam.msg}</div>
          </div>
        ))}
        {cams.length === 0 && (
          <div style={{ gridColumn: 'span 2', textAlign: 'center', padding: '40px', color: '#6b7280' }}>
            No active camera streams found.
          </div>
        )}
      </div>

      {/* Right Panel (Alerts & Timeline) */}
      <div style={{ position: 'fixed', right: 0, top: '48px', width: '260px', background: 'white', borderLeft: '1px solid #e5e7eb', padding: '16px', display: 'flex', flexDirection: 'column', gap: '16px', height: 'calc(100vh - 48px)', overflow: 'auto' }}>
        <div>
          <div style={{ fontSize: '11px', fontWeight: '600', color: '#6b7280', marginBottom: '10px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Real-time Alerts</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {[
              { item: 'Luggage', cam: 'CAM-D3', time: '15:40', status: 'Confirmed', color: '#ef4444', bg: '#fef2f2' },
              { item: 'Backpack', cam: 'CAM-A2', time: '15:42', status: 'Suspected', color: '#f59e0b', bg: '#fffbeb' },
            ].map((alert, i) => (
              <div key={i} style={{ border: `1px solid #e5e7eb`, borderLeft: `3px solid ${alert.color}`, borderRadius: '0 8px 8px 0', padding: '10px', background: alert.bg }}>
                <div style={{ fontWeight: '600', fontSize: '13px' }}>{alert.item}</div>
                <div style={{ fontSize: '11px', color: '#6b7280', marginTop: '2px' }}>{alert.cam} · {alert.time}</div>
                <span style={{ fontSize: '11px', background: alert.color, color: 'white', padding: '2px 8px', borderRadius: '8px', display: 'inline-block', marginTop: '6px' }}>{alert.status}</span>
              </div>
            ))}
          </div>
        </div>

        <div>
          <div style={{ fontSize: '11px', fontWeight: '600', color: '#6b7280', marginBottom: '10px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Detection Timeline</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {[
              { time: '15:38', text: 'Luggage + person linked', color: '#9ca3af' },
              { time: '15:39', text: 'Person left, object fixed', color: '#9ca3af' },
              { time: '15:39', text: 'Suspected — timer started', color: '#f59e0b' },
              { time: '15:40', text: 'Confirmed lost item', color: '#ef4444' },
              { time: '15:42', text: 'Admin alert sent', color: '#3b82f6' },
            ].map((tl, i) => (
              <div key={i} style={{ display: 'flex', gap: '8px', alignItems: 'center', fontSize: '12px', color: '#6b7280' }}>
                <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: tl.color, flexShrink: 0 }}></div>
                <span style={{ color: tl.color, fontWeight: '500', minWidth: '36px' }}>{tl.time}</span>
                <span>{tl.text}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* 카메라 모달 (확대 보기) */}
      {modalCam && (
        <div onClick={() => setModalCam(null)} style={{
          position: 'fixed', top: 0, left: 0, width: '100vw', height: '100vh',
          background: 'rgba(0,0,0,0.7)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000,
        }}>
          <div onClick={e => e.stopPropagation()} style={{
            background: '#111827', borderRadius: '12px', padding: '20px', width: '800px',
          }}>
            {/* 모달 상단 */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <span style={{ color: 'white', fontWeight: '600', fontSize: '15px' }}>{modalCam.name}</span>
                <span style={{ background: '#22c55e', color: 'white', fontSize: '10px', padding: '2px 6px', borderRadius: '8px' }}>● LIVE</span>
              </div>
              <button onClick={() => setModalCam(null)} style={{ background: 'none', border: 'none', color: '#9ca3af', fontSize: '20px', cursor: 'pointer' }}>✕</button>
            </div>

            {/* 영상 영역 */}
            <div
              ref={videoContainerRef}
              onMouseDown={handleMouseDown}
              onMouseMove={handleMouseMove}
              onMouseUp={handleMouseUp}
              onMouseLeave={handleMouseUp}
              style={{
                background: '#1f2937',
                borderRadius: '8px',
                height: '380px',
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
                <img src={`http://localhost:5000/video_feed/${modalCam.id}`} alt={modalCam.name} style={{ width: '100%', height: '100%', objectFit: 'contain' }} />
              </div>
            </div>

            {/* 하단 컨트롤 */}
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div style={{ fontSize: '12px', color: modalCam.statusColor }}>{modalCam.status} — {modalCam.msg}</div>
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
