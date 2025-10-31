# Machine Learning Click Probability Prediction

The bidder system now includes machine learning-based click-through rate (CTR) prediction to optimize bidding prices.

## 🎯 Overview

Each bidder uses a trained logistic regression model to predict the probability that a user will click on an ad, then adjusts bid prices accordingly:
- **Higher predicted CTR** → **Higher bid price** (up to 2x multiplier)
- **Lower predicted CTR** → **Lower bid price**

This helps maximize return on ad spend by directing budget toward higher-value impressions.

## 🧠 Model Architecture

### Training Data
- **Samples**: 10,000 synthetic impressions
- **Features**: Device type, OS, Country, Hour of day, Bidfloor
- **Target**: Binary click outcome

### Features Used
1. `device_type_phone` - Binary flag for phone
2. `device_type_tablet` - Binary flag for tablet  
3. `device_type_desktop` - Binary flag for desktop
4. `os_ios` - Binary flag for iOS
5. `os_android` - Binary flag for Android
6. `country_usa` - Binary flag for USA
7. `hour_of_day` - Normalized hour (0-1)
8. `bidfloor` - Normalized bidfloor (0-1)

### Model Type
**Logistic Regression** trained via gradient descent
- Sigmoid activation function
- 1000 training iterations
- Learning rate: 0.01
- Weights initialized randomly

### Industry CTR Baselines
The model is trained on realistic industry averages:
- **Base CTR**: 1.5%
- **Device multipliers**: Phone (1.2x) > Tablet (1.1x) > Desktop (0.8x)
- **OS multipliers**: iOS (1.1x) > Android (0.9x)
- **Country multipliers**: USA (1.2x) > Others (0.8x)
- **Time multipliers**: Peak hours 10-14 (1.3x), Business hours (1.1x), Off-peak (0.7x)

## 💰 Price Adjustment Formula

```
base_bid = bidfloor + strategy_premium
ctr_multiplier = 1.0 + (predicted_ctr / 0.05)
ctr_multiplier = min(ctr_multiplier, 2.0)  # Cap at 2x
final_bid = base_bid * ctr_multiplier
```

**Examples:**
- 2% CTR → 1.4x multiplier
- 5% CTR → 2.0x multiplier (capped)
- 0.5% CTR → 1.1x multiplier

## 📊 Usage

### Train Model
```bash
python3 ml_predictor.py
```

Model is automatically trained on first run and saved to `ctr_model.pkl`.

### Get Predictions
```bash
curl -X POST http://localhost:8081/predict \
  -H "Content-Type: application/json" \
  -d '{
    "imp": [{
      "id": "imp-1",
      "bidfloor": 2.0,
      "device": {
        "devicetype": "PHONE",
        "os": "iOS",
        "geo": {"country": "USA"}
      }
    }]
  }'
```

**Response:**
```json
{
  "predictions": [{
    "impid": "imp-1",
    "predicted_ctr": 0.0384,
    "ctr_percent": 3.84,
    "suggested_bid": 3.54,
    "confidence": "medium"
  }]
}
```

### Automatic Integration

All bidders automatically use ML predictions when generating bids. The predicted CTR is included in the bid response:

```json
{
  "seatbid": [{
    "bid": [{
      "price": 3.89,
      "ext": {
        "predicted_ctr": 0.0384
      }
    }]
  }]
}
```

### Demo Script
```bash
python3 demo_ml_pricing.py
```

Shows before/after comparison of base pricing vs ML-adjusted pricing.

## 🔬 Testing

### Test Different Scenarios

```bash
# High CTR (USA iOS Phone)
curl -X POST http://localhost:8081/predict ...

# Medium CTR (USA Android Tablet)  
curl -X POST http://localhost:8081/predict ...

# Low CTR (Foreign Desktop)
curl -X POST http://localhost:8081/predict ...
```

### Compare Strategies

Run the multi-bidder comparison to see how ML affects pricing across strategies:

```bash
python3 test_targeted.py --type all
```

## 📈 Expected Results

### CTR Predictions by Type
- **USA iOS Phone**: ~3-5% CTR
- **USA Android Phone**: ~2.5-4% CTR
- **USA iOS Tablet**: ~3-4.5% CTR
- **USA Android Tablet**: ~2.5-3.5% CTR
- **Foreign iOS**: ~1-2% CTR
- **Desktop**: Variable (0.5-2%)

### Price Adjustments
- Premium impressions (high CTR) typically see 20-100% price increase
- Lower-value impressions see minimal or no increase
- All adjustments capped at 2x base bid

## 🔧 Model Customization

### Modify Training Data
Edit `ml_predictor.py`:

```python
def _generate_synthetic_training_data(self):
    # Adjust base CTR
    base_ctr = 0.015  # Change from 1.5%
    
    # Adjust device multipliers
    device_multiplier = [1.5, 1.2, 0.6]  # Boost phone, reduce desktop
    
    # Add new features
    ...
```

### Retrain Model
```bash
rm ctr_model.pkl
python3 ml_predictor.py
```

### Use Different Algorithms
Replace `_train_logistic_regression()` with:
- Random Forest
- Gradient Boosting (XGBoost)
- Neural Network
- Deep Learning models

## 🎓 Learning Concepts

This ML implementation demonstrates:

1. **Feature Engineering**: Extracting relevant signals from raw data
2. **Model Training**: Logistic regression for binary classification
3. **Model Serialization**: Saving/loading trained models
4. **Online Prediction**: Real-time CTR estimation
5. **Business Integration**: Using predictions to drive decisions
6. **A/B Testing**: Comparing strategies with/without ML

## 🔮 Future Enhancements

Potential improvements:
- **Online Learning**: Update model with real click data
- **User Features**: Add demographic, behavioral data
- **Contextual Features**: Page content, time since last visit
- **Deep Models**: Neural networks for complex patterns
- **Multi-Objective**: Optimize for conversions, not just clicks
- **Ensemble Methods**: Combine multiple models
- **Explainability**: Show which features drive predictions

## 📁 Files

- `ml_predictor.py` - ML model and predictor
- `ctr_model.pkl` - Trained model (auto-generated)
- `demo_ml_pricing.py` - Demo script
- `bidder_multi.py` - Integrated bidder with ML

## 📊 Real-World Application

In production ad systems:
- **Training**: Models train on millions of historical impressions
- **Evaluation**: A/B tests measure ROI improvement
- **Refresh**: Retrained daily/weekly with new data
- **Monitoring**: Track prediction accuracy and business metrics
- **Scaling**: Distributed inference for sub-10ms latency

## 🚀 Impact

ML-powered bidding typically:
- Improves ROI by 10-30%
- Reduces wasted spend on low-value impressions
- Increases win rate on premium inventory
- Enables real-time optimization

