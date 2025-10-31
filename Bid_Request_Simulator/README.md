# Minimalistic Bid Request Simulator

A lightweight OpenRTB-like bid request simulator demonstrating programmatic advertising and real-time bidding concepts.

## 🆕 Multi-Strategy Bidding System with ML

**NEW!** The simulator now supports running **three different bidder strategies simultaneously** with **machine learning-powered click probability prediction**:
- **Conservative** (Port 8081): High quality, narrow targeting, ML-optimized pricing
- **Aggressive** (Port 8082): Maximize volume, broad targeting, ML-optimized pricing
- **Balanced** (Port 8083): Moderate approach, ML-optimized pricing

All bidders use a trained logistic regression model to predict CTR and adjust bid prices automatically!

See [MULTI_BIDDER_README.md](MULTI_BIDDER_README.md) and [ML_README.md](ML_README.md) for details!

## Quick Start

### 1. Install Dependencies
```bash
pip3 install -r requirements.txt
```

### 2. Start the Bidder Server
```bash
python3 bidder_server.py
```

The server starts on `http://localhost:8080`

### 3. Run the Generator (in another terminal)
```bash
python3 bid_request_generator.py
```

## How It Works

### Bidder Server
- Receives OpenRTB-like bid requests via HTTP POST
- Evaluates each request based on configurable rules
- Returns bid responses or 204 No Content

**Current Rules:**
- ✅ Bids on: USA + PHONE or TABLET + iOS
- ❌ No bid on: Any other country, DESKTOP devices, or non-iOS
- Pricing: bidfloor + $0.05 (minimum $1.00)
- Daily Budget: $10.00 (resets daily or via POST /reset)
- Time Window: 9 AM - 5 PM only

### Bid Request Generator
- Generates random OpenRTB-like bid requests
- Sends requests to the bidder server
- Displays results

## Command Options

### Generator Options
```bash
python3 bid_request_generator.py --count 20        # 20 requests
python3 bid_request_generator.py --delay 0.5       # 0.5s delay
python3 bid_request_generator.py --imp-count 2     # 2 impressions/request
python3 bid_request_generator.py --stream          # Continuous mode
python3 bid_request_generator.py --format json     # JSON output
python3 bid_request_generator.py --usa-ios         # USA iOS only (guaranteed bids!)
```

## Understanding Output

**Bid Accepted:**
```
✓ Bid response received ($1.77)
```

**No Bid:**
```
○ No bid (204 No Content)
```

## Customization

Edit `bidder_server.py` to change bidder logic:
```python
TARGET_COUNTRY = "CAN"           # Change target country
TARGET_DEVICES = ["DESKTOP"]     # Change device types
MIN_BID_PRICE = 0.25             # Change minimum bid
```

## API Endpoints

- `POST /bid` - Submit bid request
- `GET /health` - Health check
- `GET /stats` - Bidder configuration and budget status
- `GET /analytics` - Historical analytics from database (JSON)
- `GET /dashboard` - Web analytics dashboard (HTML)
- `POST /reset` - Manually reset budget (use when budget exhausted)

## Example Requests

### Submit Bid Request
```bash
curl -X POST http://localhost:8080/bid \
  -H "Content-Type: application/json" \
  -d '{
    "id":"test-1",
    "imp":[{
      "id":"imp-1",
      "bidfloor":1.0,
      "device":{
        "devicetype":"PHONE",
        "os":"iOS",
        "geo":{"country":"USA"}
      }
    }]
  }'
```

### Reset Budget
```bash
curl -X POST http://localhost:8080/reset
```

### Check Stats
```bash
curl http://localhost:8080/stats
```

### View Analytics (JSON)
```bash
curl http://localhost:8080/analytics
```

### View Dashboard (Web UI)
Open your browser to: **http://localhost:8080/dashboard**

The dashboard provides:
- 📊 Key metrics (requests, bids, bid rate, spend, **ML predicted CTR**)
- 🤖 **ML Performance section** (min/max/avg CTR)
- 📈 Interactive charts
- 🔄 Auto-refresh every 5 seconds
- 📱 Responsive design

## Database

The bidder automatically logs all requests and responses to `bidder.db` (SQLite).

**Tables:**
- `bid_requests` - All incoming bid requests
- `bid_responses` - All bid responses (accepted/rejected) **with ML predictions**

**Query examples:**
```bash
# View requests
sqlite3 bidder.db "SELECT * FROM bid_requests WHERE country='USA';"

# View ML predictions
sqlite3 bidder.db "SELECT bid_price, predicted_ctr FROM bid_responses WHERE response_status='ACCEPTED';"
```

## Learning Concepts

This simulator demonstrates:
- OpenRTB protocol structure
- Real-time bidding (RTB) mechanics
- HTTP-based communication
- JSON data exchange
- Decision logic implementation
- Flask web development
- SQLite database logging
- Analytics and reporting
- Multi-strategy bidding systems
- A/B testing for bidding algorithms
- Machine learning for prediction and optimization
- ML model training and inference
- Feature engineering for ML

## Requirements

- Python 3.7+
- Flask 3.0.0
- Requests 2.31.0
- python-dateutil 2.8.2
- NumPy 1.24.3

