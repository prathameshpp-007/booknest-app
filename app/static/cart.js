// BookNest - Shopping cart page.

document.addEventListener("DOMContentLoaded", () => {
  const loading = document.getElementById("cart-loading");
  const empty = document.getElementById("cart-empty");
  const content = document.getElementById("cart-content");
  const itemsWrap = document.getElementById("cart-items");
  const summaryCount = document.getElementById("summary-count");
  const summarySubtotal = document.getElementById("summary-subtotal");
  const summaryTotal = document.getElementById("summary-total");
  const clearCartBtn = document.getElementById("clear-cart-btn");
  const notification = document.getElementById("cart-notification");
  const checkoutLink = document.getElementById("checkout-link");

  let notificationTimer = null;
  let pending = false;

  init();

  async function init() {
    await loadCart();
  }

  async function loadCart() {
    try {
      const response = await fetch("/api/cart");
      if (!response.ok) throw new Error(`Server responded with ${response.status}`);
      const cart = await response.json();
      renderCart(cart);
    } catch (err) {
      console.error("Failed to load cart:", err);
      loading.classList.add("hidden");
      showNotification("Could not load your cart. Please refresh the page.", "error");
    }
  }

  function renderCart(cart) {
    loading.classList.add("hidden");

    if (!cart.items || cart.items.length === 0) {
      empty.classList.remove("hidden");
      content.classList.add("hidden");
      updateBadge(0);
      return;
    }

    empty.classList.add("hidden");
    content.classList.remove("hidden");
    itemsWrap.innerHTML = "";

    cart.items.forEach((item) => {
      itemsWrap.appendChild(createCartItem(item));
    });

    summaryCount.textContent = String(cart.count);
    summarySubtotal.textContent = formatMoney(cart.subtotal);
    summaryTotal.textContent = formatMoney(cart.total);
    checkoutLink.classList.remove("hidden");
    updateBadge(cart.count);
  }

  function createCartItem(item) {
    const row = document.createElement("article");
    row.className = "cart-item";
    row.dataset.bookId = item.book_id;

    row.innerHTML = `
      <div class="cart-item-main">
        <div class="cart-item-info">
          <span class="category-badge">${escapeHtml(item.category || "General")}</span>
          <h3 class="cart-item-title">${escapeHtml(item.title)}</h3>
          <p class="cart-item-author">by ${escapeHtml(item.author)}</p>
          <p class="cart-item-price">${formatMoney(item.price)} each</p>
        </div>
      </div>
      <div class="cart-item-controls">
        <div class="qty-control" role="group" aria-label="Quantity for ${escapeHtml(item.title)}">
          <button type="button" class="qty-btn" data-action="decrease" aria-label="Decrease quantity">&minus;</button>
          <input
            type="number"
            class="qty-input"
            value="${item.quantity}"
            min="1"
            max="99"
            data-action="set"
            aria-label="Quantity"
          >
          <button type="button" class="qty-btn" data-action="increase" aria-label="Increase quantity">+</button>
        </div>
        <div class="cart-item-total">${formatMoney(item.line_total)}</div>
        <button type="button" class="btn-remove-item" data-action="remove">Remove</button>
      </div>
    `;

    return row;
  }

  itemsWrap.addEventListener("click", (e) => {
    const actionBtn = e.target.closest("[data-action]");
    if (!actionBtn || pending) return;

    const row = e.target.closest(".cart-item");
    if (!row) return;

    const bookId = row.dataset.bookId;
    const input = row.querySelector(".qty-input");
    const current = parseInt(input.value, 10) || 1;
    const action = actionBtn.dataset.action;

    if (action === "decrease") {
      setQuantity(bookId, Math.max(1, current - 1), row);
    } else if (action === "increase") {
      setQuantity(bookId, Math.min(99, current + 1), row);
    } else if (action === "remove") {
      removeItem(bookId, row);
    }
  });

  itemsWrap.addEventListener("change", (e) => {
    const input = e.target.closest(".qty-input");
    if (!input) return;
    const row = input.closest(".cart-item");
    const quantity = parseInt(input.value, 10);
    if (!quantity || quantity < 1) {
      input.value = "1";
      setQuantity(row.dataset.bookId, 1, row);
      return;
    }
    setQuantity(row.dataset.bookId, Math.min(99, quantity), row);
  });

  async function setQuantity(bookId, quantity, row) {
    setRowBusy(row, true);
    try {
      const response = await fetch(`/api/cart/${bookId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ quantity }),
      });
      const data = await response.json();
      if (!response.ok) {
        showNotification(data.error || "Could not update quantity.", "error");
        return;
      }
      renderCart(data);
      showNotification("Quantity updated.", "success");
    } catch (err) {
      console.error("Update quantity error:", err);
      showNotification("Network error while updating quantity.", "error");
    } finally {
      setRowBusy(row, false);
    }
  }

  async function removeItem(bookId, row) {
    setRowBusy(row, true);
    try {
      const response = await fetch(`/api/cart/${bookId}`, { method: "DELETE" });
      const data = await response.json();
      if (!response.ok) {
        showNotification(data.error || "Could not remove item.", "error");
        return;
      }
      renderCart(data);
      showNotification("Book removed from cart.", "success");
    } catch (err) {
      console.error("Remove item error:", err);
      showNotification("Network error while removing item.", "error");
    } finally {
      setRowBusy(row, false);
    }
  }

  clearCartBtn.addEventListener("click", async () => {
    if (pending) return;
    pending = true;
    clearCartBtn.disabled = true;
    clearCartBtn.textContent = "Clearing...";
    try {
      const response = await fetch("/api/cart", { method: "DELETE" });
      const data = await response.json();
      renderCart(response.ok ? data : { items: [], count: 0 });
      showNotification("Cart cleared.", "success");
    } catch (err) {
      console.error("Clear cart error:", err);
      showNotification("Network error while clearing the cart.", "error");
    } finally {
      pending = false;
      clearCartBtn.disabled = false;
      clearCartBtn.textContent = "Clear Cart";
    }
  });

  function setRowBusy(row, busy) {
    if (!row) return;
    row.classList.toggle("is-busy", busy);
    row.querySelectorAll("button, input").forEach((el) => {
      el.disabled = busy;
    });
  }

  function updateBadge(count) {
    document.querySelectorAll("#nav-cart-count, #mobile-nav-cart-count").forEach((badge) => {
      badge.textContent = count;
      badge.classList.toggle("hidden", count === 0);
    });
  }

  function showNotification(message, type = "success") {
    clearTimeout(notificationTimer);
    notification.className = `notification-banner ${type}`;
    notification.textContent = message;
    notification.classList.remove("hidden");
    notificationTimer = setTimeout(() => notification.classList.add("hidden"), 4000);
  }

  function formatMoney(value) {
    return `$${Number(value || 0).toFixed(2)}`;
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
});
