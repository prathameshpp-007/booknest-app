// BookNest - Vanilla JavaScript Frontend

document.addEventListener("DOMContentLoaded", () => {
  // DOM Elements
  const searchInput = document.getElementById("search-input");
  const clearSearchBtn = document.getElementById("clear-search-btn");
  const categoryFilter = document.getElementById("category-filter");
  const resultsCount = document.getElementById("results-count");
  const bookGrid = document.getElementById("book-grid");
  const emptyState = document.getElementById("empty-state");
  const resetFiltersBtn = document.getElementById("reset-filters-btn");
  const notificationBanner = document.getElementById("notification-banner");

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

  const deleteModal = document.getElementById("delete-modal");
  const deleteBookTitle = document.getElementById("delete-book-title");
  const cancelDeleteBtn = document.getElementById("cancel-delete-btn");
  const confirmDeleteBtn = document.getElementById("confirm-delete-btn");

  // State
  let pendingDeleteId = null;
  let searchDebounceTimer = null;
  let notificationTimer = null;

  // Initial Load
  init();

  async function init() {
    await loadCategories();
    await fetchBooks();
    setupEventListeners();
  }

  function setupEventListeners() {
    // Search input with debounce
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

    // Category filter change
    categoryFilter.addEventListener("change", () => {
      fetchBooks();
    });

    // Reset filters button in empty state
    resetFiltersBtn.addEventListener("click", () => {
      searchInput.value = "";
      clearSearchBtn.classList.add("hidden");
      categoryFilter.value = "";
      fetchBooks();
    });

    // Add book form submit
    addBookForm.addEventListener("submit", handleAddBook);

    // Clear input errors on user typing
    titleInput.addEventListener("input", () => clearFieldError(titleInput, titleError));
    authorInput.addEventListener("input", () => clearFieldError(authorInput, authorError));
    categoryInput.addEventListener("input", () => clearFieldError(categoryInput, categoryError));
    priceInput.addEventListener("input", () => clearFieldError(priceInput, priceError));

    // Delete modal events
    cancelDeleteBtn.addEventListener("click", closeDeleteModal);
    confirmDeleteBtn.addEventListener("click", handleConfirmDelete);

    deleteModal.addEventListener("click", (e) => {
      if (e.target === deleteModal) {
        closeDeleteModal();
      }
    });

    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && !deleteModal.classList.contains("hidden")) {
        closeDeleteModal();
      }
    });
  }

  // Fetch & Render Categories
  async function loadCategories() {
    try {
      const response = await fetch("/api/categories");
      if (!response.ok) return;
      const categories = await response.json();

      // Preserve currently selected category if any
      const selectedCat = categoryFilter.value;

      // Reset options keeping "All Categories"
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

  // Fetch & Render Books
  async function fetchBooks() {
    const q = searchInput.value.trim();
    const category = categoryFilter.value.trim();

    const params = new URLSearchParams();
    if (q) params.set("q", q);
    if (category) params.set("category", category);

    resultsCount.textContent = "Loading catalog...";

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

    // Format price
    const formattedPrice = typeof book.price === "number" ? `$${book.price.toFixed(2)}` : `$${book.price}`;

    card.innerHTML = `
      <div class="card-top">
        <span class="category-badge">${escapeHtml(book.category || "Uncategorized")}</span>
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
        <button class="btn-delete-card" data-id="${book.id}" data-title="${escapeAttr(book.title)}" title="Delete book">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="3 6 5 6 21 6"></polyline>
            <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
          </svg>
          Delete
        </button>
      </div>
    `;

    // Attach delete button handler
    const delBtn = card.querySelector(".btn-delete-card");
    delBtn.addEventListener("click", () => {
      openDeleteModal(book.id, book.title);
    });

    return card;
  }

  // Handle Add Book
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

    // Submit payload
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

      // Success
      addBookForm.reset();
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

  // Delete Book Logic
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
      confirmDeleteBtn.textContent = "Delete";
    }
  }

  // Form Field Validation Helpers
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

  // Toast / Banner Notification
  function showNotification(message, type = "success") {
    clearTimeout(notificationTimer);
    notificationBanner.className = `notification-banner ${type}`;
    notificationBanner.textContent = message;
    notificationBanner.classList.remove("hidden");

    notificationTimer = setTimeout(() => {
      notificationBanner.classList.add("hidden");
    }, 4500);
  }

  // HTML sanitizers
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

