// Navbar: transparent -> white on scroll
const navbar = document.querySelector(".navbar");
function updateNavbar() {
  if (!navbar) return;
  if (window.scrollY > 40) navbar.classList.add("scrolled");
  else navbar.classList.remove("scrolled");
}
window.addEventListener("scroll", updateNavbar, { passive: true });
updateNavbar();

// Sections fade up into view
const revealEls = document.querySelectorAll(".reveal");
if ("IntersectionObserver" in window && revealEls.length) {
  const io = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add("is-visible");
          io.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.15 }
  );
  revealEls.forEach((el) => io.observe(el));
} else {
  revealEls.forEach((el) => el.classList.add("is-visible"));
}

// Feature-importance bars: fill to their real width shortly after load (gives a subtle animated feel)
const fiBars = document.querySelectorAll(".fi-bar-fill");
if (fiBars.length) {
  const fillBars = () => fiBars.forEach((b) => { b.style.width = b.dataset.pct + "%"; });
  if ("IntersectionObserver" in window) {
    const fiPanel = document.querySelector(".fi-panel");
    if (fiPanel) {
      const fiObserver = new IntersectionObserver(
        (entries) => { if (entries[0].isIntersecting) { fillBars(); fiObserver.disconnect(); } },
        { threshold: 0.2 }
      );
      fiObserver.observe(fiPanel);
    } else {
      fillBars();
    }
  } else {
    fillBars();
  }
}

// Indicator explainer popup: click a name -> show plain-language description
const indDataEl = document.getElementById("indikator-data");
const indDescriptions = indDataEl ? JSON.parse(indDataEl.textContent) : {};
const indOverlay = document.getElementById("indModalOverlay");
const indTitle = document.getElementById("indModalTitle");
const indBody = document.getElementById("indModalBody");

document.querySelectorAll(".ind-name").forEach((btn) => {
  btn.addEventListener("click", () => {
    const kode = btn.dataset.ind;
    indTitle.textContent = btn.textContent.trim();
    indBody.textContent = indDescriptions[kode] || "Penjelasan belum tersedia.";
    indOverlay.classList.add("open");
  });
});

function closeIndModal() {
  if (indOverlay) indOverlay.classList.remove("open");
}
document.getElementById("indModalClose")?.addEventListener("click", closeIndModal);
indOverlay?.addEventListener("click", (e) => { if (e.target === indOverlay) closeIndModal(); });
document.addEventListener("keydown", (e) => { if (e.key === "Escape") closeIndModal(); });
