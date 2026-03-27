import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Login from './pages/Login'
import Dashboard from './pages/dashboard'
import DetectionHistory from './pages/DetectionHistory'
import Alerts from './pages/Alerts'
import Layout from './Layout'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Login />} />
        <Route path="/dashboard" element={<Layout><Dashboard /></Layout>} />
        <Route path="/detection-history" element={<Layout><DetectionHistory /></Layout>} />
        <Route path="/alerts" element={<Layout><Alerts /></Layout>} />
      </Routes>
    </BrowserRouter>
  )
}

export default App