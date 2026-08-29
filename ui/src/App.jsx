import { useState } from 'react'
import Header from './components/Header'
import Home from './pages/Home'
import Catalog from './pages/Catalog'
import './App.css'

function App() {
  const [currentPage, setCurrentPage] = useState('home')

  return (
    <div className="app">
      <Header currentPage={currentPage} setCurrentPage={setCurrentPage} />
      {currentPage === 'home' && <Home />}
      {currentPage === 'catalog' && <Catalog />}
    </div>
  )
}

export default App
