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
if (chartDataEl && !window.Chart) {
  // FIX: sebelumnya kegagalan ini diam-diam -- kalau Chart.js gagal ke-load
  // dgn alasan apapun (file hilang, dst), sekarang minimal ada jejak di
  // console supaya gampang didiagnosis lewat DevTools, bukan cuma "kosong".
  console.error("[PrediksiEmas] Chart.js tidak ter-load -- grafik tidak bisa dirender. Cek static/vendor/chart.umd.js.");
}
if (chartDataEl && window.Chart) {
  const chartData = JSON.parse(chartDataEl.textContent);
  const ctx = document.getElementById("goldChart");
  if (ctx && chartData.harga && chartData.harga.length) {
    // Plugin kecil: gambar garis vertikal putus-putus di tanggal yang sedang
    // di-hover, supaya jelas titik mana yang lagi ditunjuk kursor.
    const verticalLineOnHover = {
      id: "verticalLineOnHover",
      afterDraw(chart) {
        const active = chart.tooltip && chart.tooltip._active;
        if (active && active.length) {
          const x = active[0].element.x;
          const { top, bottom } = chart.chartArea;
          const c = chart.ctx;
          c.save();
          c.beginPath();
          c.moveTo(x, top);
          c.lineTo(x, bottom);
          c.lineWidth = 1;
          c.strokeStyle = "rgba(184,134,11,0.35)";
          c.setLineDash([4, 4]);
          c.stroke();
          c.restore();
        }
      },
    };

    // FIX: sebelumnya hari libur/weekend yang null di UJUNG rentang (bukan di
    // tengah) tampil sebagai area kosong polos -- Chart.js memang tidak bisa
    // menggambar garis ke titik yang tidak ada di ujung, jadi itu wilayah
    // benar2 blank. Ini SEBENARNYA BENAR (bukan bug), tapi keliatannya
    // seperti "data hilang". Plugin ini kasih shading abu2 tipis + label
    // "Libur" di kolom itu, supaya jelas itu memang hari tanpa perdagangan.
    const holidayShading = {
      id: "holidayShading",
      beforeDatasetsDraw(chart) {
        const { ctx, chartArea, scales } = chart;
        const data = chart.data.datasets[0].data;
        const xScale = scales.x;
        if (!chartArea) return;
        ctx.save();
        data.forEach((val, i) => {
          if (val === null || val === undefined) {
            const centerX = xScale.getPixelForValue(i);
            const bandHalfWidth = xScale.width / data.length / 2;
            ctx.fillStyle = "rgba(0,0,0,0.035)";
            ctx.fillRect(centerX - bandHalfWidth, chartArea.top, bandHalfWidth * 2, chartArea.height);
          }
        });
        ctx.restore();
      },
    };

    new Chart(ctx, {
      type: "line",
      plugins: [verticalLineOnHover, holidayShading],
      data: {
        labels: chartData.labels,
        datasets: [{
          label: `Harga Close (${chartData.ticker})`,
          data: chartData.harga,
          borderColor: "#B8860B",
          backgroundColor: "rgba(212,175,55,0.15)",
          borderWidth: 2,
          pointRadius: 0,
          pointHoverRadius: 5,
          pointHitRadius: 12, // FIX: area sentuh titik diperbesar (titik aslinya
                              // tak terlihat krn pointRadius:0), jadi lebih mudah kena.
          tension: 0.25,
          fill: true,
          spanGaps: true, // FIX: sumbu-x sekarang kalender hari kerja penuh --
                           // hari libur bursa jadi null; spanGaps menyambung
                           // garis melewatinya dgn mulus, bukan memutusnya.
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        // FIX: mode "index" + intersect:false -- tooltip muncul begitu kursor
        // ada DI MANA SAJA sepanjang garis vertikal tanggal itu, tidak perlu
        // presisi tepat di atas titik data (yang tadinya kecil/tak terlihat).
        interaction: { mode: "index", intersect: false },
        hover: { mode: "index", intersect: false },
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: (item) => `$${item.parsed.y.toLocaleString("en-US", { minimumFractionDigits: 2 })}`,
            },
          },
        },
        scales: {
          x: {
            grid: { display: false },
            ticks: {
              autoSkip: false, // FIX: dgn cuma 7 titik, semua tanggal wajib tampil,
                                // jangan biarkan Chart.js menyembunyikan sebagian.
              maxRotation: 45,
              minRotation: 0,
            },
          },
          y: {
            ticks: { callback: (val) => `$${val.toLocaleString("en-US")}` },
            grid: { color: "rgba(0,0,0,0.06)" },
          },
        },
      },
    });
  }
}
