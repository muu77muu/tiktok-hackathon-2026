import { useState, useEffect } from "react";

export default function Catalog() {
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize] = useState(20);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);

  const fetchProducts = async (page = 1) => {
    try {
      setLoading(true);
      const response = await fetch(
        `http://localhost:8000/api/products/list?page=${page}&page_size=${pageSize}`
      );
      if (!response.ok) {
        throw new Error("Failed to fetch products");
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
    fetchProducts(1);
  }, []);

  const handlePrevPage = () => {
    if (currentPage > 1) {
      fetchProducts(currentPage - 1);
    }
  };

  const handleNextPage = () => {
    if (currentPage < totalPages) {
      fetchProducts(currentPage + 1);
    }
  };

  return (
    <main className="main">
      {loading && <p className="status">Loading products...</p>}

      {error && <p className="status error">Error: {error}</p>}

      {!loading && !error && products.length === 0 && (
        <p className="status">No products found</p>
      )}

      {!loading && !error && products.length > 0 && (
        <>
          <div className="products-grid">
            {products.map((product) => (
              <div key={product.product_id} className="product-card">
                <p className="product-id">
                  {product.product_id}{" "}
                  <span className="category-subtitle">
                    (
                    {(() => {
                      try {
                        const categoryStr = product.category.replace(/'/g, '"');
                        const categories = JSON.parse(categoryStr);
                        return categories.slice(-1);
                      } catch (e) {
                        return product.category;
                      }
                    })()}
                    )
                  </span>
                </p>
                <h3>{product.title}</h3>
                <p className={product.price ? "price" : "price-null"}>
                  {product.price
                    ? `$${parseFloat(product.price).toFixed(2)}`
                    : "No Price Available"}
                </p>
              </div>
            ))}
          </div>

          <div className="pagination">
            <button
              onClick={handlePrevPage}
              disabled={currentPage === 1}
              className="pagination-btn"
            >
              ← Previous
            </button>
            <span className="pagination-info">
              Page {currentPage} of {totalPages} (Total: {total} products)
            </span>
            <button
              onClick={handleNextPage}
              disabled={currentPage === totalPages}
              className="pagination-btn"
            >
              Next →
            </button>
          </div>
        </>
      )}
    </main>
  );
}
