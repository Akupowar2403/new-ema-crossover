// --- CONFIGURATION & STATE ---
const API_BASE_URL = 'http://127.0.0.1:8000';
const WS_URL = 'ws://127.0.0.1:8000/ws';
const REFRESH_INTERVAL_MS = 15 * 60 * 1000;
const TIME_FRAMES = ["1m", "15m", "1h", "4h", "1d"];
let masterSymbolList = [];

// --- HELPER FUNCTIONS ---

function startLiveClock() {
    const timestampElement = document.getElementById('last-updated');
    if (!timestampElement) return;
    timestampElement.textContent = new Date().toLocaleTimeString();
    setInterval(() => {
        timestampElement.textContent = new Date().toLocaleTimeString();
    }, 1000);
}

function interpolateColor(color1, color2, factor) {
    const result = color1.slice(1).match(/.{2}/g)
        .map((hex, i) => {
            const val1 = parseInt(hex, 16);
            const val2 = parseInt(color2.slice(1).match(/.{2}/g)[i], 16);
            const val = Math.round(val1 + factor * (val2 - val1));
            return val.toString(16).padStart(2, '0');
        });
    return `#${result.join('')}`;
}

function getDynamicTrendStyle(status, bars) {
    const bullishStart = '#2E7D32';
    const bullishEnd = '#E8F5E9';
    const bearishStart = '#C62828';
    const bearishEnd = '#FFEBEE';
    const neutralStyle = { backgroundColor: '#f1fafb', color: '#161c91' };

    if (bars === null || (status !== 'Bullish' && status !== 'Bearish')) {
        return neutralStyle;
    }

    const progress = Math.min((bars - 1) / 99, 1);

    if (status === 'Bullish') {
        const bgColor = interpolateColor(bullishStart, bullishEnd, progress);
        const textColor = progress > 0.6 ? '#000000' : '#FFFFFF';
        return { backgroundColor: bgColor, color: textColor };
    }

    if (status === 'Bearish') {
        const bgColor = interpolateColor(bearishStart, bearishEnd, progress);
        const textColor = progress > 0.6 ? '#000000' : '#FFFFFF';
        return { backgroundColor: bgColor, color: textColor };
    }

    return neutralStyle;
}

// --- NEW HELPER FUNCTION ---
/**
 * Adds a new row to the screener table with "Loading..." placeholders.
 * @param {string} symbol - The symbol to add (e.g., "BTCUSD").
 */
function addLoadingRowToTable(symbol) {
    const table = document.getElementById('crypto-table');
    const tbody = table.querySelector('tbody');
    if (!tbody || tbody.querySelector(`[data-symbol="${symbol}"]`)) {
        return; // Do nothing if table body doesn't exist or row is already there
    }

    const tr = document.createElement('tr');
    tr.dataset.symbol = symbol;

    let rowContent = `<td class="asset-name clickable" title="Add ${symbol} to Watchlist">${symbol}</td>`;
    
    const style = getDynamicTrendStyle('N/A', null); // Get neutral style
    const inlineStyle = `style="background-color:${style.backgroundColor}; color:${style.color};"`;

    TIME_FRAMES.forEach(() => {
        rowContent += `<td ${inlineStyle}>Loading...</td>`;
    });
    
    tr.innerHTML = rowContent;
    tbody.prepend(tr); // Add the new row to the top of the table
}
// ----------------------------


// --- WEBSOCKET CONNECTION ---
function connectWebSocket() {
    console.log("Attempting to connect to WebSocket...");
    const ws = new WebSocket(WS_URL);

    ws.onopen = () => console.log("WebSocket connection established.");

    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        
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
            setTimeout(() => newAlert.classList.add('fade-out'), VISIBLE_DURATION_MS);
            setTimeout(() => newAlert.remove(), VISIBLE_DURATION_MS + FADE_ANIMATION_MS);

        } else if (data.type === 'live_update') {
            updateTableCell(data.symbol, data.timeframe, data.signal);
        }
    };

    ws.onclose = () => {
        console.log("WebSocket connection closed. Reconnecting in 5 seconds...");
        setTimeout(connectWebSocket, 5000);
    };

    ws.onerror = (error) => console.error("WebSocket error:", error);
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
        showError("Error fetching screener data.");
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
        if (!response.ok) {
            const errData = await response.json();
            throw new Error(errData.detail || 'Failed to add symbol');
        }
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

function updateTableCell(symbol, timeframe, signal) {
    const table = document.getElementById('crypto-table');
    const row = table.querySelector(`[data-symbol="${symbol}"]`)?.closest('tr');
    if (!row) return;

    const timeframeIndex = TIME_FRAMES.indexOf(timeframe);
    if (timeframeIndex === -1) return;

    const cell = row.cells[timeframeIndex + 1];
    if (!cell) return;
    
    const style = getDynamicTrendStyle(signal.status, signal.bars_since);
    cell.style.backgroundColor = style.backgroundColor;
    cell.style.color = style.color;
    
    const barsText = signal.bars_since !== null ? `(${signal.bars_since} bars)` : '';
    const text = signal.status !== "Neutral" && signal.status !== "N/A"
        ? `${signal.status.substring(0, 4)} ${barsText}`
        : signal.status;

    cell.textContent = text;
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
            const style = getDynamicTrendStyle(signal.status, signal.bars_since);
            const inlineStyle = `style="background-color:${style.backgroundColor}; color:${style.color};"`;
            const barsText = signal.bars_since !== null ? `(${signal.bars_since} bars)` : '';
            const text = signal.status !== "Neutral" && signal.status !== "N/A"
                ? `${signal.status.substring(0, 4)} ${barsText}`
                : signal.status;
            rowContent += `<td ${inlineStyle}>${text}</td>`;
        });
        tr.innerHTML = rowContent;
        fragment.appendChild(tr);
    });
    tbody.appendChild(fragment);
}

function populateSymbolDatalist(symbols) {
    const datalist = document.getElementById('symbol-suggestions');
    if (!datalist) return;
    datalist.innerHTML = '';
    symbols.forEach(symbol => {
        const option = document.createElement('option');
        option.value = symbol;
        datalist.appendChild(option);
    });
}

// In script.js

function renderWatchlist(symbols) {
    const list = document.getElementById('watchlist-list');
    list.innerHTML = '';
    if (symbols.length === 0) {
        list.innerHTML = '<li>Your watchlist is empty.</li>';
        return;
    }
    
    symbols.forEach(symbol => {
        // Create the list item
        const li = document.createElement('li');

        // Create the new '-' remove button
        const removeBtn = document.createElement('button');
        removeBtn.textContent = '−'; // Using the minus sign character
        removeBtn.className = 'remove-symbol-btn';
        removeBtn.dataset.symbol = symbol;
        removeBtn.title = `Remove ${symbol}`; // Add a helpful tooltip

        // Create a span for the symbol name
        const symbolSpan = document.createElement('span');
        symbolSpan.textContent = symbol;
        
        // Add the button and the name to the list item
        li.appendChild(removeBtn);
        li.appendChild(symbolSpan);

        list.appendChild(li);
    });
}

function showLoadingSpinner(show) { document.getElementById('loading-spinner').style.display = show ? 'block' : 'none'; }
function showError(message) {
    const errorDiv = document.getElementById('error-message');
    errorDiv.textContent = message || '';
    errorDiv.style.display = message ? 'block' : 'none';
}

// --- INITIALIZATION ---
async function runDataRefreshCycle() {
    const watchlist = await fetchWatchlist();
    if (watchlist === null) return;
    renderWatchlist(watchlist);
    const screenerData = await fetchScreenerData(watchlist);
    if (screenerData) {
        populateTable('crypto-table', screenerData.crypto || []);
    }
}

document.addEventListener('DOMContentLoaded', async () => {
    connectWebSocket();
    startLiveClock(); 
    
    await fetchAllSymbols(); 
    populateSymbolDatalist(masterSymbolList);

    await runDataRefreshCycle();
    setInterval(runDataRefreshCycle, REFRESH_INTERVAL_MS);
    
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
                // --- MODIFIED ---
                // Instantly add a "Loading..." row to the table for immediate feedback
                addLoadingRowToTable(symbol);
                // ----------------
            }
        }
    });

    document.getElementById('watchlist-list').addEventListener('click', async (e) => {
        if (e.target.matches('.remove-symbol-btn')) {
            const symbol = e.target.dataset.symbol;
            const updatedWatchlist = await removeSymbolFromWatchlist(symbol);
            if (updatedWatchlist) {
                renderWatchlist(updatedWatchlist);
                // --- MODIFIED ---
                // Instantly remove the row from the table for immediate feedback
                document.querySelector(`#crypto-table tr[data-symbol="${symbol}"]`)?.remove();
                // ----------------
            }
        }
    });
    
    document.getElementById('crypto-table').addEventListener('click', async (e) => {
        if (e.target.matches('.asset-name.clickable')) {
            const symbol = e.target.closest('tr').dataset.symbol;
            const updatedWatchlist = await addSymbolToWatchlist(symbol);
            if (updatedWatchlist) {
                renderWatchlist(updatedWatchlist);
                 // --- MODIFIED ---
                // Instantly add a "Loading..." row to the table for immediate feedback
                addLoadingRowToTable(symbol);
                // ----------------
            }
        }
    });
});