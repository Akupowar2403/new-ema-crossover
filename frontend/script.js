// --- CONFIGURATION & STATE ---
const API_BASE_URL = 'http://127.0.0.1:8000';
const WS_URL = 'ws://127.0.0.1:8000/ws';
const REFRESH_INTERVAL_MS = 15 * 60 * 1000;
const TIME_FRAMES = ["1m", "15m", "1h", "4h", "1d"];
let previousSignals = {};
let masterSymbolList = [];

// --- WEBSOCKET CONNECTION ---
function connectWebSocket() {
    console.log("Attempting to connect to WebSocket...");
    const ws = new WebSocket(WS_URL);

    ws.onopen = () => {
        console.log("WebSocket connection established.");
    };

// In script.js

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    
    // This block handles the 30-second pop-up alert when a crossover happens
    if (data.type === 'crossover_alert') {
        const alertList = document.getElementById('alerts-list');
        
        if (alertList.children.length === 1 && alertList.children[0].textContent.includes('No new alerts')) {
            alertList.innerHTML = '';
        }

        const newAlert = document.createElement('li');
        const alertReceivedTime = new Date().toLocaleTimeString();
        const crossoverEventTime = new Date(data.crossover_timestamp * 1000).toLocaleTimeString();
        newAlert.textContent = `[${alertReceivedTime}] New ${data.status} crossover on ${data.symbol} (${data.timeframe}) confirmed at ${crossoverEventTime}.`;
        
        alertList.prepend(newAlert);

        const VISIBLE_DURATION_MS = 30000;
        const FADE_ANIMATION_MS = 500;

        setTimeout(() => {
            newAlert.classList.add('fade-out');
        }, VISIBLE_DURATION_MS);

        setTimeout(() => {
            newAlert.remove();
        }, VISIBLE_DURATION_MS + FADE_ANIMATION_MS);

    } 
    // --- NEW LOGIC: This block handles the continuous bar count updates ---
    else if (data.type === 'live_update') {
        // This quietly updates the table cell with the latest "bars since" count
        updateTableCell(data.symbol, data.timeframe, data.signal);
    }
};

    ws.onclose = () => {
        console.log("WebSocket connection closed. Reconnecting in 5 seconds...");
        setTimeout(connectWebSocket, 5000);
    };

    ws.onerror = (error) => {
        console.error("WebSocket error:", error);
    };
}

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

// In script.js

function updateTableCell(symbol, timeframe, signal) {
    const table = document.getElementById('crypto-table');
    const row = table.querySelector(`[data-symbol="${symbol}"]`)?.closest('tr');
    if (!row) return;

    const timeframeIndex = TIME_FRAMES.indexOf(timeframe);
    if (timeframeIndex === -1) return;

    const cell = row.cells[timeframeIndex + 1];
    if (!cell) return;
    
    // --- THIS IS THE CRUCIAL UPDATE ---
    // Use the helper function to get the correct color class
    const statusClass = getTrendStrengthClass(signal.status, signal.bars_since);
    
    const barsText = signal.bars_since !== null ? `(${signal.bars_since} bars)` : '';
    const text = signal.status !== "Neutral" && signal.status !== "N/A"
        ? `${signal.status.substring(0, 4)} ${barsText}`
        : signal.status;

    cell.className = statusClass;
    cell.textContent = text;
}

function populateAllTables(data) {
    populateTable('crypto-table', data.crypto || []);
}


function updateSymbolDropdown(watchlistSymbols) {
    const selectElement = document.getElementById('symbol-select');
    if (!selectElement) return;

    const currentSelection = selectElement.value;
    selectElement.innerHTML = ''; 

    if (watchlistSymbols.length === 0) {
        selectElement.innerHTML = '<option value="">Add a symbol to your watchlist</option>';
        return;
    }

    watchlistSymbols.forEach(symbol => {
        const option = document.createElement('option');
        option.value = symbol;
        option.textContent = symbol;
        selectElement.appendChild(option);
    });

    if (watchlistSymbols.includes(currentSelection)) {
        selectElement.value = currentSelection;
    }
}


function populateTable(tableId, assetsData) {
    const table = document.getElementById(tableId);
    if (!table.querySelector('thead')) {
        const thead = table.createTHead();
        const headerRow = thead.insertRow();
        ['Symbol', ...TIME_FRAMES].forEach(text => {
            const th = document.createElement('th');
            th.textContent = text;
            headerRow.appendChild(th);
        });
    }
    let tbody = table.querySelector('tbody') || table.createTBody();
    tbody.innerHTML = '';
    const fragment = document.createDocumentFragment();

    assetsData.forEach(asset => {
        const tr = document.createElement('tr');
        tr.dataset.symbol = asset.name;
        
        let rowContent = `<td class="asset-name clickable" title="Add ${asset.name} to Watchlist">${asset.name}</td>`;
        
        TIME_FRAMES.forEach(tf => {
            const signal = asset.timeframes?.[tf] || { status: 'N/A', bars_since: null };
            const status = signal.status || 'N/A'; 
            const bars_since = signal.bars_since;
            
            // --- THIS IS THE UPDATED LINE ---
            // It now calls your new helper function to get the correct color class
            const statusClass = getTrendStrengthClass(status, bars_since);
            
            const barsText = bars_since !== null ? `(${bars_since} bars)` : '';
            const text = status !== "Neutral" && status !== "N/A"
                ? `${status.substring(0, 4)} ${barsText}`
                : status;

            rowContent += `<td class="${statusClass}">${text}</td>`;
        });
        tr.innerHTML = rowContent;
        fragment.appendChild(tr);
    });
    tbody.appendChild(fragment);
}

function populateSymbolDatalist(symbols) {
    // We target the new <datalist> element, not the old dropdown
    const datalist = document.getElementById('symbol-suggestions');
    if (!datalist) {
        console.error("Error: Could not find the datalist with ID 'symbol-suggestions'.");
        return;
    }

    // Clear any old options that might be there
    datalist.innerHTML = '';

    // Add each symbol from the master list as a new <option>
    symbols.forEach(symbol => {
        const option = document.createElement('option');
        // For a datalist, the browser uses the 'value' for both matching and displaying
        option.value = symbol;
        datalist.appendChild(option);
    });
}
// THIS FUNCTION IS CRUCIAL FOR THE COLOR SHADING
function getTrendStrengthClass(status, bars) {
    if (status === 'Bullish') {
        if (bars >= 0 && bars <= 10) return 'bullish-1';
        if (bars >= 11 && bars <= 40) return 'bullish-2';
        if (bars >= 41 && bars <= 60) return 'bullish-3';
        if (bars > 60) return 'bullish-4';
    } 
    else if (status === 'Bearish') {
        if (bars >= 0 && bars <= 10) return 'bearish-1';
        if (bars >= 11 && bars <= 40) return 'bearish-2';
        if (bars >= 41 && bars <= 60) return 'bearish-3';
        if (bars > 60) return 'bearish-4';
    }
    return 'neutral'; // Default class for "N/A"
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
    
    updateSymbolDropdown(watchlist); 
    renderWatchlist(watchlist);

    const screenerData = await fetchScreenerData(watchlist);
    if (screenerData) {
        populateAllTables(screenerData);
    }
}

function startLiveClock() {
    const timestampElement = document.getElementById('last-updated');
    if (!timestampElement) return;

    timestampElement.textContent = new Date().toLocaleTimeString();

    setInterval(() => {
        timestampElement.textContent = new Date().toLocaleTimeString();
    }, 1000);
}

// At the end of script.js

document.addEventListener('DOMContentLoaded', async () => {
    connectWebSocket();
    startLiveClock(); 
    
    // This part is crucial:
    // 1. Fetch the master list of all symbols
    await fetchAllSymbols(); 
    // 2. Immediately use that list to create the suggestions
    populateSymbolDatalist(masterSymbolList); // This line is likely missing

    // Fetches initial data for the screener table
    await runDataRefreshCycle();

    // Sets up the automatic refresh every 15 minutes
    setInterval(runDataRefreshCycle, REFRESH_INTERVAL_MS);
    
    // --- The rest of your event listeners ---
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
            const symbol = e.target.closest('tr').dataset.symbol;
            const updatedWatchlist = await addSymbolToWatchlist(symbol);
            if (updatedWatchlist) {
                renderWatchlist(updatedWatchlist);
            }
        }
    });
});