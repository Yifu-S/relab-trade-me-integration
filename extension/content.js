// Content script for Relab Trade Me Integration
(function () {
  "use strict";

  console.log("Relab: Content script loaded!");

  // Configuration
  const BACKEND_URL = "http://localhost:5000";

  // Wait for page to load
  function waitForElement(selector, timeout = 5000) {
    return new Promise((resolve, reject) => {
      const element = document.querySelector(selector);
      if (element) {
        resolve(element);
        return;
      }

      const observer = new MutationObserver((mutations) => {
        const element = document.querySelector(selector);
        if (element) {
          observer.disconnect();
          resolve(element);
        }
      });

      observer.observe(document.body, {
        childList: true,
        subtree: true,
      });

      setTimeout(() => {
        observer.disconnect();
        reject(new Error(`Element ${selector} not found within ${timeout}ms`));
      }, timeout);
    });
  }

  // Create Relab analysis button
  function createRelabButton() {
    const button = document.createElement("button");
    button.id = "relab-analyze-btn";
    button.className = "relab-analyze-button";
    button.innerHTML = `
            <i class="relab-icon">🏠</i>
            <span>Get Relab Data</span>
        `;
    button.addEventListener("click", handleRelabAnalysis);
    return button;
  }

  // Handle Relab analysis
  async function handleRelabAnalysis() {
    const button = document.getElementById("relab-analyze-btn");
    const originalText = button.innerHTML;

    try {
      // Show loading state
      button.innerHTML =
        '<i class="relab-icon">⏳</i><span>Analyzing...</span>';
      button.disabled = true;

      // Get current page URL
      const currentUrl = window.location.href;

      // Call backend API
      const response = await fetch(`${BACKEND_URL}/api/property/analyze`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ trademe_url: currentUrl }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();

      if (data.error) {
        throw new Error(data.error);
      }

      // Display results in a modal
      displayResults(data);
    } catch (error) {
      console.error("Relab analysis error:", error);
      showError(`Analysis failed: ${error.message}`);
    } finally {
      // Restore button state
      button.innerHTML = originalText;
      button.disabled = false;
    }
  }

  // Display analysis results
  function displayResults(data) {
    try {
      console.log("Displaying results:", data);

      // Remove existing modal if any
      const existingModal = document.getElementById("relab-modal");
      if (existingModal) {
        existingModal.remove();
      }

      // Create modal
      const modal = document.createElement("div");
      modal.id = "relab-modal";
      modal.className = "relab-modal";

      const trademeData = data.trademe_data || {};
      const relabData = data.relab_data || {};
      const cmaData = data.cma_analysis || {};

      modal.innerHTML = `
              <div class="relab-modal-content">
                  <div class="relab-modal-header">
                      <h3>🏠 Relab Property Analysis</h3>
                      <button class="relab-modal-close" onclick="this.closest('.relab-modal').remove()">×</button>
                  </div>
                  
                  <div class="relab-modal-body">
                      <!-- Relab Data Section -->
                      <div class="relab-data-main">
                          <h4>📊 Relab Property Data</h4>
                          <div class="relab-data-grid">
                              <div class="relab-data-item">
                                                                     <strong>Capital Value:</strong> ${
                                                                       relabData.cv
                                                                         ? "$" +
                                                                           (
                                                                             relabData.cv ||
                                                                             0
                                                                           ).toLocaleString()
                                                                         : "N/A"
                                                                     }
                              </div>
                              <div class="relab-data-item">
                                  <strong>Land Title:</strong> ${
                                    relabData.land_title || "N/A"
                                  }
                              </div>
                                                              <div class="relab-data-item">
                                    <strong>Land Area:</strong> ${
                                      relabData.land_area
                                        ? relabData.land_area + " m²"
                                        : "N/A"
                                    }
                                </div>
                                <div class="relab-data-item">
                                    <strong>Floor Area:</strong> ${
                                      relabData.floor_area
                                        ? relabData.floor_area + " m²"
                                        : "N/A"
                                    }
                                </div>
                                                                <div class="relab-data-item">
                                    <strong>Year Built:</strong> ${
                                      relabData.year_built || "N/A"
                                    }
                                </div>
                              <div class="relab-data-item">
                                  <strong>Bedrooms:</strong> ${
                                    relabData.bedrooms || "N/A"
                                  }
                              </div>
                              <div class="relab-data-item">
                                  <strong>Bathrooms:</strong> ${
                                    relabData.bathrooms || "N/A"
                                  }
                              </div>
                              <div class="relab-data-item">
                                  <strong>Address:</strong> ${
                                    trademeData.address || "N/A"
                                  }
                              </div>
                              <div class="relab-data-item">
                                  <strong>Land Title:</strong> ${
                                    relabData.land_title || "N/A"
                                  }
                              </div>
                          </div>
                          
                          <!-- Relab Property Link -->
                          <div class="relab-property-link">
                              <a href="https://relab.co.nz/property/${encodeURIComponent(
                                trademeData.address || ""
                              )}" target="_blank" class="relab-link-btn">
                                  🔗 View Full Property Details on Relab
                              </a>
                          </div>
                      </div>

                    <!-- CMA Analysis -->
                                         ${
                                           cmaData.valuation_range
                                             ? `
                          <div class="relab-cma-section">
                              <h4>📈 Market Analysis (Based on ${
                                cmaData.comparable_sales
                                  ? cmaData.comparable_sales.length
                                  : 0
                              } Comparable Properties)</h4>
                              <div class="relab-valuation-highlight">
                                  <div class="relab-valuation-range">
                                      <strong>Valuation Range:</strong> 
                                      $${(
                                        cmaData.valuation_range?.overall_range
                                          ?.low || 0
                                      ).toLocaleString()} - $${(
                                                 cmaData.valuation_range
                                                   ?.overall_range?.high || 0
                                               ).toLocaleString()}
                                  </div>
                                  <div class="relab-valuation-mid">
                                      <strong>Mid-Point:</strong> $${(
                                        cmaData.valuation_range?.overall_range
                                          ?.mid || 0
                                      ).toLocaleString()}
                                  </div>
                                  <div class="relab-confidence">
                                      <strong>Confidence:</strong> ${
                                        cmaData.analysis_summary
                                          .confidence_level
                                      }
                                  </div>
                              </div>
                            
                            <div class="relab-benchmarks">
                                <div class="relab-benchmark">
                                    <strong>Sale/CV Ratio:</strong> ${
                                      cmaData.benchmarks?.sale_cv_ratio || "N/A"
                                    }
                                </div>
                                <div class="relab-benchmark">
                                    <strong>Floor Rate:</strong> $${(
                                      cmaData.benchmarks?.floor_rate_per_sqm ||
                                      0
                                    ).toLocaleString()}/m²
                                </div>
                                <div class="relab-benchmark">
                                    <strong>Land Rate:</strong> $${(
                                      cmaData.benchmarks?.land_rate_per_sqm || 0
                                    ).toLocaleString()}/m²
                                </div>
                            </div>
                            
                            <div class="relab-recommendation">
                                <strong>Recommendation:</strong> ${
                                  cmaData.analysis_summary?.recommendation ||
                                  "Based on market analysis, this property shows typical market performance."
                                }
                            </div>
                        </div>
                    `
                                             : ""
                                         }
                </div>
                
                <div class="relab-modal-footer">
                    <button class="relab-btn relab-btn-primary" onclick="saveToWatchlist()">
                        💾 Save to Watchlist
                    </button>
                    <button class="relab-btn relab-btn-secondary" onclick="generateAIReport()">
                        🤖 AI Report
                    </button>
                    <button class="relab-btn relab-btn-secondary" onclick="openFullDashboard()">
                        📊 Full Dashboard
                    </button>
                </div>
            </div>
        `;

      document.body.appendChild(modal);
    } catch (error) {
      console.error("Error displaying results:", error);
      showError(`Display error: ${error.message}`);
    }
  }

  // Show error message
  function showError(message) {
    const errorDiv = document.createElement("div");
    errorDiv.className = "relab-error";
    errorDiv.innerHTML = `
            <div class="relab-error-content">
                <span>❌ ${message}</span>
                <button onclick="this.parentElement.parentElement.remove()">×</button>
            </div>
        `;
    document.body.appendChild(errorDiv);

    // Auto-remove after 5 seconds
    setTimeout(() => {
      if (errorDiv.parentElement) {
        errorDiv.remove();
      }
    }, 5000);
  }

  // Save to watchlist
  async function saveToWatchlist() {
    try {
      const response = await fetch(`${BACKEND_URL}/api/property/save`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ property_url: window.location.href }),
      });

      const data = await response.json();
      showNotification(data.message || "Property saved to watchlist");
    } catch (error) {
      showError("Failed to save to watchlist");
    }
  }

  // Generate AI report
  async function generateAIReport() {
    try {
      const response = await fetch(`${BACKEND_URL}/api/property/report`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ property_url: window.location.href }),
      });

      const data = await response.json();

      // Display AI report in modal
      const modal = document.getElementById("relab-modal");
      if (modal) {
        const body = modal.querySelector(".relab-modal-body");
        const reportDiv = document.createElement("div");
        reportDiv.className = "relab-ai-report";
        reportDiv.innerHTML = `
                    <h4>🤖 AI Property Report</h4>
                    <p><strong>Summary:</strong> ${data.summary}</p>
                    <div class="relab-ai-recommendations">
                        <h5>Recommendations:</h5>
                        <ul>
                            ${data.recommendations
                              .map((rec) => `<li>${rec}</li>`)
                              .join("")}
                        </ul>
                    </div>
                    <div class="relab-ai-risks">
                        <h5>Risk Factors:</h5>
                        <ul>
                            ${data.risk_factors
                              .map((risk) => `<li>${risk}</li>`)
                              .join("")}
                        </ul>
                    </div>
                `;
        body.appendChild(reportDiv);
      }
    } catch (error) {
      showError("Failed to generate AI report");
    }
  }

  // Open full dashboard
  function openFullDashboard() {
    window.open(
      `${BACKEND_URL}?url=${encodeURIComponent(window.location.href)}`,
      "_blank"
    );
  }

  // Show notification
  function showNotification(message) {
    const notification = document.createElement("div");
    notification.className = "relab-notification";
    notification.innerHTML = `
            <div class="relab-notification-content">
                <span>✅ ${message}</span>
                <button onclick="this.parentElement.parentElement.remove()">×</button>
            </div>
        `;
    document.body.appendChild(notification);

    // Auto-remove after 3 seconds
    setTimeout(() => {
      if (notification.parentElement) {
        notification.remove();
      }
    }, 3000);
  }

  // Initialize extension
  async function initialize() {
    try {
      console.log("Relab: Starting initialization...");

      // Wait for the page to be ready
      await waitForElement(
        '.listing-title, h1, .property-details, .listing-header, .price, [data-testid="listing-title"]',
        10000
      );

      // Find a good place to inject the button
      const targetSelectors = [
        ".listing-title",
        ".property-details",
        ".listing-header",
        "h1",
        ".price",
        '[data-testid="listing-title"]',
        ".listing-title h1",
        ".property-header",
        ".listing-details",
      ];

      let targetElement = null;
      for (const selector of targetSelectors) {
        targetElement = document.querySelector(selector);
        if (targetElement) {
          console.log("Relab: Found target element:", selector);
          break;
        }
      }

      if (!targetElement) {
        console.log(
          "Relab: No suitable target element found, trying fallback..."
        );
        // Fallback: try to find any element that might work
        const fallbackSelectors = [
          "main",
          ".main-content",
          ".listing-content",
          ".property-content",
          "article",
          ".container",
        ];

        for (const selector of fallbackSelectors) {
          targetElement = document.querySelector(selector);
          if (targetElement) {
            console.log("Relab: Using fallback element:", selector);
            break;
          }
        }
      }

      if (!targetElement) {
        console.log("Relab: No target element found at all");
        return;
      }

      // Create and inject the button
      const button = createRelabButton();

      // Insert after the target element
      targetElement.parentNode.insertBefore(button, targetElement.nextSibling);

      console.log("Relab Trade Me Integration initialized successfully");
    } catch (error) {
      console.error("Relab: Failed to initialize:", error);
    }
  }

  // Make functions globally available for onclick handlers
  window.saveToWatchlist = saveToWatchlist;
  window.generateAIReport = generateAIReport;
  window.openFullDashboard = openFullDashboard;

  // Add manual trigger function
  window.triggerRelabAnalysis = function () {
    console.log("Relab: Manual trigger activated");
    handleRelabAnalysis();
  };

  // Add a floating button as fallback
  function addFloatingButton() {
    const existingButton = document.getElementById("relab-floating-btn");
    if (existingButton) return;

    const floatingButton = document.createElement("button");
    floatingButton.id = "relab-floating-btn";
    floatingButton.innerHTML = "🏠 Relab";
    floatingButton.style.cssText = `
         position: fixed;
         top: 20px;
         right: 20px;
         z-index: 10000;
         background: linear-gradient(135deg, #2ecc71 0%, #27ae60 100%);
         color: white;
         border: none;
         border-radius: 8px;
         padding: 10px 15px;
         font-size: 14px;
         font-weight: 600;
         cursor: pointer;
         box-shadow: 0 2px 8px rgba(46, 204, 113, 0.3);
         transition: all 0.3s ease;
     `;

    floatingButton.addEventListener("click", handleRelabAnalysis);
    document.body.appendChild(floatingButton);

    console.log("Relab: Added floating button as fallback");
  }

  // Always add floating button as primary method
  setTimeout(addFloatingButton, 1000);

  // Start initialization when DOM is ready
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initialize);
  } else {
    initialize();
  }

  // Also try to initialize after a delay in case the page loads dynamically
  setTimeout(initialize, 2000);

  // Listen for dynamic content changes
  const observer = new MutationObserver((mutations) => {
    for (const mutation of mutations) {
      if (mutation.type === "childList" && mutation.addedNodes.length > 0) {
        // Check if any new elements might be relevant
        const hasRelevantContent = Array.from(mutation.addedNodes).some(
          (node) => {
            if (node.nodeType === Node.ELEMENT_NODE) {
              return (
                node.querySelector &&
                (node.querySelector(".listing-title") ||
                  node.querySelector("h1") ||
                  node.querySelector(".property-details"))
              );
            }
            return false;
          }
        );

        if (hasRelevantContent) {
          console.log("Relab: Detected new content, re-initializing...");
          setTimeout(initialize, 500);
        }
      }
    }
  });

  observer.observe(document.body, {
    childList: true,
    subtree: true,
  });
})();
