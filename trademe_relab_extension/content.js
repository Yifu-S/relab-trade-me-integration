// content.js

const BACKEND_URL = 'http://127.0.0.1:5000'; // Must match Flask server

// --- Utility Functions ---
function extractAddress() {
    // Try to find the address element on the Trade Me page
    // Selector needs to be updated based on actual TM page structure
    const addressElement = document.querySelector('h1.tm-property-listing-body__location');
    if (addressElement) {
        return addressElement.textContent.trim();
    }
    console.warn("Could not find address element on Trade Me page.");
    return null;
}

function extractPrice() {
    const priceElement = document.querySelector('h2.tm-property-listing-body__price');
    if (priceElement) {
        return priceElement.textContent.trim();
    }
    return null;
}

function createRelabPanel() {
    // Create the container div for the Relab panel
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

    // Add event listeners
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
        console.error("Error fetching Relab data:", error);
        resultsEl.innerHTML = `<p style="color: red;">Failed to connect to backend: ${error.message}</p>`;
        resultsEl.style.display = 'block';
    } finally {
        loadingEl.style.display = 'none';
    }
}

function displayRelabResults(relabData) {
    const resultsEl = document.getElementById('relab-results');
    const saveBtn = document.getElementById('relab-save-btn');

    let html = `<h4>Due Diligence Data (Fetched: ${new Date(relabData.extracted_at).toLocaleString()})</h4>`;
    html += `<ul>`;
    for (const [key, value] of Object.entries(relabData.key_points)) {
        html += `<li><strong>${key}:</strong> ${value}</li>`;
    }
    html += `</ul>`;

    // Display screenshots (paths from backend)
    if (relabData.screenshots && relabData.screenshots.length > 0) {
        html += `<h4>Screenshots:</h4>`;
        html += `<div id="relab-screenshots">`;
        relabData.screenshots.forEach(path => {
            // Note: The backend saves paths. The extension cannot directly access these files.
            // For a real implementation, the backend should serve the images or provide URLs.
            // This demo just shows the path.
            html += `<p>Screenshot saved: <code>${path}</code></p>`;
            // html += `<img src="${BACKEND_URL}/screenshots/${encodeURIComponent(path.split('/').pop())}" style="max-width: 100%; border: 1px solid #ccc; margin: 5px 0;">`; // If backend serves them
        });
        html += `</div>`;
    }

    resultsEl.innerHTML = html;
    resultsEl.style.display = 'block';
    saveBtn.style.display = 'block'; // Show save button after successful fetch
}

async function saveToWatchlist() {
    const address = extractAddress();
    // In a real scenario, you'd collect all the relevant data (TM + Relab)
    // For demo, just send the address and a placeholder
    const propertyData = {
        address: address,
        url: window.location.href,
        // fetched_at: new Date().toISOString(),
        // relab_data: ... // data from displayRelabResults
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
// Check if we are on a Trade Me property listing page
if (window.location.hostname === 'www.trademe.co.nz' &&
    window.location.pathname.startsWith('/a/property/residential/') &&
    window.location.pathname.includes('/listing/')) {

    console.log("Trade Me Relab Assistant: Detected property listing page.");

    // Wait a bit for the page to load fully
    window.addEventListener('load', () => {
        setTimeout(() => {
            // Inject the Relab panel button/link
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
        }, 2000); // Adjust delay if needed
    });
}