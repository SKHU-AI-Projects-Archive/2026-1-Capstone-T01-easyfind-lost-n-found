import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Dashboard from './pages/dashboard'
import DetectionHistory from './pages/DetectionHistory'
import PreciseDection from './pages/PreciseDection'
import Alerts from './pages/Alerts'
import Settings from './pages/Settings'
import Layout from './Layout'
import { LanguageProvider } from './LanguageContext'

function App() {
  return (
    <LanguageProvider>
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="/dashboard" element={<Layout><Dashboard /></Layout>} />
        <Route path="/detection-history" element={<Layout><DetectionHistory /></Layout>} />
        <Route path="/alerts" element={<Layout><Alerts /></Layout>} />
        <Route path="/precise-detection" element={<Layout><PreciseDection /></Layout>} />
        <Route path="/settings" element={<Layout><Settings /></Layout>} />
      </Routes>
    </BrowserRouter>
    </LanguageProvider>
  )
}

export default App