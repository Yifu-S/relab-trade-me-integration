**Workflow**

This solution enhances the user's existing browsing behavior on Trade Me with automated Relab integration, minimizing disruption.

1. **Setup & Installation:**

The user installs the custom Chrome browser extension.

The extension connects to a backend service (e.g., an n8n workflow or a simple server) that can access the Relab platform.

2. **Browsing & Discovery (User-Driven):**

The user browses Trade Me listings as they normally would, using Trade Me's search and filters. When they find a listing they are interested in, they land on the property's detail page.

3. **Initiating Due Diligence (User Action):**

The browser extension detects that the user is on a Trade Me listing page. It then displays Relab screen next to the Trademe listing page (split screen), so the user can view all the information from ™ and Relab together, to do their DD review.

It displays a new button on the page, for example, labeled "Get Relab Data" or "Analyze in Relab". The user clicks this button.

use playwright to login to Relab and search for this property. then click it through search bar suggestion to go to the property information page. Next, scrape the following information about this property on the listing page: Land title, Land area, Floor area, Year Built, Bedroom(s), Bathroom(s), List Date.

4. Based on the data scraped about this property, run a Comparative Market Analysis using Relab (CMA button on the property page), and come up with a market data based valuation range for this listing.

After clicking, the user will be redirected to a CMA page on Relab. There you will need to apply filters to search for similar sold properties. The ideal number of similar properties is around 10. If the current number of similar properties is too large or too small, you'll need to adjust the criteria to reach the desired number of similar properties.

- **Analyse subjective property in Relab, can capture the following attributes**
  - _Land title - use the same as subject site_
  - _Land area - +/- 20%_
  - _Floor area - +/- 20%_
  - _Build era - +/- one decade_
  - _Bedroom - +/- one_
  - _Bathroom - +/- one_
  - _Sale date - last 12 months_
- **Enter these attributes into Relab, and get a list of comparable sales**
  - _Need some logic to control the sensitivity of the above, best outcome is to get 8-10 comparable results_
  - _If you get too little, loosen the criteria_
  - _If you get too much, tighten the criteria_
- Based on the comparable sales records, come up with the following bench-marks
  - Broad range of the selected properties (8-10)
  - **Benchmark 1 -** Work out the average sale/cv ratio based on selected properties, and apply this ratio to subject property
  - **Benchmark 2 -** Work out the average floor $/sqm rate based on selected properties, and apply this ratio to subject property
  - **Benchmark 3 -** Work out the average land $/sqm rate based on selected properties, and apply this ratio to subject property
- Present the above information in a compact dashboard for the user

5. The user can save this property in a watch list

6. The user can run an AI generated property report on this property
