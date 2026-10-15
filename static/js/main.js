/**
 * RationSmart - Frontend Application JavaScript
 * Dynamic POS cart calculator, quota validator, Chart.js visualizers, and utilities.
 */

document.addEventListener('DOMContentLoaded', () => {
    // 1. POS Dynamic Cart Subtotal & Balance Calculator
    initPOSCalculator();

    // 2. Initialize Charts if canvas elements exist
    initDashboardCharts();

    // 3. Quick Table Filter
    initTableFilters();
});

function initPOSCalculator() {
    const posForm = document.getElementById('posForm');
    if (!posForm) return;

    const qtyInputs = posForm.querySelectorAll('.pos-qty-input');
    const grandTotalEl = document.getElementById('posGrandTotal');
    const submitBtn = document.getElementById('btnSubmitSale');
    const quotaWarningBox = document.getElementById('posQuotaWarning');

    function recalculateTotal() {
        let grandTotal = 0;
        let hasOverQuota = false;
        let overQuotaDetails = [];

        qtyInputs.forEach(input => {
            const price = parseFloat(input.dataset.price) || 0;
            const maxRemaining = parseFloat(input.dataset.max) || 0;
            const commName = input.dataset.name || 'Commodity';
            const unit = input.dataset.unit || 'kg';
            const val = parseFloat(input.value) || 0;

            const subtotalEl = document.getElementById(`subtotal_${input.dataset.id}`);
            const subtotal = Math.round(val * price * 100) / 100;
            
            if (subtotalEl) {
                subtotalEl.innerText = `₹${subtotal.toFixed(2)}`;
            }

            grandTotal += subtotal;

            // Check if entered quantity exceeds remaining monthly quota
            if (val > maxRemaining + 0.001) {
                hasOverQuota = true;
                overQuotaDetails.push(`${commName}: entered ${val} ${unit}, remaining is only ${maxRemaining} ${unit}`);
                input.classList.add('is-invalid');
            } else {
                input.classList.remove('is-invalid');
            }
        });

        if (grandTotalEl) {
            grandTotalEl.innerText = `₹${grandTotal.toFixed(2)}`;
        }

        // Show/hide quota warning banner
        if (quotaWarningBox) {
            if (hasOverQuota) {
                quotaWarningBox.classList.remove('d-none');
                quotaWarningBox.innerHTML = `<strong>⚠️ Quota Warning:</strong> ${overQuotaDetails.join('<br>')}`;
                if (submitBtn) submitBtn.disabled = true;
            } else {
                quotaWarningBox.classList.add('d-none');
                if (submitBtn) submitBtn.disabled = false;
            }
        }
    }

    qtyInputs.forEach(input => {
        input.addEventListener('input', recalculateTotal);
        input.addEventListener('change', recalculateTotal);
    });

    // Run initial calculation
    recalculateTotal();
}

function initDashboardCharts() {
    // 1. Monthly Distribution by Commodity Bar Chart
    const commChartCanvas = document.getElementById('commodityDistributionChart');
    if (commChartCanvas) {
        fetch('/api/analytics/monthly-distribution')
            .then(res => res.json())
            .then(data => {
                new Chart(commChartCanvas, {
                    type: 'bar',
                    data: {
                        labels: data.labels,
                        datasets: [{
                            label: 'Distributed Quantity (kg / L)',
                            data: data.data,
                            backgroundColor: [
                                '#0e3860',
                                '#007791',
                                '#f59e0b',
                                '#10b981',
                                '#8b5cf6'
                            ],
                            borderRadius: 6
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: { display: false }
                        },
                        scales: {
                            y: {
                                beginAtZero: true,
                                title: { display: true, text: 'Quantity (kg/L)' }
                            }
                        }
                    }
                });
            })
            .catch(err => console.error('Error loading distribution chart:', err));
    }

    // 2. Beneficiaries Card Categories Doughnut Chart
    const catChartCanvas = document.getElementById('cardCategoryChart');
    if (catChartCanvas) {
        fetch('/api/analytics/card-categories')
            .then(res => res.json())
            .then(data => {
                new Chart(catChartCanvas, {
                    type: 'doughnut',
                    data: {
                        labels: data.labels.map(l => `${l} Card`),
                        datasets: [{
                            data: data.counts,
                            backgroundColor: [
                                '#f59e0b', // AAY - Yellow
                                '#ef4444', // PHH - Pink/Red
                                '#3b82f6', // NPHH - Blue
                                '#10b981'  // AY - Green
                            ]
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: { position: 'bottom' }
                        }
                    }
                });
            })
            .catch(err => console.error('Error loading category chart:', err));
    }
}

function initTableFilters() {
    const searchInputs = document.querySelectorAll('[data-table-search]');
    searchInputs.forEach(input => {
        const targetTableId = input.dataset.tableSearch;
        const targetTable = document.getElementById(targetTableId);
        if (!targetTable) return;

        input.addEventListener('keyup', () => {
            const filter = input.value.toLowerCase();
            const rows = targetTable.querySelectorAll('tbody tr');
            rows.forEach(row => {
                const text = row.innerText.toLowerCase();
                row.style.display = text.includes(filter) ? '' : 'none';
            });
        });
    });
}
