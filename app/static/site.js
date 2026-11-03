// BookNest - Shared navigation and dialog behaviour for every page.

document.addEventListener("DOMContentLoaded", () => {
  const mobileToggleBtn = document.getElementById("mobile-toggle-btn");
  const mobileMenu = document.getElementById("mobile-menu");

  const aboutModal = document.getElementById("about-modal");
  const navAboutBtn = document.getElementById("nav-about");
  const mobileNavAboutBtn = document.getElementById("mobile-nav-about");
  const closeAboutModalBtn = document.getElementById("close-about-modal-btn");
  const dismissAboutBtn = document.getElementById("dismiss-about-btn");

  function closeMobileMenu() {
    if (mobileMenu && !mobileMenu.classList.contains("hidden")) {
      mobileMenu.classList.add("hidden");
      if (mobileToggleBtn) {
        mobileToggleBtn.setAttribute("aria-expanded", "false");
      }
    }
  }

  function openAboutModal() {
    if (aboutModal) aboutModal.classList.remove("hidden");
  }

  function closeAboutModal() {
    if (aboutModal) aboutModal.classList.add("hidden");
  }

  if (mobileToggleBtn && mobileMenu) {
    mobileToggleBtn.addEventListener("click", () => {
      const isExpanded = mobileToggleBtn.getAttribute("aria-expanded") === "true";
      mobileToggleBtn.setAttribute("aria-expanded", String(!isExpanded));
      mobileMenu.classList.toggle("hidden");
    });
  }

  document.querySelectorAll(".mobile-nav-link, #mobile-add-book-btn").forEach((link) => {
    link.addEventListener("click", closeMobileMenu);
  });

  if (navAboutBtn) {
    navAboutBtn.addEventListener("click", openAboutModal);
  }

  if (mobileNavAboutBtn) {
    mobileNavAboutBtn.addEventListener("click", () => {
      closeMobileMenu();
      openAboutModal();
    });
  }

  if (closeAboutModalBtn) {
    closeAboutModalBtn.addEventListener("click", closeAboutModal);
  }

  if (dismissAboutBtn) {
    dismissAboutBtn.addEventListener("click", closeAboutModal);
  }

  if (aboutModal) {
    aboutModal.addEventListener("click", (e) => {
      if (e.target === aboutModal) closeAboutModal();
    });
  }

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && aboutModal && !aboutModal.classList.contains("hidden")) {
      closeAboutModal();
    }
  });
});
