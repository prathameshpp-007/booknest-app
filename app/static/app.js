// BookNest - Modern Vanilla JavaScript Frontend

document.addEventListener("DOMContentLoaded", () => {
  // DOM Elements - Search and Filters
  const searchInput = document.getElementById("search-input");
  const clearSearchBtn = document.getElementById("clear-search-btn");
  const categoryFilter = document.getElementById("category-filter");
  const clearAllFiltersBtn = document.getElementById("clear-all-filters-btn");
  const resultsCount = document.getElementById("results-count");
  const bookGrid = document.getElementById("book-grid");
  const emptyState = document.getElementById("empty-state");
  const resetFiltersBtn = document.getElementById("reset-filters-btn");
  const notificationBanner = document.getElementById("notification-banner");

  // DOM Elements - Add Book Modal & Form
  const addBookModal = document.getElementById("add-book-modal");
  const openAddBtns = document.querySelectorAll(".btn-open-add");
  const closeAddModalBtn = document.getElementById("close-add-modal-btn");
  const cancelAddModalBtn = document.getElementById("cancel-add-modal-btn");
  const addBookForm = document.getElementById("add-book-form");
  const titleInput = document.getElementById("book-title");
  const authorInput = document.getElementById("book-author");
  const categoryInput = document.getElementById("book-category");
  const priceInput = document.getElementById("book-price");
  const categoryDatalist = document.getElementById("category-suggestions");
  const submitBtn = document.getElementById("submit-btn");

  const titleError = document.getElementById("title-error");
  const authorError = document.getElementById("author-error");
  const categoryError = document.getElementById("category-error");
  const priceError = document.getElementById("price-error");

  // DOM Elements - Delete Modal
  const deleteModal = document.getElementById("delete-modal");
  const deleteBookTitle = document.getElementById("delete-book-title");
  const cancelDeleteBtn = document.getElementById("cancel-delete-btn");
  const confirmDeleteBtn = document.getElementById("confirm-delete-btn");
  const closeDeleteModalX = document.getElementById("close-delete-modal-x");

  // DOM Elements - Mobile Navigation
  const mobileToggleBtn = document.getElementById("mobile-toggle-btn");
  const mobileMenu = document.getElementById("mobile-menu");

  // State
  let pendingDeleteId = null;
  let searchDebounceTimer = null;
  let notificationTimer = null;

  // Initialize
  init();

  async function init() {
    await loadCategories();
    await fetchBooks();
    setupEventListeners();
  }

  function setupEventListeners() {
    // ------------------------------------------------------------------------
    // Search & Filter Listeners
    // ------------------------------------------------------------------------
    searchInput.addEventListener("input", () => {
      if (searchInput.value.trim().length > 0) {
        clearSearchBtn.classList.remove("hidden");
      } else {
        clearSearchBtn.classList.add("hidden");
      }
      clearTimeout(searchDebounceTimer);
      searchDebounceTimer = setTimeout(() => {
        fetchBooks();
      }, 250);
    });

    clearSearchBtn.addEventListener("click", () => {
      searchInput.value = "";
      clearSearchBtn.classList.add("hidden");
      searchInput.focus();
      fetchBooks();
    });

    categoryFilter.addEventListener("change", () => {
      fetchBooks();
    });

    if (clearAllFiltersBtn) {
      clearAllFiltersBtn.addEventListener("click", resetAllFilters);
    }

    resetFiltersBtn.addEventListener("click", resetAllFilters);

    // ------------------------------------------------------------------------
    // Add Book Modal Listeners
    // ------------------------------------------------------------------------
    openAddBtns.forEach((btn) => {
      btn.addEventListener("click", openAddModal);
    });

    if (closeAddModalBtn) {
      closeAddModalBtn.addEventListener("click", closeAddModal);
    }
    if (cancelAddModalBtn) {
      cancelAddModalBtn.addEventListener("click", closeAddModal);
    }

    addBookModal.addEventListener("click", (e) => {
      if (e.target === addBookModal) {
        closeAddModal();
      }
    });

    addBookForm.addEventListener("submit", handleAddBook);

    // Real-time error clearance
    titleInput.addEventListener("input", () => clearFieldError(titleInput, titleError));
    authorInput.addEventListener("input", () => clearFieldError(authorInput, authorError));
    categoryInput.addEventListener("input", () => clearFieldError(categoryInput, categoryError));
    priceInput.addEventListener("input", () => clearFieldError(priceInput, priceError));

    // ------------------------------------------------------------------------
    // Delete Modal Listeners
    // ------------------------------------------------------------------------
    cancelDeleteBtn.addEventListener("click", closeDeleteModal);
    if (closeDeleteModalX) {
      closeDeleteModalX.addEventListener("click", closeDeleteModal);
    }
    confirmDeleteBtn.addEventListener("click", handleConfirmDelete);

    deleteModal.addEventListener("click", (e) => {
      if (e.target === deleteModal) {
        closeDeleteModal();
      }
    });

    // Global keyboard listener (Escape key closes open modals)
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") {
        if (!addBookModal.classList.contains("hidden")) closeAddModal();
        if (!deleteModal.classList.contains("hidden")) closeDeleteModal();
      }
    });
  }

  // --------------------------------------------------------------------------
  // Helpers & Actions
  // --------------------------------------------------------------------------
  function resetAllFilters() {
    searchInput.value = "";
    clearSearchBtn.classList.add("hidden");
    categoryFilter.value = "";
    fetchBooks();
  }

  function closeMobileMenu() {
    if (mobileMenu && !mobileMenu.classList.contains("hidden")) {
      mobileMenu.classList.add("hidden");
      mobileToggleBtn.setAttribute("aria-expanded", "false");
    }
  }

  function openAddModal() {
    closeMobileMenu();
    addBookModal.classList.remove("hidden");
    setTimeout(() => {
      titleInput.focus();
    }, 50);
  }

  function closeAddModal() {
    addBookModal.classList.add("hidden");
    clearFieldError(titleInput, titleError);
    clearFieldError(authorInput, authorError);
    clearFieldError(categoryInput, categoryError);
    clearFieldError(priceInput, priceError);
  }

  // --------------------------------------------------------------------------
  // Category Loading
  // --------------------------------------------------------------------------
  async function loadCategories() {
    try {
      const response = await fetch("/api/categories");
      if (!response.ok) return;
      const categories = await response.json();

      const selectedCat = categoryFilter.value;

      categoryFilter.innerHTML = '<option value="">All Categories</option>';
      categoryDatalist.innerHTML = "";

      categories.forEach((cat) => {
        const option = document.createElement("option");
        option.value = cat;
        option.textContent = cat;
        if (cat === selectedCat) {
          option.selected = true;
        }
        categoryFilter.appendChild(option);

        const datalistOption = document.createElement("option");
        datalistOption.value = cat;
        categoryDatalist.appendChild(datalistOption);
      });
    } catch (err) {
      console.error("Failed to load categories:", err);
    }
  }

  // --------------------------------------------------------------------------
  // Books Fetching & Rendering
  // --------------------------------------------------------------------------
  async function fetchBooks() {
    const q = searchInput.value.trim();
    const category = categoryFilter.value.trim();

    const params = new URLSearchParams();
    if (q) params.set("q", q);
    if (category) params.set("category", category);

    resultsCount.textContent = "Updating catalog...";

    try {
      const response = await fetch(`/api/books?${params.toString()}`);
      if (!response.ok) {
        throw new Error(`Server responded with ${response.status}`);
      }
      const books = await response.json();
      renderBooks(books);
    } catch (err) {
      console.error("Failed to fetch books:", err);
      showNotification("Failed to load books. Please try refreshing.", "error");
      resultsCount.textContent = "Error loading books";
    }
  }

  function renderBooks(books) {
    bookGrid.innerHTML = "";

    if (!books || books.length === 0) {
      bookGrid.classList.add("hidden");
      emptyState.classList.remove("hidden");
      resultsCount.textContent = "Showing 0 books";
      return;
    }

    bookGrid.classList.remove("hidden");
    emptyState.classList.add("hidden");
    resultsCount.textContent = `Showing ${books.length} book${books.length === 1 ? "" : "s"}`;

    books.forEach((book) => {
      const card = createBookCard(book);
      bookGrid.appendChild(card);
    });
  }

  function createBookCard(book) {
    const card = document.createElement("article");
    card.className = "book-card";
    card.dataset.id = book.id;

    const formattedPrice = typeof book.price === "number" ? `$${book.price.toFixed(2)}` : `$${book.price}`;

    card.innerHTML = `
      <div class="card-top">
        <span class="category-badge">${escapeHtml(book.category || "General")}</span>
      </div>
      <div class="card-center">
        <h3 class="book-card-title">${escapeHtml(book.title)}</h3>
        <p class="book-card-author">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
            <circle cx="12" cy="7" r="4"></circle>
          </svg>
          ${escapeHtml(book.author)}
        </p>
      </div>
      <div class="card-bottom">
        <span class="book-price">${formattedPrice}</span>
        <button type="button" class="btn-delete-card" data-id="${book.id}" data-title="${escapeAttr(book.title)}" title="Delete book from catalog">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="3 6 5 6 21 6"></polyline>
            <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
          </svg>
          Delete
        </button>
      </div>
      <div class="card-actions">
        <button type="button" class="btn btn-secondary btn-add-cart" data-id="${book.id}">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
            <circle cx="9" cy="21" r="1"></circle>
            <circle cx="20" cy="21" r="1"></circle>
            <path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6"></path>
          </svg>
          <span>Add to Cart</span>
        </button>
        <button type="button" class="btn btn-primary btn-buy-now" data-id="${book.id}">
          <span>Buy Now</span>
        </button>
      </div>
    `;

    const delBtn = card.querySelector(".btn-delete-card");
    delBtn.addEventListener("click", () => {
      openDeleteModal(book.id, book.title);
    });

    const addCartBtn = card.querySelector(".btn-add-cart");
    addCartBtn.addEventListener("click", () => addBookToCart(book, addCartBtn));

    const buyNowBtn = card.querySelector(".btn-buy-now");
    buyNowBtn.addEventListener("click", () => buyNow(book, buyNowBtn));

    return card;
  }

  // --------------------------------------------------------------------------
  // Cart Actions
  // --------------------------------------------------------------------------
  async function addBookToCart(book, button) {
    const original = button.innerHTML;
    button.disabled = true;
    button.textContent = "Adding...";

    try {
      const response = await fetch("/api/cart", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ book_id: book.id, quantity: 1 }),
      });
      const data = await response.json();

      if (!response.ok) {
        showNotification(data.error || "Could not add book to cart", "error");
        return;
      }

      updateCartBadge(data.count);
      showNotification(`"${book.title}" added to your cart.`, "success");
    } catch (err) {
      console.error("Add to cart error:", err);
      showNotification("Network error while adding to cart. Please try again.", "error");
    } finally {
      button.disabled = false;
      button.innerHTML = original;
    }
  }

  async function buyNow(book, button) {
    const original = button.innerHTML;
    button.disabled = true;
    button.innerHTML = '<span class="btn-spinner"></span> Preparing...';

    try {
      const response = await fetch("/api/cart", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ book_id: book.id, quantity: 1 }),
      });
      const data = await response.json();

      if (!response.ok) {
        showNotification(data.error || "Could not start checkout", "error");
        button.disabled = false;
        button.innerHTML = original;
        return;
      }

      window.location.href = "/checkout";
    } catch (err) {
      console.error("Buy now error:", err);
      showNotification("Network error while starting checkout. Please try again.", "error");
      button.disabled = false;
      button.innerHTML = original;
    }
  }

  function updateCartBadge(count) {
    const badges = document.querySelectorAll("#nav-cart-count, #mobile-nav-cart-count");
    badges.forEach((badge) => {
      badge.textContent = count;
      if (count > 0) {
        badge.classList.remove("hidden");
      } else {
        badge.classList.add("hidden");
      }
    });
  }

  // --------------------------------------------------------------------------
  // Add Book Submission
  // --------------------------------------------------------------------------
  async function handleAddBook(e) {
    e.preventDefault();

    const title = titleInput.value.trim();
    const author = authorInput.value.trim();
    const category = categoryInput.value.trim();
    const priceStr = priceInput.value.trim();

    let hasError = false;

    if (!title) {
      showFieldError(titleInput, titleError, "Title is required");
      hasError = true;
    }
    if (!author) {
      showFieldError(authorInput, authorError, "Author is required");
      hasError = true;
    }
    if (!category) {
      showFieldError(categoryInput, categoryError, "Category is required");
      hasError = true;
    }

    const priceNum = parseFloat(priceStr);
    if (!priceStr || isNaN(priceNum) || priceNum <= 0) {
      showFieldError(priceInput, priceError, "Enter a valid price greater than $0.00");
      hasError = true;
    }

    if (hasError) return;

    const payload = {
      title,
      author,
      category,
      price: priceNum,
    };

    setSubmitLoading(true);

    try {
      const response = await fetch("/api/books", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });

      const data = await response.json();

      if (!response.ok) {
        showNotification(data.error || "Failed to add book", "error");
        return;
      }

      addBookForm.reset();
      closeAddModal();
      showNotification(`"${data.title}" was added successfully!`, "success");
      await loadCategories();
      await fetchBooks();
    } catch (err) {
      console.error("Add book error:", err);
      showNotification("Network error while adding book. Please try again.", "error");
    } finally {
      setSubmitLoading(false);
    }
  }

  // --------------------------------------------------------------------------
  // Delete Book Logic
  // --------------------------------------------------------------------------
  function openDeleteModal(id, title) {
    pendingDeleteId = id;
    deleteBookTitle.textContent = `"${title}"`;
    deleteModal.classList.remove("hidden");
    confirmDeleteBtn.focus();
  }

  function closeDeleteModal() {
    deleteModal.classList.add("hidden");
    pendingDeleteId = null;
  }

  async function handleConfirmDelete() {
    if (!pendingDeleteId) return;

    confirmDeleteBtn.disabled = true;
    confirmDeleteBtn.textContent = "Deleting...";

    try {
      const response = await fetch(`/api/books/${pendingDeleteId}`, {
        method: "DELETE",
      });

      const data = await response.json();

      if (!response.ok) {
        showNotification(data.error || "Failed to delete book", "error");
        return;
      }

      showNotification("Book deleted successfully.", "success");
      closeDeleteModal();
      await loadCategories();
      await fetchBooks();
    } catch (err) {
      console.error("Delete book error:", err);
      showNotification("Failed to delete book. Network error.", "error");
    } finally {
      confirmDeleteBtn.disabled = false;
      confirmDeleteBtn.textContent = "Delete Book";
    }
  }

  // --------------------------------------------------------------------------
  // Field Validation & Notification Helpers
  // --------------------------------------------------------------------------
  function showFieldError(inputElem, errorElem, message) {
    inputElem.classList.add("input-invalid");
    errorElem.textContent = message;
  }

  function clearFieldError(inputElem, errorElem) {
    inputElem.classList.remove("input-invalid");
    errorElem.textContent = "";
  }

  function setSubmitLoading(isLoading) {
    submitBtn.disabled = isLoading;
    const btnText = submitBtn.querySelector(".btn-text");
    if (btnText) {
      btnText.textContent = isLoading ? "Adding Book..." : "Add Book";
    }
  }

  function showNotification(message, type = "success") {
    clearTimeout(notificationTimer);
    notificationBanner.className = `notification-banner ${type}`;
    notificationBanner.textContent = message;
    notificationBanner.classList.remove("hidden");

    notificationTimer = setTimeout(() => {
      notificationBanner.classList.add("hidden");
    }, 4500);
  }

  function escapeHtml(str) {
    if (!str) return "";
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  function escapeAttr(str) {
    return escapeHtml(str);
  }
});
