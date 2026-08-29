import { useState, useEffect } from "react";

// Flatten hierarchical category tree into a list with depth information
function flattenCategories(tree, depth = 0) {
  const result = [];
  
  if (Array.isArray(tree)) {
    tree.forEach((node) => {
      result.push({ name: node.name, depth });
      if (node.children && node.children.length > 0) {
        result.push(...flattenCategories(node.children, depth + 1));
      }
    });
  }
  
  return result;
}

export default function Catalog() {
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize] = useState(20);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);
  const [selectedCategory, setSelectedCategory] = useState("");
  const [availableCategories, setAvailableCategories] = useState([]);
  const [categoriesLoading, setCategoriesLoading] = useState(true);

  // Fetch available categories on component mount
  useEffect(() => {
    const fetchCategories = async () => {
      try {
        setCategoriesLoading(true);
        const response = await fetch(
          "http://localhost:8000/api/products/debug/categories"
        );
        if (response.ok) {
          const data = await response.json();
          console.log("Categories fetched:", data);
          // Flatten the hierarchical structure
          const flattened = flattenCategories(data.categories || []);
          setAvailableCategories(flattened);
        } else {
          console.error(
            "Failed to fetch categories:",
            response.status,
            response.statusText
          );
        }
      } catch (err) {
        console.error("Failed to fetch categories:", err);
      } finally {
        setCategoriesLoading(false);
      }
    };

    fetchCategories();
  }, []);

  const fetchProducts = async (page = 1, category = "") => {
    try {
      setLoading(true);
      let url = `http://localhost:8000/api/products/list?page=${page}&page_size=${pageSize}`;
      if (category) {
        url += `&category=${encodeURIComponent(category)}`;
      }

      const response = await fetch(url);
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
    fetchProducts(1, selectedCategory);
  }, [selectedCategory]);

  const handlePrevPage = () => {
    if (currentPage > 1) {
      fetchProducts(currentPage - 1, selectedCategory);
    }
  };

  const handleNextPage = () => {
    if (currentPage < totalPages) {
      fetchProducts(currentPage + 1, selectedCategory);
    }
  };

  const handleCategoryChange = (e) => {
    setSelectedCategory(e.target.value);
  };

  return (
    <main className="main">
      <div className="filters-section">
        <div className="filter-group">
          <label htmlFor="category-filter">Filter by Category:</label>
          <select
            id="category-filter"
            value={selectedCategory}
            onChange={handleCategoryChange}
            className="category-select"
            disabled={categoriesLoading}
          >
            <option value="">All Categories</option>
            {availableCategories.map((cat, idx) => (
              <option key={`${cat.name}-${idx}`} value={cat.name}>
                {" - ".repeat(cat.depth)}{cat.name}
              </option>
            ))}
          </select>
        </div>
      </div>

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
