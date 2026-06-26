// =======================================================
// Eksperimen Pola Candle - Frontend logic
// =======================================================

let ttChartInstance = null;

function switchTab(tabName) {
    document.querySelectorAll(".tab-btn").forEach(btn => btn.classList.remove("active"));
    document.querySelectorAll(".tab-content").forEach(content => content.classList.remove("active"));

    document.querySelector(`.tab-btn[data-tab="${tabName}"]`).classList.add("active");
    document.getElementById(`tab-${tabName}`).classList.add("active");
}

function renderSignalTable(containerId, signals, columns) {
    const container = document.getElementById(containerId);

    if (!signals || signals.length === 0) {
        container.innerHTML = "<p class='loading-text'>Belum ada sinyal terdeteksi pada rentang data ini.</p>";
        return;
    }

    const headerRow = columns.map(col => `<th>${col.label}</th>`).join("");
    const bodyRows = signals.map(row => {
        const cells = columns.map(col => {
            let val = row[col.key];
            if (typeof val === "boolean") val = val ? "✅" : "—";
            if (typeof val === "number") val = val.toFixed(col.decimals ?? 2);
            return `<td>${val ?? "-"}</td>`;
        }).join("");
        return `<tr>${cells}</tr>`;
    }).join("");

    container.innerHTML = `
        <table class="signal-table">
            <thead><tr>${headerRow}</tr></thead>
            <tbody>${bodyRows}</tbody>
        </table>
    `;
}

function renderTTChart(chartData) {
    const ctx = document.getElementById("tt-chart");

    if (ttChartInstance) {
        ttChartInstance.destroy();
    }

    if (!chartData || chartData.length === 0) return;

    ttChartInstance = new Chart(ctx, {
        type: "line",
        data: {
            labels: chartData.map(d => d.Date),
            datasets: [{
                label: "Oscillator (Z-Score)",
                data: chartData.map(d => d.linreg_osc_norm),
                borderColor: "#4f7fc4",
                backgroundColor: "rgba(79, 127, 196, 0.1)",
                borderWidth: 1.5,
                pointRadius: 0,
                tension: 0.1,
            }]
        },
        options: {
            responsive: true,
            plugins: { legend: { display: false } },
            scales: {
                x: { ticks: { maxTicksLimit: 8, font: { size: 9 } } },
                y: { ticks: { font: { size: 9 } } },
            }
        }
    });
}

async function runExperiment() {
    const btn = document.getElementById("btn-run");
    btn.disabled = true;
    btn.textContent = "⏳ Memproses...";

    const params = new URLSearchParams({
        lookback_days: document.getElementById("lookback-days").value,
        upper_wick: document.getElementById("upper-wick").value,
        lower_wick: document.getElementById("lower-wick").value,
        tt_length: document.getElementById("tt-length").value,
        tt_upper: document.getElementById("tt-upper").value,
        tt_lower: document.getElementById("tt-lower").value,
    });

    try {
        const res = await fetch(`/api/eksperimen/pola-candle?${params.toString()}`);
        const json = await res.json();

        if (!json.success) {
            alert("Gagal menjalankan eksperimen: " + json.error);
            return;
        }

        const data = json.data;

        const sourceLabels = {
            cache: "Cache (≤30 menit)",
            yfinance: "Live dari Yahoo Finance",
            twelvedata: "Live dari Twelve Data (cadangan)",
            cache_basi: "Cache lama (semua sumber gagal)",
        };
        document.getElementById("data-source-info").textContent =
            `📡 Sumber data: ${sourceLabels[data.data_source] || data.data_source} | ${data.n_candles} candle dimuat`;

        // Candle Kejepit
        document.getElementById("n-bullish-kejepit").textContent = data.candle_kejepit.n_bullish;
        document.getElementById("n-bearish-kejepit").textContent = data.candle_kejepit.n_bearish;
        renderSignalTable("table-kejepit", data.candle_kejepit.signals, [
            { key: "Date", label: "Tanggal" },
            { key: "Close", label: "Close" },
            { key: "is_bullish_kejepit", label: "Box Jual" },
            { key: "is_bearish_kejepit", label: "Box Beli" },
            { key: "zone_high", label: "Zone High" },
            { key: "zone_low", label: "Zone Low" },
        ]);

        // Candle Rejection
        document.getElementById("n-rs").textContent = data.candle_rejection.n_reject_sell;
        document.getElementById("n-rb").textContent = data.candle_rejection.n_reject_buy;
        renderSignalTable("table-rejection", data.candle_rejection.signals, [
            { key: "Date", label: "Tanggal" },
            { key: "Close", label: "Close" },
            { key: "upper_wick_pct", label: "Upper Wick %" },
            { key: "lower_wick_pct", label: "Lower Wick %" },
            { key: "is_reject_sell", label: "RS" },
            { key: "is_reject_buy", label: "RB" },
        ]);

        // Terbang Terjun
        document.getElementById("n-tt-sell").textContent = data.terbang_terjun.n_sell;
        document.getElementById("n-tt-buy").textContent = data.terbang_terjun.n_buy;
        renderSignalTable("table-terbang", data.terbang_terjun.signals, [
            { key: "Date", label: "Tanggal" },
            { key: "Close", label: "Close" },
            { key: "linreg_osc_norm", label: "Oscillator", decimals: 3 },
            { key: "is_sell_signal", label: "SELL" },
            { key: "is_buy_signal", label: "BUY" },
        ]);
        renderTTChart(data.terbang_terjun.chart);

    } catch (err) {
        console.error(err);
        alert("Terjadi kesalahan saat menjalankan eksperimen.");
    } finally {
        btn.disabled = false;
        btn.textContent = "🔄 Jalankan Eksperimen";
    }
}

document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll(".tab-btn").forEach(btn => {
        btn.addEventListener("click", () => switchTab(btn.dataset.tab));
    });

    document.getElementById("btn-run").addEventListener("click", runExperiment);

    // Jalankan otomatis sekali saat halaman dibuka
    runExperiment();
});
