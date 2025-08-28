// content.js (Consolidated Phase II Code)

const BACKEND_URL = 'http://127.0.0.1:5000'; // Must match Flask server

// --- Utility Functions ---
function extractAddress() {
    const addressElement = document.querySelector('h1.tm-property-listing-body__location');
    if (addressElement) {
        return addressElement.textContent.trim();
    }
    console.warn("Could not find address element on Trade Me page.");
    return null;
}

function createRelabPanel() {
    const panel = document.createElement('div');
    panel.id = 'relab-assistant-panel';
    panel.innerHTML = `
        <div id="relab-header">
            <h3>Relab Assistant</h3>
            <button id="relab-close-btn">X</button>
        </div>
        <div id="relab-content">
            <button id="relab-fetch-btn">Get Relab Data</button>
            <div id="relab-loading" style="display:none;">Loading Relab data...</div>
            <div id="relab-results" style="display:none;"></div>
            <button id="relab-save-btn" style="display:none; margin-top: 10px;">Save to Watchlist</button>
        </div>
    `;
    document.body.appendChild(panel);

    document.getElementById('relab-close-btn').addEventListener('click', () => {
        panel.remove();
    });

    document.getElementById('relab-fetch-btn').addEventListener('click', fetchRelabData);
    document.getElementById('relab-save-btn').addEventListener('click', saveToWatchlist);
}

async function fetchRelabData() {
    const address = extractAddress();
    const price = extractPrice();
    const trademeUrl = window.location.href;

    if (!address) {
        alert("Could not find property address on this page.");
        return;
    }

    console.log("Fetching Relab data for:", address);

    const fetchBtn = document.getElementById('relab-fetch-btn');
    const loadingEl = document.getElementById('relab-loading');
    const resultsEl = document.getElementById('relab-results');

    fetchBtn.style.display = 'none';
    loadingEl.style.display = 'block';
    resultsEl.style.display = 'none';

    try {
        const response = await fetch(`${BACKEND_URL}/api/get_relab_data`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ address: address, trademe_url: trademeUrl, price: price })
        });

        const data = await response.json();
        console.log("Received data from backend:", data);

        if (data.success) {
            displayRelabResults(data.data);
        } else {
            resultsEl.innerHTML = `<p style="color: red;">Error: ${data.error}</p>`;
            resultsEl.style.display = 'block';
        }
    } catch (error) {
        console.error("Error fetching Relab data: ", error);
        // --- Handle null data from backend ---
        if (error.message.includes("Cannot read properties of null")) {
            resultsEl.innerHTML = `<p style="color: orange;">Warning: Backend reported success but returned no data. Check the backend logs for extraction errors.</p>`;
        } else {
            resultsEl.innerHTML = `<p style="color: red;">Failed to connect to backend: ${error.message}</p>`;
        }
        // --- End Handle null data ---
        resultsEl.style.display = 'block';
    } finally {
        loadingEl.style.display = 'none';
    }
}

function displayRelabResults(relabData) {
    const resultsEl = document.getElementById('relab-results');
    const saveBtn = document.getElementById('relab-save-btn');

    // --- Add a check for null or undefined data ---
    if (!relabData) {
        resultsEl.innerHTML = `<p style="color: orange;">Warning: Backend reported success but returned no data. There might have been an error during data extraction. Check the backend logs.</p>`;
        resultsEl.style.display = 'block';
        saveBtn.style.display = 'none';
        console.warn("displayRelabResults received null/undefined data:", relabData);
        return;
    }
    // --- End check ---

    let html = `<h4>Due Diligence Data </h4>`;
    html += `<ul>`;
    for (const [key, value] of Object.entries(relabData)) {
        // Skip the 'extracted_at' field from the list since it's already in the header
        if (key !== 'extracted_at') {
            html += `<li><strong>${key}:</strong> ${value}</li>`;
        }
    }
    html += `</ul>`;
    resultsEl.innerHTML = html;
    resultsEl.style.display = 'block';
    saveBtn.style.display = 'block';
}

function extractPrice() {
    const priceElement = document.querySelector('h2.tm-property-listing-body__price');
    if (priceElement) {
        return priceElement.textContent.trim();
    }
    return null;
}

async function saveToWatchlist() {
    const address = extractAddress();
    const relabDataDiv = document.getElementById('relab-results');
    const relabDataText = relabDataDiv ? relabDataDiv.innerText : 'No Relab data available';

    const propertyData = {
        address: address,
        url: window.location.href,
        relab_data: relabDataText,
        fetched_at: new Date().toISOString(),
    };

    try {
        const response = await fetch(`${BACKEND_URL}/api/save_to_watchlist`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ property_info: propertyData })
        });

        const data = await response.json();
        if (data.success) {
            alert("Property saved to watchlist!");
        } else {
            alert(`Error saving: ${data.error}`);
        }
    } catch (error) {
        console.error("Error saving to watchlist:", error);
        alert("Failed to save to watchlist.");
    }
}

// --- Main Execution ---
if (window.location.hostname === 'www.trademe.co.nz' &&
    window.location.pathname.startsWith('/a/property/residential/') &&
    window.location.pathname.includes('/listing/')) {

    console.log("Trade Me Relab Assistant: Detected property listing page.");

    window.addEventListener('load', () => {
        setTimeout(() => {
            const existingButton = document.getElementById('relab-open-panel-btn');
            if (!existingButton) {
                const openButton = document.createElement('button');
                openButton.id = 'relab-open-panel-btn';
                openButton.textContent = 'Open Relab Assistant';
                openButton.style.position = 'fixed';
                openButton.style.top = '10px';
                openButton.style.right = '10px';
                openButton.style.zIndex = '10000';
                openButton.style.padding = '10px';
                openButton.style.backgroundColor = '#007bff';
                openButton.style.color = 'white';
                openButton.style.border = 'none';
                openButton.style.borderRadius = '5px';
                openButton.style.cursor = 'pointer';
                openButton.addEventListener('click', createRelabPanel);
                document.body.appendChild(openButton);
            }
        }, 2000);
    });
}
