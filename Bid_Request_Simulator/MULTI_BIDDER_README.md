# Multi-Strategy Bidder System

This implementation extends the basic bidder simulator to support **three different bidding strategies** running simultaneously, all powered by **machine learning-based click probability prediction**.

## 🎯 Bidder Strategies

### 1. Conservative Bidder (Port 8081)
**Philosophy**: High quality, narrow targeting
- **Targets**: USA, PHONE, iOS
- **Min Bid**: $2.00 CPM
- **Window**: 9am - 5pm
- **Budget**: $15/day
- **Bidding**: bidfloor + $0.20 premium

**Use Case**: Maximizing quality, ROI, and user engagement

### 2. Aggressive Bidder (Port 8082)
**Philosophy**: Maximize volume, lower barriers
- **Targets**: USA, ALL devices (PHONE/TABLET/DESKTOP), iOS + Android
- **Min Bid**: $0.50 CPM
- **Window**: 8am - 10pm (14 hours)
- **Budget**: $25/day
- **Bidding**: bidfloor + $0.01 premium

**Use Case**: Maximizing impressions and market share

### 3. Balanced Bidder (Port 8083)
**Philosophy**: Moderate targeting and pricing
- **Targets**: USA, PHONE + TABLET, iOS
- **Min Bid**: $1.00 CPM
- **Window**: 9am - 5pm
- **Budget**: $20/day
- **Bidding**: bidfloor + $0.05 premium

**Use Case**: Balanced approach between volume and quality

## 🚀 Quick Start

### Start All Bidders
```bash
./run_all_bidders.sh
```

### Stop All Bidders
```bash
pkill -f bidder_multi.py
```

### Check Individual Bidder Status
```bash
curl http://localhost:8081/stats  # Conservative
curl http://localhost:8082/stats  # Aggressive
curl http://localhost:8083/stats  # Balanced
```

## 🧪 Testing

### Test All Bidders with Random Requests
```bash
python3 test_multi_bidders.py --count 20
```

### Test with Targeted Requests
```bash
python3 test_targeted.py
```

### Test Specific Bidder Type
```bash
python3 test_targeted.py --type conservative --count 5
python3 test_targeted.py --type aggressive --count 5
python3 test_targeted.py --type balanced --count 5
```

### Test ML Click Probability Prediction
```bash
python3 ml_predictor.py  # Train and test model
python3 demo_ml_pricing.py  # See ML pricing in action
```

## 📊 Understanding Results

The test output shows:
- **Which bidders bid** on each request
- **Bid prices** for each bidder
- **Summary statistics** (bid rate, spend, avg price)
- **Remaining budget** for each bidder

### Expected Behavior

1. **Conservative**: Only bids on USA + PHONE + iOS with bidfloor ≥ $2.00
   - Highest bid prices
   - Lowest bid rate (most selective)

2. **Aggressive**: Bids on USA with any device/OS and bidfloor ≥ $0.50
   - Lowest bid prices
   - Highest bid rate (least selective)

3. **Balanced**: Bids on USA + PHONE/TABLET + iOS with bidfloor ≥ $1.00
   - Medium bid prices
   - Medium bid rate

## 🏗️ Architecture

```
test_targeted.py / test_multi_bidders.py
         ↓
    [Bid Requests]
         ↓
    ┌──────────────────────────────────────────────┐
    │         ML Click Probability Model           │
    │         Predicts: CTR, adjusts pricing       │
    └──────────────────────────────────────────────┘
         ↓
    ┌──────────────────────────────────┐
    │   Conservative (8081)            │
    │   - High quality filter          │
    │   - Premium pricing + ML         │
    └──────────────────────────────────┘
    
    ┌──────────────────────────────────┐
    │   Aggressive (8082)              │
    │   - Broad targeting              │
    │   - Volume pricing + ML          │
    └──────────────────────────────────┘
    
    ┌──────────────────────────────────┐
    │   Balanced (8083)                │
    │   - Moderate filter              │
    │   - Balanced pricing + ML        │
    └──────────────────────────────────┘
         ↓
    [Bid Responses with predicted_ctr]
         ↓
    Comparison Results
```

## 🤖 Machine Learning Integration

All bidders use **ML-based click probability prediction** to optimize pricing:

- **Trained Model**: Logistic regression on 10,000 synthetic impressions
- **Features**: Device, OS, Country, Time, Bidfloor
- **Output**: Predicted CTR (0-1)
- **Pricing**: Bid price adjusted by CTR (up to 2x multiplier)

See [ML_README.md](ML_README.md) for complete ML documentation.

## 📈 Real-World Application

This multi-bidder setup simulates:

1. **A/B Testing**: Compare different bidding strategies simultaneously
2. **Market Segmentation**: Target different audience segments with different strategies
3. **Risk Management**: Diversify bidding approaches to reduce risk
4. **Budget Allocation**: Allocate budget across strategies based on performance
5. **Learning Systems**: Use data from multiple strategies to optimize bidding

## 🔧 Customization

Edit `bidder_multi.py` to modify strategies:

```python
STRATEGIES = {
    'conservative': {
        'target_country': 'USA',
        'target_devices': ['PHONE'],
        'target_os': ['iOS'],
        'min_bid_price': 2.00,
        'bid_window_start': 9,
        'bid_window_end': 17,
        'daily_budget': 15.00,
    },
    # ... add more strategies
}
```

## 📝 Files

### Core Files
- `bidder_multi.py` - Multi-strategy bidder server with ML
- `run_all_bidders.sh` - Launcher script
- `test_multi_bidders.py` - Random request tester
- `test_targeted.py` - Targeted request tester
- `*_bidder.db` - SQLite databases (one per bidder)

### ML Files
- `ml_predictor.py` - ML click probability predictor
- `ctr_model.pkl` - Trained ML model (auto-generated)
- `demo_ml_pricing.py` - ML pricing demonstration
- `ML_README.md` - ML documentation

## 🎓 Learning Concepts

- **Strategy Pattern**: Different algorithms (bidding logic) in same interface
- **Multi-tenancy**: Running multiple instances with different configs
- **Load Balancing**: Distributing requests across services
- **Performance Testing**: Comparing strategies objectively
- **Concurrent Processing**: Testing multiple bidders simultaneously
- **Machine Learning**: Predicting click probability for optimization
- **ML Integration**: Real-time model inference in production systems

