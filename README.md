## GAM + GA4 Dashboard Visualization (RPM)

### Problem
Advertising and analytics data live in different systems (Google Ad Manager and Google Analytics 4). Teams often export CSVs, manually clean and join columns like Date and URL, and try to compare engagement (views, users, time) against monetization (impressions, revenue, eCPM). This is slow, error-prone, and makes it hard to spot opportunities and issues by page and over time.

### Solution
This Streamlit dashboard lets you upload two CSVs — one from Google Ad Manager (GAM) and one from Google Analytics 4 (GA4) — and instantly:
- Automatically detect and clean key columns (Date, URL, Views/Users/Engagement, Impressions/Revenue/eCPM)
- Standardize URL paths and parse numeric/time fields
- Merge the datasets on `date` + `url`
- Filter by date range and URLs
- Visualize trends and relationships with interactive charts

### Value
- Faster decisions: See engagement and monetization together per URL and date without manual wrangling
- Consistency: Opinionated cleaning for currency, numbers, and H:MM:SS durations
- Insight: Compare GA views vs GAM impressions; track GA/GAM revenue over time; export a unified table for further analysis

---

### Features
- CSV uploaders for GA4 and GAM
- Auto column detection with a readable mapping preview
- Cleaning for commas, dollar signs, percentages, and time strings
- URL normalization for consistent joining
- Filters: date range, multi-select URLs
- Charts:
  - Aggregated time series for available metrics
  - GA Views vs GAM Impressions scatter
  - GA Revenue vs GAM Revenue over time
- Sample loaders for provided example CSVs

---

### Getting Started

Prerequisites:
- Python 3.9+ (macOS users: ensure Command Line Tools are installed)

Install dependencies and run:
```bash
cd /Users/richcao/Desktop/Cursor_Projects/ad_dashboard
python3 -m pip install -r requirements.txt
python3 -m streamlit run app.py
```

Open your browser at `http://localhost:8501`.

If you see a prompt about Streamlit usage emails, you can press Enter to skip. A `.streamlit/config.toml` is included to run headless and disable usage collection by default.

---

### Using the App
1) In the sidebar, upload your GA4 CSV and GAM CSV.
2) Optionally, click the sample buttons to load included examples.
3) Review detected column mappings (expanders below each preview).
4) Use Filters to narrow by date range and URLs.
5) Explore the Data table and interactive charts.

Note: The app expects at minimum `date` and `url` to align the datasets. If any key column is missing, it will show what it detected so you can adjust the CSV headers or re-export.

---

### Expected CSV Headers (flexible)
The app will try multiple aliases for each logical field:

- GA4
  - Date: `Date`
  - URL: `Page path and query string` | `Page` | `Page path`
  - Views: `Views` | `Screen Page Views` | `Pageviews`
  - Users: `Users`
  - Avg. Engagement Time: `Avg. Engagement Time` | `Average Engagement Time` (H:MM:SS or MM:SS)
  - Total Ad Revenue: `Total Ad Revenue` | `Ad Revenue` | `Revenue`

- GAM
  - Date: `Date`
  - URL: `Custom Targeting (URL)` | `URL` | `Key-Value URL`
  - Total Impressions: `Total Impressions` | `Impressions`
  - Total Revenue: `Total Revenue` | `Revenue` | `Ad Server Revenue`
  - Total eCPM: `Total eCPM` | `eCPM`

If your headers differ, rename them to any of the aliases above or update the alias lists in `app.py`.

---

### Project Structure
```
ad_dashboard/
  app.py                    # Streamlit app
  requirements.txt          # Python dependencies
  .streamlit/config.toml    # Streamlit config (headless, port, usage off)
```

Your GitHub repository:
- `https://github.com/richacao-creator/GAM_GA4_Dashboard_Visualization_RPM.git`

---

### Development Notes
- Code style: emphasize readability with descriptive names and early returns
- Charts use Altair; table and controls via Streamlit
- Numeric cleaning removes commas, `$`, `%`; time parsed to seconds
- URL normalization trims trailing slashes (except root) and enforces a leading `/`

Run checks:
```bash
python3 -m streamlit run app.py
```

---

### Roadmap Ideas
- Column mapping UI to manually override auto-detection
- Per-URL detail page with RPM/visits breakdowns
- Export merged dataset as CSV
- Watchdog for faster reloads
- Containerization for easy deploy
