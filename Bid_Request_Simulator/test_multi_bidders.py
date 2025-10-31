#!/usr/bin/env python3
"""
Test Multiple Bidder Strategies
Sends the same requests to all bidder servers and compares responses.
"""

import json
import random
import argparse
import requests
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# Import from bid_request_generator
COUNTRIES = ["USA", "CAN", "GBR", "FRA", "GER", "JPN", "CHN", "BRA", "IND", "AUS"]
DEVICE_TYPES = ["PHONE", "TABLET", "DESKTOP"]
OS_TYPES = ["iOS", "Android", "Windows", "macOS"]
BROWSERS = ["Chrome", "Safari", "Firefox", "Edge"]
CATEGORIES = ["IAB1", "IAB2", "IAB3", "IAB4", "IAB5"]


def generate_bid_request():
    """Generate a random OpenRTB-like bid request."""
    country = random.choice(COUNTRIES)
    device_type = random.choice(DEVICE_TYPES)
    os_type = random.choice(OS_TYPES)
    browser = random.choice(BROWSERS)
    
    impression = {
        "id": f"imp-{datetime.now().timestamp()}",
        "bidfloor": round(random.uniform(0.10, 2.00), 2),
        "banner": {
            "w": random.choice([320, 728, 970]),
            "h": random.choice([50, 90, 250]),
            "pos": random.randint(0, 7)
        },
        "device": {
            "devicetype": device_type,
            "os": os_type,
            "geo": {
                "country": country
            }
        },
        "bcat": [random.choice(CATEGORIES)],
        "badv": ["example-badvertiser.com"]
    }
    
    bid_request = {
        "id": f"req-{datetime.now().timestamp()}",
        "at": 2,
        "tmax": 200,
        "imp": [impression],
        "site": {
            "domain": "test-publisher.com",
            "page": "https://test-publisher.com/page",
            "ref": "https://test-publisher.com/ref"
        },
        "device": {
            "devicetype": device_type,
            "ua": f"Mozilla/5.0 (compatible; {browser})",
            "os": os_type,
            "geo": {
                "country": country
            }
        },
        "user": {
            "id": f"user-{random.randint(1000000, 9999999)}"
        }
    }
    
    return bid_request


def send_to_bidder(url, bid_request, timeout=5):
    """Send a bid request to a bidder server."""
    try:
        response = requests.post(url, json=bid_request, timeout=timeout)
        if response.status_code == 200:
            data = response.json()
            return {
                'status': 200,
                'bid': True,
                'price': data['seatbid'][0]['bid'][0]['price'],
                'bidder': data.get('seatbid', [{}])[0].get('seat', 'unknown')
            }
        elif response.status_code == 204:
            return {'status': 204, 'bid': False}
        else:
            return {'status': response.status_code, 'bid': False, 'error': response.text}
    except Exception as e:
        return {'status': None, 'bid': False, 'error': str(e)}


def test_all_bidders(count=10):
    """Test all bidders with the same requests."""
    bidders = {
        'Conservative': 'http://localhost:8081/bid',
        'Aggressive': 'http://localhost:8082/bid',
        'Balanced': 'http://localhost:8083/bid'
    }
    
    print("=" * 100)
    print("Multi-Bidder Strategy Comparison")
    print("=" * 100)
    print(f"Testing with {count} random bid requests\n")
    
    results = {name: {'bids': 0, 'no_bids': 0, 'total_price': 0} for name in bidders.keys()}
    
    for i in range(count):
        bid_request = generate_bid_request()
        
        print(f"\n{'='*100}")
        print(f"Request #{i+1}: {bid_request['id']}")
        print(f"Country: {bid_request['device']['geo']['country']}")
        print(f"Device: {bid_request['device']['devicetype']} | OS: {bid_request['device']['os']}")
        print(f"Bidfloor: ${bid_request['imp'][0]['bidfloor']:.2f}")
        print("-" * 100)
        
        # Send to all bidders in parallel
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {
                executor.submit(send_to_bidder, url, bid_request): name 
                for name, url in bidders.items()
            }
            
            responses = {}
            for future in as_completed(futures):
                name = futures[future]
                responses[name] = future.result()
            
            # Display results
            for name in ['Conservative', 'Aggressive', 'Balanced']:
                resp = responses[name]
                if resp['bid']:
                    price = resp['price']
                    results[name]['bids'] += 1
                    results[name]['total_price'] += price
                    print(f"  ✓ {name:12} → BID ${price:.2f}")
                else:
                    results[name]['no_bids'] += 1
                    reason = ""
                    if resp['status'] == 204:
                        reason = " (filtered)"
                    elif resp.get('error'):
                        reason = f" (error: {resp['error'][:30]})"
                    print(f"  ✗ {name:12} → NO BID{reason}")
        
        time.sleep(0.5)
    
    # Summary
    print("\n" + "=" * 100)
    print("SUMMARY")
    print("=" * 100)
    print(f"{'Strategy':<15} {'Bids':<8} {'No Bids':<10} {'Bid Rate':<12} {'Total Spent':<15} {'Avg Price':<15}")
    print("-" * 100)
    
    for name, data in results.items():
        total = data['bids'] + data['no_bids']
        bid_rate = (data['bids'] / total * 100) if total > 0 else 0
        avg_price = (data['total_price'] / data['bids']) if data['bids'] > 0 else 0
        
        print(f"{name:<15} {data['bids']:<8} {data['no_bids']:<10} {bid_rate:>10.1f}% {data['total_price']:>12.2f} {avg_price:>12.2f}")
    
    print("=" * 100)
    
    # Get stats from each bidder
    print("\nBidder Status:")
    print("-" * 100)
    for name, base_url in bidders.items():
        try:
            stats_url = base_url.replace('/bid', '/stats')
            response = requests.get(stats_url, timeout=2)
            if response.status_code == 200:
                stats = response.json()
                print(f"{name:12} - Budget: ${stats['remaining_budget']:.2f} remaining")
        except:
            print(f"{name:12} - Status: unavailable")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Test multiple bidder strategies')
    parser.add_argument('--count', type=int, default=20, help='Number of requests to test')
    args = parser.parse_args()
    
    test_all_bidders(args.count)

