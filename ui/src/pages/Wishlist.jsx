import { useState, useEffect } from "react";
import { FaHeart } from "react-icons/fa";

export default function WishlistPage() {
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize] = useState(20);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);

  // Fetch wishlisted products from the API
  const fetchWishlistedProducts = async (page = 1) => {
    try {
      setLoading(true);
      const url = `http://localhost:8000/api/products/wishlisted?page=${page}&page_size=${pageSize}`;

      const response = await fetch(url);
      if (!response.ok) {
        throw new Error("Failed to load wishlist products");
      }

      const data = await response.json();
      setProducts(data.items || []);
      setTotal(data.total || 0);
      setTotalPages(data.total_pages || 1);
      setCurrentPage(page);
      setError(null);
    } catch (err) {
      setError(err.message);
      setProducts([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchWishlistedProducts(1);
  }, []);

  // Handle removing item directly from Wishlist view
  const handleRemoveFromWishlist = async (productId) => {
    // Optimistic UI update: remove item from list immediately
    const originalProducts = [...products];
    setProducts((prev) => prev.filter((p) => p.product_id !== productId));
    setTotal((prev) => Math.max(0, prev - 1));

    try {
      const response = await fetch(
        `http://localhost:8000/api/wishlists/${productId}`,
        {
          method: "POST", // Toggle endpoint handles removal
          headers: {
            "Content-Type": "application/json",
          },
        }
      );

      if (!response.ok) {
        throw new Error("Failed to remove item from wishlist");
      }
    } catch (err) {
      console.error(err.message);
      // Revert if API call fails
      setProducts(originalProducts);
      setTotal(originalProducts.length);
    }
  };

  const handlePrevPage = () => {
    if (currentPage > 1) {
      fetchWishlistedProducts(currentPage - 1);
    }
  };

  const handleNextPage = () => {
    if (currentPage < totalPages) {
      fetchWishlistedProducts(currentPage + 1);
    }
  };

  return (
    <main className="main">
      <div className="wishlist-header">
        <h1>My Wishlist</h1>
        {!loading && <p>{total} saved {total === 1 ? "item" : "items"}</p>}
      </div>

      {loading && <p className="status">Loading wishlist...</p>}

      {error && <p className="status error">Error: {error}</p>}

      {!loading && !error && products.length === 0 && (
        <div className="empty-wishlist">
          <p className="status">Your wishlist is currently empty.</p>
        </div>
      )}

      {!loading && !error && products.length > 0 && (
        <>
          <div className="products-grid">
            {products.map((product) => (
              <div key={product.product_id} className="product-card">
                <div className="product-card-header">
                  <p className="product-id">{product.product_id}</p>
                  <button
                    className="heart-btn"
                    onClick={() => handleRemoveFromWishlist(product.product_id)}
                    title="Remove from wishlist"
                    style={{
                      background: "none",
                      border: "none",
                      cursor: "pointer",
                    }}
                  >
                    <FaHeart style={{ color: "#e63946", fontSize: "24px" }} />
                  </button>
                </div>

                <h3>{product.title}</h3>

                <p className={product.price ? "price" : "price-null"}>
                  {product.price
                    ? `$${parseFloat(product.price).toFixed(2)}`
                    : "No Price Available"}
                </p>
              </div>
            ))}
          </div>

          {totalPages > 1 && (
            <div className="pagination">
              <button
                onClick={handlePrevPage}
                disabled={currentPage === 1}
                className="pagination-btn"
              >
                ← Previous
              </button>
              <span className="pagination-info">
                Page {currentPage} of {totalPages}
              </span>
              <button
                onClick={handleNextPage}
                disabled={currentPage === totalPages}
                className="pagination-btn"
              >
                Next →
              </button>
            </div>
          )}
        </>
      )}
    </main>
  );
}