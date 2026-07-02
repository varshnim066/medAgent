import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Navbar from './components/Navbar'
import Dashboard from './pages/Dashboard'
import PatientsList from './pages/PatientsList'
import PatientDetail from './pages/PatientDetail'
import ReasoningPage from './pages/ReasoningPage'
import ApprovalHistory from './pages/ApprovalHistory'

export default function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen flex flex-col">
        <Navbar />
        <main className="flex-1 p-4 md:p-6 max-w-screen-2xl mx-auto w-full">
          <Routes>
            <Route path="/"               element={<Dashboard />} />
            <Route path="/patients"       element={<PatientsList />} />
            <Route path="/patient/:id"    element={<PatientDetail />} />
            <Route path="/reason/:patientId/:visitId" element={<ReasoningPage />} />
            <Route path="/history"        element={<ApprovalHistory />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}
