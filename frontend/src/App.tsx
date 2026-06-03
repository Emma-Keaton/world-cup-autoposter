import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import ContentQueue from './pages/ContentQueue'
import Competitors from './pages/Competitors'
import Analytics from './pages/Analytics'
import Settings from './pages/Settings'
import ContentDetail from './pages/ContentDetail'

function App() {
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<Dashboard />} />
        <Route path="queue" element={<ContentQueue />} />
        <Route path="competitors" element={<Competitors />} />
        <Route path="analytics" element={<Analytics />} />
        <Route path="settings" element={<Settings />} />
        <Route path="content/:id" element={<ContentDetail />} />
      </Route>
    </Routes>
  )
}

export default App