// Background script for Relab Trade Me Integration
chrome.runtime.onInstalled.addListener(() => {
    console.log('Relab Trade Me Integration installed');
});

// Handle messages from content script
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === 'analyzeProperty') {
        // Forward to backend
        fetch('http://localhost:5000/api/property/analyze', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ trademe_url: request.url })
        })
        .then(response => response.json())
        .then(data => {
            sendResponse({ success: true, data: data });
        })
        .catch(error => {
            sendResponse({ success: false, error: error.message });
        });
        
        return true; // Keep message channel open for async response
    }
});

// Handle extension icon click
chrome.action.onClicked.addListener((tab) => {
    if (tab.url && tab.url.includes('trademe.co.nz/property')) {
        // Open the dashboard in a new tab
        chrome.tabs.create({
            url: 'http://localhost:5000?url=' + encodeURIComponent(tab.url)
        });
    } else {
        // Show popup for non-property pages
        chrome.action.setPopup({ popup: 'popup.html' });
    }
});
