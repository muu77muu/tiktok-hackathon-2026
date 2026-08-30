import { useState, useEffect } from "react";
import { CiHeart } from "react-icons/ci";
import { FaHeart } from "react-icons/fa";

const HARDCODED_PRODUCT_A = "B0000ATC4O";
const HARDCODED_PRODUCT_B = "B0000CDZCO";

function TruncatedDescription({ value, maxLength = MAX_DESCRIPTION_LENGTH }) {
  const [isExpanded, setIsExpanded] = useState(false);
  const formattedText = formatFieldValue(value, " ");

  if (!formattedText) return <span>N/A</span>;

  const isOverLength = formattedText.length > maxLength;
  const displayText = isExpanded || !isOverLength 
    ? formattedText 
    : `${formattedText.substring(0, maxLength).trim()}...`;

  return (
    <div className="description-cell">
      <p style={{ margin: 0, whiteSpace: "pre-line" }}>{displayText}</p>
      {isOverLength && (
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="toggle-desc-btn"
        >
          {isExpanded ? "Show Less" : "Show More"}
        </button>
      )}
    </div>
  );
}

const takeOutDesc = (value) => {
  let parsed = value;
  if (typeof value === "string") {
    try {
      const normalizedJson = value.replace(/'/g, '"');
      parsed = JSON.parse(normalizedJson);
    } catch (e) {
      // If parsing fails, use original string
      parsed = value;
    }
  }

  // If array, flatten and join elements cleanly
  if (Array.isArray(parsed)) {
    const cleanItems = parsed
      .flat()
      .map((item) => String(item).trim())
      .filter(Boolean);
    return cleanItems.length > 0 ? cleanItems.join("\n") : "N/A";
  }

  return String(parsed);
};

// Helper function to extract and format arrays, stringified JSON arrays, or plain strings
const formatFieldValue = (value, delimiter = " > ") => {
  if (!value) return "N/A";

  let parsed = value;

  // Attempt to parse stringified JSON arrays (e.g., "['Electronics', 'Computers']")
  if (typeof value === "string") {
    try {
      const normalizedJson = value.replace(/'/g, '"');
      parsed = JSON.parse(normalizedJson);
    } catch (e) {
      // If parsing fails, use original string
      parsed = value;
    }
  }

  // If array, flatten and join elements cleanly
  if (Array.isArray(parsed)) {
    const cleanItems = parsed
      .flat()
      .map((item) => String(item).trim())
      .filter(Boolean);
    return cleanItems.length > 0 ? cleanItems.join(delimiter) : "N/A";
  }

  return String(parsed);
};

export default function CompareProducts() {
  const [productA, setProductA] = useState(null);
  const [productB, setProductB] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [wishlist, setWishlist] = useState([]);

  useEffect(() => {
    const fetchComparisonData = async () => {
      try {
        setLoading(true);

        const [resA, resB, resWishlist] = await Promise.all([
          fetch(`http://localhost:8000/api/products/${HARDCODED_PRODUCT_A}`),
          fetch(`http://localhost:8000/api/products/${HARDCODED_PRODUCT_B}`),
          fetch(`http://localhost:8000/api/wishlists`),
        ]);

        if (!resA.ok || !resB.ok) {
          throw new Error("Failed to fetch one or both comparison products.");
        }

        const dataA = await resA.json();
        const dataB = await resB.json();

        setProductA(dataA);
        setProductB(dataB);

        if (resWishlist.ok) {
          const wishlistData = await resWishlist.json();
          const wishlistIds = Array.isArray(wishlistData)
            ? wishlistData.map((item) =>
                typeof item === "string" ? item : item.parent_asin,
              )
            : [];
          setWishlist(wishlistIds);
        }

        setError(null);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchComparisonData();
  }, []);

  const handleWishlist = async (productId) => {
    setWishlist((prev) =>
      prev.includes(productId)
        ? prev.filter((id) => id !== productId)
        : [...prev, productId],
    );

    try {
      const response = await fetch(
        `http://localhost:8000/api/wishlists/${productId}`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
        },
      );

      if (!response.ok) {
        throw new Error("Failed to update wishlist");
      }
    } catch (err) {
      console.error(err);
      setWishlist((prev) =>
        prev.includes(productId)
          ? prev.filter((id) => id !== productId)
          : [...prev, productId],
      );
    }
  };

  if (loading)
    return (
      <main className="main">
        <p className="status">Loading comparison...</p>
      </main>
    );
  if (error)
    return (
      <main className="main">
        <p className="status error">Error: {error}</p>
      </main>
    );

  return (
    <main className="main compare-container">
      <h1 className="compare-title">Product Comparison</h1>

      <div className="compare-grid">
        {[productA, productB].map((product, idx) => {
          if (!product) return null;
          const isWishlisted = wishlist.includes(product.product_id);

          return (
            <div key={product.product_id || idx} className="compare-card">
              <div className="compare-card-header">
                <span className="product-id">{product.product_id}</span>
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
                    <CiHeart style={{ fontSize: "28px" }} />
                  )}
                </button>
              </div>

              <h2>{product.title}</h2>
              <p className={product.price ? "price" : "price-null"}>
                {product.price
                  ? `$${parseFloat(product.price).toFixed(2)}`
                  : "No Price Available"}
              </p>
            </div>
          );
        })}
      </div>

      <section className="compare-table-section">
        <h3>Feature Breakdown</h3>
        <table className="compare-table">
          <thead>
            <tr>
              <th>Attribute</th>
              <th>Product 1</th>
              <th>Product 2</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td className="attribute-name">Price</td>
              <td>
                {productA?.price
                  ? `$${parseFloat(productA.price).toFixed(2)}`
                  : "N/A"}
              </td>
              <td>
                {productB?.price
                  ? `$${parseFloat(productB.price).toFixed(2)}`
                  : "N/A"}
              </td>
            </tr>
            <tr>
              <td className="attribute-name">Rating</td>
              <td>
                {productA?.rating ? `⭐ ${productA.rating} / 5` : "No rating"}
              </td>
              <td>
                {productB?.rating ? `⭐ ${productB.rating} / 5` : "No rating"}
              </td>
            </tr>
            <tr>
              <td className="attribute-name">Category</td>
              {/* Formatted Category with " > " separator */}
              <td>{formatFieldValue(productA?.category, " > ")}</td>
              <td>{formatFieldValue(productB?.category, " > ")}</td>
            </tr>
            <tr>
              <td className="attribute-name">Store</td>
              <td>{productA?.metadata?.store || "N/A"}</td>
              <td>{productB?.metadata?.store || "N/A"}</td>
            </tr>
            <tr>
              <td className="attribute-name">Reviews Count</td>
              <td>{productA?.metadata?.rating_number ?? "N/A"}</td>
              <td>{productB?.metadata?.rating_number ?? "N/A"}</td>
            </tr>
            <tr>
              <td className="attribute-name">Description</td>
              {/* Formatted Description with line breaks or spaces */}
              <td><TruncatedDescription value={takeOutDesc(productA?.description)} maxLength={150} /></td>
              <td><TruncatedDescription value={takeOutDesc(productB?.description)} maxLength={150} /></td>
              
            </tr>
          </tbody>
        </table>
      </section>
    </main>
  );
}
