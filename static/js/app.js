
function getTheme() {
    return document.documentElement.getAttribute("data-theme") || "light";
}

function applySavedTheme() {
    const saved = localStorage.getItem("finance-theme") || "light";
    document.documentElement.setAttribute("data-theme", saved);
}

function toggleTheme() {
    const current = getTheme();
    const next = current === "dark" ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", next);
    localStorage.setItem("finance-theme", next);
}

applySavedTheme();

function cssVar(name) {
    return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

function renderPie(id, labels, values, colors) {
    const el = document.getElementById(id);
    if (!el) return;

    new Chart(el, {
        type: "pie",
        data: {
            labels: labels,
            datasets: [{
                data: values,
                backgroundColor: colors,
                borderColor: cssVar("--card"),
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: function(ctx) {
                            const total = ctx.dataset.data.reduce((a, b) => a + b, 0);
                            const value = ctx.parsed;
                            const percent = total ? (value / total * 100).toFixed(1) : 0;
                            return `${ctx.label}: ${value.toLocaleString("ru-RU")} ₸ (${percent}%)`;
                        }
                    }
                }
            }
        }
    });
}

function renderLine(id, labels, values) {
    const el = document.getElementById(id);
    if (!el) return;

    new Chart(el, {
        type: "line",
        data: {
            labels: labels,
            datasets: [{
                label: "Баланс",
                data: values,
                borderColor: "#1683f7",
                backgroundColor: "rgba(22, 131, 247, .12)",
                pointRadius: 4,
                pointHoverRadius: 6,
                tension: .25,
                fill: true
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    labels: {
                        color: cssVar("--text")
                    }
                }
            },
            scales: {
                x: {
                    ticks: { color: cssVar("--muted") },
                    grid: { color: "rgba(148, 163, 184, .2)" }
                },
                y: {
                    ticks: {
                        color: cssVar("--muted"),
                        callback: value => value.toLocaleString("ru-RU") + " ₸"
                    },
                    grid: { color: "rgba(148, 163, 184, .2)" }
                }
            }
        }
    });
}
