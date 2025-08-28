// popup.js
document.addEventListener('DOMContentLoaded', function () {
    const statusEl = document.getElementById('status');
    const openPanelBtn = document.getElementById('openPanel');
    const viewWatchlistBtn = document.getElementById('viewWatchlist');

    // Check if we are on a TM listing page
    chrome.tabs.query({ active: true, currentWindow: true }, function (tabs) {
        let currentTab = tabs[0];
        if (currentTab.url && currentTab.url.includes('trademe.co.nz') && currentTab.url.includes('/listing/')) {
            statusEl.textContent = 'On a Trade Me listing page.';
            statusEl.style.color = 'green';
            openPanelBtn.disabled = false;
        } else {
            statusEl.textContent = 'Not on a Trade Me listing page.';
            statusEl.style.color = 'red';
            openPanelBtn.disabled = true;
        }
    });

    openPanelBtn.addEventListener('click', () => {
        chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
            chrome.scripting.executeScript({
                target: { tabId: tabs[0].id },
                func: () => {
                    // This function runs in the context of the active tab
                    if (typeof createRelabPanel === 'function') {
                        createRelabPanel();
                    } else {
                        console.error('createRelabPanel function not found on the page.');
                        alert('Error: Could not open panel. Please refresh the page.');
                    }
                }
            });
        });
    });

    viewWatchlistBtn.addEventListener('click', () => {
        // Open a new tab with the watchlist (requires a dedicated watchlist page/view)
        // For demo, just alert that it's a feature
        alert("Watchlist view would open here. Backend API endpoint: GET /api/watchlist");
        // chrome.tabs.create({ url: chrome.runtime.getURL('watchlist.html') }); // If you create a watchlist.html page
    });
});