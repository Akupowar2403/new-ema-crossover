// --- CONFIGURATION & STATE ---
const API_BASE_URL = 'http://127.0.0.1:8000';
const REFRESH_INTERVAL_MS = 15 * 60 * 1000; // 15 minutes
const TIME_FRAMES = ["1m","15m", "1h", "4h", "1d"];
let previousSignals = {};
let masterSymbolList = []; // Cache for all available symbols

// --- CORE DATA FUNCTIONS ---

async function fetchScreenerData(symbols) {
    if (!symbols || symbols.length === 0) {
        populateTable('crypto-table', []);
        return null;
    }
    showError('');
    showLoadingSpinner(true);
    try {
        const response = await fetch(`${API_BASE_URL}/screener_data`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ symbols: symbols }),
        });
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        return await response.json();
    } catch (error) {
        console.error("Failed to fetch screener data:", error);
        showError("Error fetching screener data. See console for details.");
        return null;
    } finally {
        showLoadingSpinner(false);
    }
}

async function fetchAllSymbols() {
    try {
        const response = await fetch(`${API_BASE_URL}/all-symbols`);
        if (!response.ok) throw new Error('Failed to fetch all symbols');
        const data = await response.json();
        masterSymbolList = data.symbols || [];
    } catch (error) {
        console.error(error);
        showError(error.message);
    }
}

async function fetchHistoricalCrossovers(symbol, timeframe) {
    const url = `${API_BASE_URL}/historical-crossovers?symbol=${symbol}&timeframe=${timeframe}`;
    try {
        const response = await fetch(url);
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        const data = await response.json();
        return data.crossovers || [];
    } catch (error) {
        console.error("Error fetching historical crossovers:", error);
        showError("Could not fetch historical crossovers.");
        return [];
    }
}

async function fetchWatchlist() {
    try {
        const response = await fetch(`${API_BASE_URL}/watchlist`);
        if (!response.ok) throw new Error('Failed to fetch watchlist');
        const data = await response.json();
        return data.symbols || [];
    } catch (error) {
        console.error(error);
        showError(error.message);
        return [];
    }
}

async function addSymbolToWatchlist(symbol) {
    try {
        const response = await fetch(`${API_BASE_URL}/watchlist`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ symbol: symbol }),
        });
        if (!response.ok) throw new Error('Failed to add symbol');
        const data = await response.json();
        return data.watchlist || [];
    } catch (error) {
        console.error(error);
        showError(error.message);
        return null;
    }
}

async function removeSymbolFromWatchlist(symbol) {
    try {
        const response = await fetch(`${API_BASE_URL}/watchlist/${symbol}`, {
            method: 'DELETE',
        });
        if (!response.ok) throw new Error('Failed to remove symbol');
        const data = await response.json();
        return data.watchlist || [];
    } catch (error) {
        console.error(error);
        showError(error.message);
        return null;
    }
}


// --- UI POPULATION & UPDATE FUNCTIONS ---

function populateAllTables(data) {
    populateTable('crypto-table', data.crypto || []);
}

function populateTable(tableId, assetsData) {
    const table = document.getElementById(tableId);
    if (!table.querySelector('thead')) {
        const thead = table.createTHead();
        const headerRow = thead.insertRow();
        ['Asset', ...TIME_FRAMES].forEach(text => {
            const th = document.createElement('th');
            th.textContent = text.toUpperCase();
            headerRow.appendChild(th);
        });
    }
    let tbody = table.querySelector('tbody') || table.createTBody();
    tbody.innerHTML = '';
    const fragment = document.createDocumentFragment();
    assetsData.forEach(asset => {
        const tr = document.createElement('tr');
        let rowContent = `<td class="asset-name clickable" data-symbol="${asset.name}" title="Add ${asset.name} to Watchlist">${asset.name} ➕</td>`;
        TIME_FRAMES.forEach(tf => {
            const signal = asset.timeframes?.[tf];
            if (signal) {
                const statusClass = signal.status.toLowerCase().replace(/\s+/g, '-');
                const barsText = signal.bars_since !== null ? `(${signal.bars_since} bars)` : '';
                const text = signal.status !== "Neutral" && signal.status !== "N/A"
                    ? `${signal.status.substring(0, 4).toUpperCase()} ${barsText}`
                    : signal.status;
                rowContent += `<td class="${statusClass}">${text}</td>`;
                checkForAlert(asset.name, tf, signal);
            } else {
                rowContent += `<td class="error">Error</td>`;
            }
        });
        tr.innerHTML = rowContent;
        fragment.appendChild(tr);
    });
    tbody.appendChild(fragment);
}

// UPDATED: This function now populates the <datalist> element
function populateSymbolDatalist(assets) {
    const datalist = document.getElementById('symbol-datalist');
    datalist.innerHTML = '';
    assets.forEach(item => {
        const option = document.createElement('option');
        option.value = item;
        datalist.appendChild(option);
    });
}

function displayCrossovers(crossovers) {
    const container = document.getElementById('crossover-results');
    if (!crossovers.length) {
        container.innerHTML = '<p>No crossover data found.</p>';
        return;
    }
    let html = '<h3>Historical EMA Crossovers</h3><table class="crossover-table"><thead><tr><th>Timestamp</th><th>Type</th><th>Close Price</th></tr></thead><tbody>';
    crossovers.forEach(event => {
        const date = new Date(event.timestamp * 1000).toLocaleString();
        html += `<tr><td>${date}</td><td>${event.type.charAt(0).toUpperCase() + event.type.slice(1)}</td><td>${event.close}</td></tr>`;
    });
    html += '</tbody></table>';
    container.innerHTML = html;
}

function renderWatchlist(symbols) {
    const list = document.getElementById('watchlist-list');
    list.innerHTML = '';
    if (symbols.length === 0) {
        list.innerHTML = '<li>Your watchlist is empty. Add a symbol above.</li>';
        return;
    }
    symbols.forEach(symbol => {
        const li = document.createElement('li');
        li.textContent = symbol;
        const removeBtn = document.createElement('button');
        removeBtn.textContent = 'Remove';
        removeBtn.className = 'remove-symbol-btn';
        removeBtn.dataset.symbol = symbol;
        li.appendChild(removeBtn);
        list.appendChild(li);
    });
}

// --- UI HELPER & EVENT FUNCTIONS ---

function showLoadingSpinner(show) { document.getElementById('loading-spinner').style.display = show ? 'block' : 'none'; }
function showError(message) {
    const errorDiv = document.getElementById('error-message');
    errorDiv.textContent = message || '';
    errorDiv.style.display = message ? 'block' : 'none';
}

function checkForAlert(assetName, timeframe, newSignal) {
    const key = `${assetName}-${timeframe}`;
    if (newSignal.bars_since === 0 && newSignal.status !== "Neutral" && (previousSignals[key]?.status !== newSignal.status)) {
        const alertList = document.getElementById('alerts-list');
        if (alertList.children.length === 1 && alertList.children[0].textContent.includes('No new alerts')) {
            alertList.innerHTML = '';
        }
        const newAlert = document.createElement('li');
        newAlert.textContent = `[${new Date().toLocaleTimeString()}] New ${newSignal.status} crossover: ${assetName} on ${timeframe}.`;
        alertList.prepend(newAlert);
    }
    previousSignals[key] = newSignal;
}

function debounce(func, delay = 300) {
    let timeoutId;
    return (...args) => {
        clearTimeout(timeoutId);
        timeoutId = setTimeout(() => func.apply(this, args), delay);
    };
}

function addSearchFilter(inputId, tableId) {
    const input = document.getElementById(inputId);
    const table = document.getElementById(tableId);
    
    input.addEventListener('input', debounce(() => {
        const filter = input.value.toUpperCase();
        const rows = table.querySelectorAll('tbody tr');
        rows.forEach(row => {
            const symbolText = row.cells[0]?.textContent.toUpperCase();
            row.style.display = symbolText?.includes(filter) ? '' : 'none';
        });
    }));
}

// --- INITIALIZATION ---

async function runDataRefreshCycle() {
    const watchlist = await fetchWatchlist();
    if (watchlist === null) return; 
    
    renderWatchlist(watchlist);

    const screenerData = await fetchScreenerData(watchlist);
    if (screenerData) {
        populateAllTables(screenerData);
        document.getElementById('last-updated').textContent = new Date().toLocaleTimeString();
    }
}

document.addEventListener('DOMContentLoaded', async () => {
    await fetchAllSymbols(); 
    populateSymbolDatalist(masterSymbolList); // Populate the new datalist
    await runDataRefreshCycle(); 

    setInterval(runDataRefreshCycle, REFRESH_INTERVAL_MS);

    // Set up event listeners
    addSearchFilter('search-input', 'crypto-table');
    
    document.getElementById('fetch-crossovers').addEventListener('click', async () => {
        // UPDATED: Get value from the new input ID
        const symbol = document.getElementById('symbol-search-input').value;
        const timeframe = document.getElementById('timeframe-select').value;
        const container = document.getElementById('crossover-results');
        container.innerHTML = '<p>Loading crossover data...</p>';
        const crossovers = await fetchHistoricalCrossovers(symbol, timeframe);
        displayCrossovers(crossovers);
    });

    document.querySelector('.tabs').addEventListener('click', (e) => {
        if (e.target.matches('.tab-link')) {
            const tabName = e.target.dataset.tab;
            document.querySelectorAll(".tab-content").forEach(tab => tab.classList.remove("active"));
            document.querySelectorAll(".tab-link").forEach(link => link.classList.remove("active"));
            document.getElementById(tabName).classList.add("active");
            e.target.classList.add("active");
        }
    });

    document.getElementById('add-symbol-button').addEventListener('click', async () => {
        const input = document.getElementById('add-symbol-input');
        const symbol = input.value.trim().toUpperCase();
        if (symbol) {
            const updatedWatchlist = await addSymbolToWatchlist(symbol);
            if (updatedWatchlist) {
                renderWatchlist(updatedWatchlist);
                input.value = '';
                await runDataRefreshCycle();
            }
        }
    });

    document.getElementById('watchlist-list').addEventListener('click', async (e) => {
        if (e.target.matches('.remove-symbol-btn')) {
            const symbol = e.target.dataset.symbol;
            const updatedWatchlist = await removeSymbolFromWatchlist(symbol);
            if (updatedWatchlist) {
                renderWatchlist(updatedWatchlist);
                await runDataRefreshCycle();
            }
        }
    });
    
    document.getElementById('crypto-table').addEventListener('click', async (e) => {
        if (e.target.matches('.asset-name.clickable')) {
            const symbol = e.target.dataset.symbol;
            const updatedWatchlist = await addSymbolToWatchlist(symbol);
            if (updatedWatchlist) {
                renderWatchlist(updatedWatchlist);
            }
        }
    });
});