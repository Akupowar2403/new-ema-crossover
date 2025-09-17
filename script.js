const API_URL = 'http://127.0.0.1:8000/screener_data';  // Screener data API

const TIME_FRAMES = ["15m", "1h", "4h", "1d"];

// Store previous signals to identify fresh alerts
let previousSignals = {};

/**
 * Shows or hides the loading spinner
 */
function showLoadingSpinner(show) {
    document.getElementById('loading-spinner').style.display = show ? 'block' : 'none';
}

/**
 * Shows an error message or hides error display
 */
function showError(message) {
    const errorDiv = document.getElementById('error-message');
    if (message) {
        errorDiv.textContent = message;
        errorDiv.style.display = 'block';
    } else {
        errorDiv.textContent = '';
        errorDiv.style.display = 'none';
    }
}

/**
 * Populate symbol dropdown from the fetched screener data
 */
async function populateSymbolDropdown() {
    try {
        const res = await fetch(API_URL);
        if (!res.ok) throw new Error(`Failed to fetch symbols: ${res.status}`);
        const data = await res.json();

        const symbolSelect = document.getElementById('symbol-select');
        symbolSelect.innerHTML = ''; // Clear existing options

        data.crypto.forEach(item => {
            const option = document.createElement('option');
            option.value = item.name;
            option.textContent = item.name;
            symbolSelect.appendChild(option);
        });
    } catch (error) {
        showError(error.message);
    }
}

/**
 * Main function to fetch screener data and update all tables
 */
async function fetchAndDisplayData() {
    showError('');
    showLoadingSpinner(true);
    try {
        const response = await fetch(API_URL);
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        const data = await response.json();

        populateTable('crypto-table', data.crypto || []);
        populateTable('forex-table', data.forex || []);
        populateTable('stocks-table', data.stocks || []);

        document.getElementById('last-updated').textContent = new Date().toLocaleTimeString();
    } catch (error) {
        console.error("Failed to fetch screener data:", error);
        showError("Error fetching screener data. See console.");
    } finally {
        showLoadingSpinner(false);
    }
}

/**
 * Create table header and rows for the screener table
 */
function populateTable(tableId, assetsData) {
    const table = document.getElementById(tableId);
    table.innerHTML = '';

    // Header
    let header = '<tr><th>Asset</th>';
    TIME_FRAMES.forEach(tf => header += `<th>${tf.toUpperCase()}</th>`);
    header += '</tr>';
    table.innerHTML = header;

    // Rows
    assetsData.forEach(asset => {
        let row = `<tr><td class="asset-name">${asset.name}</td>`;
        TIME_FRAMES.forEach(tf => {
            const signal = asset.timeframes ? asset.timeframes[tf] : null;
            if (signal) {
                const statusClass = signal.status.toLowerCase();
                const text = signal.status !== "Neutral" && signal.status !== "N/A"
                    ? `${signal.status.substring(0,4).toUpperCase()} (${signal.bars_since} bars)`
                    : signal.status;
                row += `<td class="${statusClass}">${text}</td>`;

                checkForAlert(asset.name, tf, signal);
            } else {
                row += `<td class="error">Error</td>`;
            }
        });
        row += '</tr>';
        table.innerHTML += row;
    });
}

/**
 * Detect new crossover alert and prepend to alerts list
 */
function checkForAlert(assetName, timeframe, newSignal) {
    const key = `${assetName}-${timeframe}`;
    const oldSignal = previousSignals[key];

    if (newSignal.bars_since === 0 && newSignal.status !== "Neutral" && (!oldSignal || oldSignal.status !== newSignal.status)) {
        const alertList = document.getElementById('alerts-list');
        if (alertList.children.length === 1 && alertList.children[0].textContent.includes('No new alerts')) {
            alertList.innerHTML = '';
        }
        const newAlert = document.createElement('li');
        const time = new Date().toLocaleTimeString();
        newAlert.textContent = `[${time}] New ${newSignal.status} crossover: ${assetName} on ${timeframe} timeframe.`;
        alertList.prepend(newAlert);
    }

    previousSignals[key] = newSignal;
}

/**
 * Tab switching logic
 */
function openTab(evt, tabName) {
    const tabcontent = document.getElementsByClassName("tab-content");
    for (let i = 0; i < tabcontent.length; i++) {
        tabcontent[i].style.display = "none";
    }

    const tablinks = document.getElementsByClassName("tab-link");
    for (let i = 0; i < tablinks.length; i++) {
        tablinks[i].className = tablinks[i].className.replace(" active", "");
    }

    document.getElementById(tabName).style.display = "block";
    evt.currentTarget.className += " active";
}

// Search/filter input handlers
function addSearchFilter(inputId, tableId) {
    document.getElementById(inputId).addEventListener('input', function () {
        const filter = this.value.toUpperCase();
        const rows = document.querySelectorAll(`#${tableId} tbody tr`);

        rows.forEach(row => {
            const symbolText = row.cells[0].textContent.toUpperCase();
            row.style.display = symbolText.includes(filter) ? '' : 'none';
        });
    });
}

/**
 * Fetch and display historical EMA crossovers from backend
 */
async function fetchHistoricalCrossovers(symbol, timeframe) {
    const url = `http://127.0.0.1:8000/historical-crossovers?symbol=${symbol}&timeframe=${timeframe}`;
    try {
        const response = await fetch(url);
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        const data = await response.json();
        return data.crossovers || [];
    } catch (error) {
        console.error("Error fetching historical crossovers:", error);
        return [];
    }
}

/**
 * Display historical EMA crossovers in table
 */
function displayCrossovers(crossovers) {
    const container = document.getElementById('crossover-results');
    if (!crossovers.length) {
        container.innerHTML = '<p>No crossover data found.</p>';
        return;
    }
    let html = '<h3>Historical EMA Crossovers</h3><table class="crossover-table">';
    html += '<tr><th>Timestamp</th><th>Type</th><th>Close Price</th></tr>';
    crossovers.forEach(event => {
        const date = new Date(event.timestamp * 1000).toLocaleString();
        html += `<tr><td>${date}</td><td>${event.type.charAt(0).toUpperCase() + event.type.slice(1)}</td><td>${event.close}</td></tr>`;
    });
    html += '</table>';
    container.innerHTML = html;
}

// Button fetch-crossovers event listener
document.getElementById('fetch-crossovers').addEventListener('click', async () => {
    const symbol = document.getElementById('symbol-select').value;
    const timeframe = document.getElementById('timeframe-select').value;
    const container = document.getElementById('crossover-results');
    container.innerHTML = '<p>Loading crossover data...</p>';
    const crossovers = await fetchHistoricalCrossovers(symbol, timeframe);
    displayCrossovers(crossovers);
});


// --- Initial page load ---
document.addEventListener('DOMContentLoaded', () => {
    populateSymbolDropdown();
    fetchAndDisplayData();

    setInterval(fetchAndDisplayData, 15 * 60 * 1000); // auto-refresh every 15min

    addSearchFilter('search-input', 'crypto-table');
    addSearchFilter('search-forex', 'forex-table');
    addSearchFilter('search-stocks', 'stocks-table');
});
