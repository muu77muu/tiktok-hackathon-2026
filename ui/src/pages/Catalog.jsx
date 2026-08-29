import { useState, useEffect, useRef } from "react";
import { CiHeart } from "react-icons/ci";
import { FaHeart } from "react-icons/fa"; // Imported filled heart icon

// Flatten hierarchical category tree into a list with depth and path information
function flattenCategories(tree, depth = 0, parentPath = "") {
  const result = [];

  if (Array.isArray(tree)) {
    tree.forEach((node) => {
      const currentPath = parentPath
        ? `${parentPath} > ${node.name}`
        : node.name;
      result.push({ name: node.name, depth, path: currentPath });
      if (node.children && node.children.length > 0) {
        result.push(
          ...flattenCategories(node.children, depth + 1, currentPath),
        );
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
  const [categoryInput, setCategoryInput] = useState("");
  const [availableCategories, setAvailableCategories] = useState([]);
  const [categoriesLoading, setCategoriesLoading] = useState(true);
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const [wishlist, setWishlist] = useState([]); // State to store array of wishlisted product IDs
  const dropdownRef = useRef(null);

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsDropdownOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, []);

  // Fetch wishlist IDs on component mount
  useEffect(() => {
    const fetchWishlist = async () => {
      try {
        const response = await fetch("http://localhost:8000/api/wishlists");
        if (response.ok) {
          const data = await response.json();
          // Expecting data to be an array of IDs: ["id1", "id2"] or items containing IDs
          const wishlistIds = Array.isArray(data)
            ? data.map((item) =>
                typeof item === "string" ? item : item.parent_asin,
              )
            : [];
          setWishlist(wishlistIds);
        }
      } catch (err) {
        console.error("Failed to fetch wishlist:", err);
      }
    };

    fetchWishlist();
  }, []);

  // Fetch available categories on component mount
  useEffect(() => {
    const fetchCategories = async () => {
      try {
        setCategoriesLoading(true);
        const response = await fetch(
          "http://localhost:8000/api/products/debug/categories",
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
            response.statusText,
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

  const handleCategoryInputChange = (e) => {
    const value = e.target.value;
    setCategoryInput(value);
    setSelectedCategory(value);
    setIsDropdownOpen(true);
  };

  const handleSelectCategory = (catName) => {
    setCategoryInput(catName);
    setSelectedCategory(catName);
    setIsDropdownOpen(false);
  };

  const handleClearCategory = () => {
    setCategoryInput("");
    setSelectedCategory("");
    setIsDropdownOpen(false);
  };

  const handleWishlist = async (product_id) => {
    try {
      const url = `http://localhost:8000/api/wishlists/${product_id}`;

      const response = await fetch(url, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
      });

      if (!response.ok) {
        throw new Error("Failed to update wishlist");
      }
      setWishlist((prevWishlist) =>
        prevWishlist.includes(product_id)
          ? prevWishlist.filter((id) => id !== product_id)
          : [...prevWishlist, product_id],
      );
    } catch (err) {
      console.error(err.message);
      // Revert state if the request fails
      setWishlist((prevWishlist) =>
        prevWishlist.includes(product_id)
          ? prevWishlist.filter((id) => id !== product_id)
          : [...prevWishlist, product_id],
      );
    }
  };

  const filteredCategories = availableCategories.filter(
    (cat) =>
      cat.name.toLowerCase().includes(categoryInput.toLowerCase()) ||
      cat.path.toLowerCase().includes(categoryInput.toLowerCase()),
  );

  return (
    <main className="main">
      <div className="filters-section">
        <div className="filter-group">
          <label htmlFor="category-filter">Filter by Category:</label>
          <div className="category-combobox" ref={dropdownRef}>
            <div className="category-input-wrapper">
              <input
                id="category-filter"
                type="text"
                value={categoryInput}
                onChange={handleCategoryInputChange}
                onFocus={() => setIsDropdownOpen(true)}
                placeholder="Type or select category..."
                className="category-input"
                disabled={categoriesLoading}
                autoComplete="off"
              />
              {categoryInput && (
                <button
                  type="button"
                  className="category-clear-btn"
                  onClick={handleClearCategory}
                  title="Clear category filter"
                >
                  ✕
                </button>
              )}
            </div>

            {isDropdownOpen && (
              <ul className="category-dropdown">
                <li
                  className={`category-dropdown-item ${
                    selectedCategory === "" ? "selected" : ""
                  }`}
                  onClick={() => handleSelectCategory("")}
                >
                  All Categories
                </li>
                {filteredCategories.length > 0 ? (
                  filteredCategories.map((cat, idx) => (
                    <li
                      key={`${cat.name}-${idx}`}
                      className={`category-dropdown-item ${
                        selectedCategory === cat.name ? "selected" : ""
                      }`}
                      style={{ paddingLeft: `${12 + cat.depth * 16}px` }}
                      onClick={() => handleSelectCategory(cat.name)}
                    >
                      <span className="category-item-text">
                        {cat.depth > 0 && (
                          <span className="depth-indent">
                            {"\u00A0\u00A0".repeat(cat.depth)}
                          </span>
                        )}
                        {cat.name}
                      </span>
                    </li>
                  ))
                ) : (
                  <li className="category-dropdown-item no-results">
                    No matching categories found
                  </li>
                )}
              </ul>
            )}
          </div>
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
            {products.map((product) => {
              const isWishlisted = wishlist.includes(product.product_id);

              return (
                <div key={product.product_id} className="product-card">
                  <p className="product-id">
                    {product.product_id}{" "}
                    <span className="category-subtitle">
                      (
                      {(() => {
                        try {
                          const categoryStr = product.category.replace(
                            /'/g,
                            '"',
                          );
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
                  <button
                    className="heart-btn"
                    onClick={() => handleWishlist(product.product_id)}
                    style={{
                      background: "none",
                      border: "none",
                      cursor: "pointer",
                    }}
                  >
                    {isWishlisted ? (
                      <FaHeart style={{ color: "#e63946", fontSize: "24px" }} />
                    ) : (
                      <CiHeart style={{ color: "#989595", fontSize: "28px" }} />
                    )}
                  </button>
                </div>
              );
            })}
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
