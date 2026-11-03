// BookNest - Demo checkout page.

document.addEventListener("DOMContentLoaded", () => {
  const loading = document.getElementById("checkout-loading");
  const empty = document.getElementById("checkout-empty");
  const content = document.getElementById("checkout-content");
  const form = document.getElementById("checkout-form");
  const itemsWrap = document.getElementById("checkout-items");
  const subtotalEl = document.getElementById("checkout-subtotal");
  const totalEl = document.getElementById("checkout-total");
  const placeOrderBtn = document.getElementById("place-order-btn");
  const notification = document.getElementById("checkout-notification");

  const fields = {
    name: {
      input: document.getElementById("customer-name"),
      error: document.getElementById("name-error"),
    },
    email: {
      input: document.getElementById("customer-email"),
      error: document.getElementById("email-error"),
    },
    phone: {
      input: document.getElementById("customer-phone"),
      error: document.getElementById("phone-error"),
    },
    address: {
      input: document.getElementById("customer-address"),
      error: document.getElementById("address-error"),
    },
  };

  let notificationTimer = null;
  let submitting = false;

  init();

  async function init() {
    await loadSummary();

    Object.values(fields).forEach(({ input, error }) => {
      input.addEventListener("input", () => clearError(input, error));
    });

    form.addEventListener("submit", handleSubmit);
  }

  async function loadSummary() {
    try {
      const response = await fetch("/api/cart");
      if (!response.ok) throw new Error(`Server responded with ${response.status}`);
      const cart = await response.json();
      loading.classList.add("hidden");

      if (!cart.items || cart.items.length === 0) {
        empty.classList.remove("hidden");
        content.classList.add("hidden");
        return;
      }

      empty.classList.add("hidden");
      content.classList.remove("hidden");

      itemsWrap.innerHTML = "";
      cart.items.forEach((item) => {
        const row = document.createElement("div");
        row.className = "checkout-item";
        row.innerHTML = `
          <div>
            <span class="checkout-item-title">${escapeHtml(item.title)}</span>
            <span class="checkout-item-qty">Qty ${item.quantity} &times; ${formatMoney(item.price)}</span>
          </div>
          <span class="checkout-item-total">${formatMoney(item.line_total)}</span>
        `;
        itemsWrap.appendChild(row);
      });

      subtotalEl.textContent = formatMoney(cart.subtotal);
      totalEl.textContent = formatMoney(cart.total);
    } catch (err) {
      console.error("Failed to load cart summary:", err);
      loading.classList.add("hidden");
      showNotification("Could not load your order summary. Please refresh.", "error");
    }
  }

  function validate() {
    let valid = true;

    const name = fields.name.input.value.trim();
    if (name.length < 2) {
      setError(fields.name.input, fields.name.error, "Please enter your full name.");
      valid = false;
    }

    const email = fields.email.input.value.trim();
    if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)) {
      setError(fields.email.input, fields.email.error, "Please enter a valid email address.");
      valid = false;
    }

    const phoneDigits = fields.phone.input.value.replace(/\D/g, "");
    if (phoneDigits.length < 7 || phoneDigits.length > 15) {
      setError(fields.phone.input, fields.phone.error, "Please enter a valid phone number (7-15 digits).");
      valid = false;
    }

    const address = fields.address.input.value.trim();
    if (address.length < 5) {
      setError(fields.address.input, fields.address.error, "Please enter your full delivery address.");
      valid = false;
    }

    return valid;
  }

  async function handleSubmit(e) {
    e.preventDefault();
    if (submitting) return;

    if (!validate()) {
      showNotification("Please fix the highlighted fields before placing your order.", "error");
      return;
    }

    submitting = true;
    setLoading(true);

    try {
      const response = await fetch("/api/checkout", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: fields.name.input.value.trim(),
          email: fields.email.input.value.trim(),
          phone: fields.phone.input.value.trim(),
          address: fields.address.input.value.trim(),
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        if (data.fields) {
          Object.entries(data.fields).forEach(([key, message]) => {
            if (fields[key]) {
              setError(fields[key].input, fields[key].error, message);
            }
          });
        }
        showNotification(data.error || "Could not place your order.", "error");
        setLoading(false);
        submitting = false;
        return;
      }

      updateBadge(0);
      window.location.href = data.redirect_url;
    } catch (err) {
      console.error("Checkout error:", err);
      showNotification("Network error while placing your order. Please try again.", "error");
      setLoading(false);
      submitting = false;
    }
  }

  function setLoading(isLoading) {
    placeOrderBtn.disabled = isLoading;
    const text = placeOrderBtn.querySelector(".btn-text");
    if (text) text.textContent = isLoading ? "Placing Order..." : "Place Demo Order";
  }

  function setError(input, errorEl, message) {
    input.classList.add("input-invalid");
    errorEl.textContent = message;
  }

  function clearError(input, errorEl) {
    input.classList.remove("input-invalid");
    errorEl.textContent = "";
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
    notificationTimer = setTimeout(() => notification.classList.add("hidden"), 5000);
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
