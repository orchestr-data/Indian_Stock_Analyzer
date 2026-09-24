# Indian Stock Fundamental Analyzer

A local, private fundamental research workstation for Indian equities (NSE/BSE).

**No cloud AI. No recommendations. No scores. No paid APIs.**

---

## Purpose

This tool helps you systematically investigate Indian companies using fundamental analysis. It imports financial data from Screener.in Excel exports, stores it locally, calculates financial ratios from first principles, and surfaces factual observations about trends and changes.

It is a **research aid**, not an investment advisor. It will never tell you to BUY, SELL, or HOLD. It will never score a company 82/100.

---

## Features

- Import Screener.in Excel exports locally
- Store data in a local DuckDB database — no cloud, no subscription
- Calculate 30+ financial metrics from first principles (ROE, ROCE, FCF, CAGR, etc.)
- Analyze historical trends with 3Y/5Y/10Y context
- Earnings quality analysis (CFO/PAT, FCF/PAT, receivable divergence)
- Balance sheet and debt analysis
- Valuation multiples with historical context
- Shareholding / promoter analysis
- Quarterly results analysis
- Peer comparison (companies you have imported)
- Import and search annual report PDFs
- Structured observations — factual, not verdicts
- Sector-aware analysis (17 sector configs)
- Explicit Consolidated / Standalone separation
- Corporate actions register — share count history, dividends, buybacks
- Historical valuation context (P/E and P/B snapshots, synthetic multiples)
- Earnings quality analysis (CFO/PAT, FCF/PAT, receivable divergence)

---

## Limitations

- **No automatic data download** — you must manually export from Screener.in
- **No real-time prices** — market data only comes from what Screener exports
- **No buy/sell/hold recommendations** — by design
- **No overall scores** — by design
- **No cloud AI** — local only (optional Ollama support planned)
- Historical P/E band analysis requires multiple Screener imports over time
- Corporate action data is entered manually (not in Screener Excel export)

---

## Architecture

```
Streamlit UI
    └── Application Services
            ├── Data Service (ingestion, normalization, validation)
            ├── Analysis Engine (trends, observations, earnings quality)
            └── Document Service (PDF extraction, local search)
                    └── DuckDB (local embedded database)
                            └── Parquet / Raw Files
```

The calculation engine is completely independent of the UI — pure functions, fully tested.

---

## Folder Structure

```
indian-stock-analyzer/
├── app.py                  # Streamlit entry point
├── requirements.txt
├── pyproject.toml
├── data/
│   ├── raw/companies/      # Original source files (never modified)
│   ├── processed/          # Intermediate data
│   └── stock_analyzer.duckdb
├── config/
│   ├── app.yaml
│   ├── thresholds.yaml     # Research heuristics (all configurable)
│   └── sectors/            # 17 sector YAML configs
├── src/
│   ├── calculations/       # Pure financial functions
│   ├── analysis/           # Trends, observations, earnings quality, valuations
│   ├── ingestion/          # Screener parser, normalizer, validator
│   ├── database/           # DuckDB schema and repository
│   ├── sectors/            # Sector registry and loader
│   ├── documents/          # PDF extraction and search
│   ├── models/             # Pydantic data models
│   └── ui/                 # Streamlit page components (16 pages)
└── tests/                  # 310+ unit tests
```

---

## Installation

### 1. Clone / download the project

```
cd C:\projects
git clone <repo-url> indian-stock-analyzer
cd indian-stock-analyzer
```

### 2. Create a virtual environment

**Windows:**
```
python -m venv .venv
.venv\Scripts\activate
```

**macOS / Linux:**
```
python -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```
pip install -r requirements.txt
```

### 4. Run the application

```
streamlit run app.py
```

The app will open in your browser at `http://localhost:8501`.

---

## Importing Screener Data

1. Go to [screener.in](https://www.screener.in) (free account required)
2. Search for a company (e.g. TCS, Infosys)
3. Click **Export to Excel** on the company page
4. In the app sidebar, click **Import Screener Excel**
5. Upload the downloaded `.xlsx` file
6. Optionally set the ticker symbol and sector
7. Click **Import**

The original file is preserved unchanged in `data/raw/companies/TICKER/screener/`.

---

## Importing Annual Reports (PDFs)

1. Download the annual report PDF from the company website or BSE/NSE
2. In the app sidebar, click **Import PDF Document**
3. Select the company (must be imported first)
4. Choose document type (Annual Report, Investor Presentation, etc.)
5. Enter the fiscal year
6. Click **Import PDF**

The PDF text will be extracted and made searchable in the **Documents** page.

---

## Statement Type (Consolidated vs Standalone)

Every financial record is explicitly tagged as **Consolidated** or **Standalone**.

- **Consolidated**: Includes all subsidiaries — typically the more relevant view
- **Standalone**: Parent company only

The app detects the statement type from the Screener export and displays it clearly.
You can switch between types using the sidebar selector when both are available.

Never mix consolidated and standalone data in the same trend analysis.

---

## Sector Engine

The sector engine adapts which metrics are shown based on the company's sector.

Banking companies show NIM, GNPA, CASA ratio — not Debt/Equity or EV/EBITDA.
IT Services show Receivable Days and FCF Yield — not Inventory Days.
Metals show EV/EBITDA and Net Debt/EBITDA — with cycle-awareness notes.

Sector configs are YAML files in `config/sectors/`. All thresholds are labeled as research heuristics, not universal rules.

To override a company's sector: use the **Sector** selectbox in the sidebar and click **Save Sector**. The override is saved to the database and persists across sessions.

---

## Metric Definitions

All calculations are documented in source code with:
- Formula
- Input values used
- Definition
- Known limitations

Key definitions:

| Metric | Formula |
|--------|---------|
| ROE | PAT attributable / Average Shareholders' Equity × 100 |
| ROCE | EBIT / Average Capital Employed × 100 |
| Capital Employed | Equity + Debt − Cash |
| Net Debt | Borrowings − Cash |
| FCF | Operating Cash Flow − Capital Expenditure |
| CFO/PAT | Operating Cash Flow / PAT |
| CAGR | (Final/Initial)^(1/Years) − 1 |
| EV | Market Cap + Debt − Cash |

CAGR is undefined when the initial value is zero or negative. The app returns "Not available" with an explanation rather than silently failing.

---

## Running Tests

```
pytest
```

Or with coverage:

```
pytest --cov=src --cov-report=term-missing
```

Tests cover:
- All calculation formulas (zero, None, negative, edge cases)
- CAGR with insufficient history, zero start, negative start
- ROE/ROCE with negative equity
- Cash flow with negative capex
- Normalizer label mapping
- Database repository (upsert, deduplication)
- Data validation (shareholding sums, pledge logic)
- Trend direction classification
- Sector-specific calculations (banking NIM/GNPA/PCR, NBFC, insurance)
- Valuation analysis (PE/PB history, synthetic multiples)
- Corporate actions (share count, dividends, buybacks)

---

## Data Storage

All data is stored locally:

| Location | Contents |
|----------|---------|
| `data/stock_analyzer.duckdb` | All imported financial data |
| `data/raw/companies/TICKER/` | Original source files (never modified) |
| `data/documents/` | Reserved for document processing |

The database is a single file. Back it up by copying it. Delete it to start fresh.

---

## Privacy

- No data is sent to any cloud service
- No API keys required
- No internet connection required after installation
- Your imported financial data never leaves your computer

---

## Optional Ollama Integration (Future)

The app is designed to support optional local AI assistance via Ollama for:
- Annual report summarization
- Question answering over local documents
- Management commentary comparison

To enable: set `ollama.enabled: true` in `config/app.yaml`.
Ollama must be installed locally. No cloud model calls are made.
Financial calculations are never delegated to the LLM.

The app works completely without Ollama — all analysis is deterministic.

---

## Troubleshooting

**Import fails with "unknown labels"**
The Screener export format may have changed. Check the warnings in the Data Quality page. The unknown labels list will tell you what wasn't recognized. Update `src/ingestion/normalizer.py` to add mappings.

**Database errors on first run**
Delete `data/stock_analyzer.duckdb` and restart. The schema will be recreated.

**Streamlit not found**
Ensure your virtual environment is activated: `.venv\Scripts\activate` (Windows).

**PyMuPDF import error**
PDF extraction is optional. If `fitz` is not installed, PDFs will be imported without text extraction. Install with: `pip install PyMuPDF`.

---

## Phase Status

| Phase | Status | Description |
|-------|--------|-------------|
| 1 | ✅ | Foundation, config, DuckDB schema, models, Streamlit shell |
| 2 | ✅ | Screener Excel parser, normalizer, importer, 310+ tests |
| 3 | ✅ | Calculation library — growth, margins, leverage, efficiency, valuation |
| 4 | ✅ | Trend engine and core dashboard pages |
| 5 | ✅ | Observation engine — factual, rule-based, no verdicts |
| 6 | ✅ | Earnings quality analysis (CFO/PAT, FCF/PAT, Other Income %) |
| 7 | ✅ | Valuation page — synthetic multiples, historical P/E P/B snapshots |
| 8 | ✅ | Sector engine — Banking/NBFC/Insurance aware UI, sector metrics page |
| 9 | ✅ | Peer comparison |
| 10 | ✅ | Quarterly analysis |
| 11 | ✅ | Data quality page |
| 12 | ✅ | Corporate actions — share count, dividends, buybacks, manual register |
| 13 | ✅ | PDF import and search |
| 14 | Planned | Optional local Ollama integration |
| 15 | ✅ | Final polish — sector override, is_valid fixes, README |
