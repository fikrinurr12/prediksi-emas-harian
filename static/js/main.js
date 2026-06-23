// =======================================================
// Gold Predictor - Frontend logic
// Mengambil data dari endpoint Flask (/api/predict,
// /api/feature-importance) dan merender ke UI.
// =======================================================

async function loadCurrentPrice() {
    try {
        const res = await fetch("/api/predict");
        const json = await res.json();

        if (!json.success) {
            document.getElementById("current-price").textContent = "Gagal memuat data";
            return;
        }

        const data = json.data;

        document.getElementById("current-price").textContent =
            `$${data.current_price.toLocaleString("en-US", { minimumFractionDigits: 2 })}`;

        const changeEl = document.getElementById("price-change");
        const sign = data.price_change >= 0 ? "▲" : "▼";
        changeEl.textContent = `${sign} $${Math.abs(data.price_change).toFixed(2)} (${data.price_change_pct.toFixed(2)}%)`;
        changeEl.style.color = data.price_change >= 0 ? "#9ef0c2" : "#ffb3ab";

        document.getElementById("last-update").textContent = `Update terakhir: ${data.last_update}`;

        // Simpan data terakhir di window supaya tombol prediksi tidak perlu fetch ulang
        window.__lastPredictionData = data;

    } catch (err) {
        console.error("Gagal memuat harga emas:", err);
        document.getElementById("current-price").textContent = "Gagal memuat data";
    }
}

function renderPrediction(data) {
    const resultBox = document.getElementById("prediction-result");
    resultBox.classList.remove("hidden");

    const directionEl = document.getElementById("prediction-direction");
    const isUp = data.prediction_code === 1;

    directionEl.textContent = isUp ? "📈 Prediksi: Harga Naik" : "📉 Prediksi: Harga Turun";
    directionEl.className = "prediction-direction " + (isUp ? "up" : "down");

    document.getElementById("prediction-confidence").textContent =
        `Tingkat keyakinan model: ${data.confidence.toFixed(1)}%`;

    document.getElementById("bar-naik").style.width = `${data.probability_naik}%`;
    document.getElementById("bar-turun").style.width = `${data.probability_turun}%`;
    document.getElementById("text-naik").textContent = `${data.probability_naik.toFixed(0)}%`;
    document.getElementById("text-turun").textContent = `${data.probability_turun.toFixed(0)}%`;
}

async function handlePredictClick() {
    const btn = document.getElementById("btn-predict");
    btn.disabled = true;
    btn.textContent = "⏳ Memproses...";

    try {
        // Jika data sudah ada dari load awal, langsung pakai, supaya tidak
        // double request ke yfinance.
        let data = window.__lastPredictionData;
        if (!data) {
            const res = await fetch("/api/predict");
            const json = await res.json();
            if (!json.success) throw new Error(json.error);
            data = json.data;
        }
        renderPrediction(data);
    } catch (err) {
        alert("Gagal mendapatkan prediksi. Coba lagi beberapa saat.");
        console.error(err);
    } finally {
        btn.disabled = false;
        btn.textContent = "🔄 Prediksi Arah Harga";
    }
}

async function loadFeatureImportance() {
    const container = document.getElementById("feature-importance-list");

    try {
        const res = await fetch("/api/feature-importance");
        const json = await res.json();

        if (!json.success) {
            container.innerHTML = "<p class='loading-text'>Gagal memuat data.</p>";
            return;
        }

        const items = json.data; // [{Feature, Percentage}, ...] sudah terurut

        const labelMap = {
            SMA: "SMA (Simple Moving Average)",
            EMA: "EMA (Exponential Moving Average)",
            RSI: "RSI (Relative Strength Index)",
            STI: "STI (Stochastic Oscillator)",
            PROC: "PROC (Price Rate of Change)",
        };

        container.innerHTML = items.map(item => `
            <div class="fi-row">
                <div class="fi-row-label">
                    <span>${labelMap[item.Feature] || item.Feature}</span>
                    <span>${item.Percentage}%</span>
                </div>
                <div class="fi-bar-bg">
                    <div class="fi-bar-fill" style="width: ${item.Percentage}%"></div>
                </div>
            </div>
        `).join("");

        const top = items[0];
        const insightBox = document.getElementById("insight-box");
        insightBox.textContent =
            `Insight: ${labelMap[top.Feature] || top.Feature} memiliki kontribusi tertinggi ` +
            `(${top.Percentage}%) dalam menentukan arah pergerakan harga emas harian.`;

    } catch (err) {
        console.error("Gagal memuat feature importance:", err);
        container.innerHTML = "<p class='loading-text'>Gagal memuat data.</p>";
    }
}

document.addEventListener("DOMContentLoaded", () => {
    loadCurrentPrice();
    loadFeatureImportance();

    document.getElementById("btn-predict").addEventListener("click", handlePredictClick);
});
