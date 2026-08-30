export default function Header({ currentPage, setCurrentPage }) {
  return (
    <header className="header">
      <div className="header-content">
        <h1 className="logo">Shopping Copilot</h1>
        <nav className="nav">
          <button
            className={`nav-link ${currentPage === 'home' ? 'active' : ''}`}
            onClick={() => setCurrentPage('home')}
          >
            Home
          </button>
          <button
            className={`nav-link ${currentPage === 'catalog' ? 'active' : ''}`}
            onClick={() => setCurrentPage('catalog')}
          >
            Catalog
          </button>
          <button
            className={`nav-link ${currentPage === 'wishlist' ? 'active' : ''}`}
            onClick={() => setCurrentPage('wishlist')}
          >
            Wishlist
          </button>
          <button
            className={`nav-link ${currentPage === 'chatbox' ? 'active' : ''}`}
            onClick={() => setCurrentPage('chatbox')}
          >
            Chatbox
          </button>
                    <button
            className={`nav-link ${currentPage === 'compare' ? 'active' : ''}`}
            onClick={() => setCurrentPage('compare')}
          >
            Compare
          </button>
        </nav>
      </div>
    </header>
  )
}
