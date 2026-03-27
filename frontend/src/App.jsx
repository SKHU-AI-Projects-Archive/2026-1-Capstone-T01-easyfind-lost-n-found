import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Login from './pages/Login'
import Dashboard from './pages/dashboard'
import DetectionHistory from './pages/DetectionHistory'
import Layout from './Layout'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Login />} />
        <Route path="/dashboard" element={<Layout><Dashboard /></Layout>} />
        <Route path="/detection-history" element={<Layout><DetectionHistory /></Layout>} />
      </Routes>
    </BrowserRouter>
  )
}

export default App