#!/usr/bin/env python3
"""
Demonstrate ML-based pricing before/after comparison
"""

import requests
import json

def test_ml_pricing():
    """Compare base pricing vs ML-adjusted pricing."""
    
    impressions = [
        {
            "name": "USA iOS Phone (High CTR)",
            "imp": {
                "id": "imp-1",
                "bidfloor": 2.0,
                "device": {"devicetype": "PHONE", "os": "iOS", "geo": {"country": "USA"}}
            },
            "base_expected": 2.20  # bidfloor + 0.20
        },
        {
            "name": "USA Android Tablet (Medium CTR)",
            "imp": {
                "id": "imp-2",
                "bidfloor": 1.0,
                "device": {"devicetype": "TABLET", "os": "Android", "geo": {"country": "USA"}}
            },
            "base_expected": 1.05  # bidfloor + 0.05
        },
        {
            "name": "GER iOS Desktop (Low CTR)",
            "imp": {
                "id": "imp-3",
                "bidfloor": 0.8,
                "device": {"devicetype": "DESKTOP", "os": "iOS", "geo": {"country": "GER"}}
            },
            "base_expected": 1.01  # bidfloor + 0.01
        }
    ]
    
    print("=" * 100)
    print("ML-BASED PRICING COMPARISON")
    print("=" * 100)
    print()
    
    for test in impressions:
        print(f"Test: {test['name']}")
        print("-" * 100)
        
        # Get ML prediction
        try:
            resp = requests.post(
                "http://localhost:8081/predict",
                json={"imp": [test['imp']]},
                timeout=2
            )
            if resp.status_code == 200:
                prediction = resp.json()['predictions'][0]
                predicted_ctr = prediction['predicted_ctr']
                suggested_bid = prediction['suggested_bid']
                
                print(f"  Base Expected Bid:    ${test['base_expected']:.2f}")
                print(f"  ML Predicted CTR:     {predicted_ctr*100:.2f}%")
                print(f"  ML Suggested Bid:     ${suggested_bid:.2f}")
                
                difference = suggested_bid - test['base_expected']
                if difference > 0:
                    print(f"  ML Adjustment:        +${difference:.2f} ({difference/test['base_expected']*100:.1f}% increase)")
                else:
                    print(f"  ML Adjustment:        ${difference:.2f} ({abs(difference)/test['base_expected']*100:.1f}% decrease)")
            else:
                print(f"  Error getting prediction")
        except Exception as e:
            print(f"  Error: {e}")
        
        print()
    
    print("=" * 100)
    print("KEY TAKEAWAYS")
    print("=" * 100)
    print("• ML predicts click probability based on device, OS, country, time")
    print("• Higher predicted CTR = higher bid price (up to 2x multiplier)")
    print("• Bidders optimize spend toward higher-value impressions")
    print("• All three bidder strategies use same ML model")
    print("=" * 100)


if __name__ == '__main__':
    test_ml_pricing()

