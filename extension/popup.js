// Popup script for Relab Trade Me Integration
document.addEventListener('DOMContentLoaded', function() {
    const statusDiv = document.getElementById('status');
    const statusText = document.getElementById('statusText');
    const openDashboardBtn = document.getElementById('openDashboard');
    const analyzeCurrentBtn = document.getElementById('analyzeCurrent');
    const settingsBtn = document.getElementById('settings');

    // Check backend connection
    async function checkConnection() {
        try {
            const response = await fetch('http://localhost:5000/', { 
                method: 'GET',
                mode: 'no-cors' // This will still throw an error if server is down
            });
            
            statusDiv.className = 'status connected';
            statusText.textContent = 'Connected to backend';
        } catch (error) {
            statusDiv.className = 'status disconnected';
            statusText.textContent = 'Backend not available';
        }
    }

    // Open dashboard
    openDashboardBtn.addEventListener('click', function() {
        chrome.tabs.create({
            url: 'http://localhost:5000'
        });
    });

    // Analyze current page
    analyzeCurrentBtn.addEventListener('click', function() {
        chrome.tabs.query({active: true, currentWindow: true}, function(tabs) {
            const currentTab = tabs[0];
            
            if (currentTab.url && currentTab.url.includes('trademe.co.nz/property')) {
                // Send message to content script to trigger analysis
                chrome.tabs.sendMessage(currentTab.id, {
                    action: 'triggerAnalysis'
                });
                
                // Close popup
                window.close();
            } else {
                alert('Please navigate to a Trade Me property page first.');
            }
        });
    });

    // Settings
    settingsBtn.addEventListener('click', function() {
        chrome.tabs.create({
            url: 'http://localhost:5000/settings'
        });
    });

    // Check connection on load
    checkConnection();
});
