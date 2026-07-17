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

// Grafik harga emas -- dirender dari data yfinance yang dikirim Flask (bukan widget eksternal),
// supaya instrumen & sumber datanya identik dengan yang dipakai model untuk prediksi.
const chartDataEl = document.getElementById("chart-data");
if (chartDataEl && window.Chart) {
  const chartData = JSON.parse(chartDataEl.textContent);
  const ctx = document.getElementById("goldChart");
  if (ctx && chartData.harga && chartData.harga.length) {
    new Chart(ctx, {
      type: "line",
      data: {
        labels: chartData.labels,
        datasets: [{
          label: `Harga Close (${chartData.ticker})`,
          data: chartData.harga,
          borderColor: "#B8860B",
          backgroundColor: "rgba(212,175,55,0.15)",
          borderWidth: 2,
          pointRadius: 0,
          pointHoverRadius: 4,
          tension: 0.25,
          fill: true,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: (item) => `$${item.parsed.y.toLocaleString("en-US", { minimumFractionDigits: 2 })}`,
            },
          },
        },
        scales: {
          x: { grid: { display: false } },
          y: {
            ticks: { callback: (val) => `$${val.toLocaleString("en-US")}` },
            grid: { color: "rgba(0,0,0,0.06)" },
          },
        },
      },
    });
  }
}
