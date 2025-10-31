#!/usr/bin/env python3
"""
Generate targeted test requests for comparing bidder strategies
"""

import json
import argparse
import requests
import time
from datetime import datetime

BIDDERS = {
    'Conservative': 'http://localhost:8081',
    'Aggressive': 'http://localhost:8082',
    'Balanced': 'http://localhost:8083'
}


def send_targeted_request(target_type, count=5):
    """Send targeted requests based on bidder requirements."""
    
    if target_type == 'conservative':
        # USA, PHONE, iOS, high bidfloor, 10-17 window
        country = "USA"
        device_type = "PHONE"
        os_type = "iOS"
        bidfloor = 2.10  # Above $2 minimum
    elif target_type == 'aggressive':
        # USA, PHONE, Android, low bidfloor
        country = "USA"
        device_type = "PHONE"
        os_type = "Android"
        bidfloor = 0.55  # Just above $0.50 minimum
    elif target_type == 'balanced':
        # USA, TABLET, iOS
        country = "USA"
        device_type = "TABLET"
        os_type = "iOS"
        bidfloor = 1.10  # Just above $1 minimum
    else:
        print("Invalid target type")
        return
    
    print(f"\n🎯 Generating {count} requests for {target_type} bidder")
    print(f"   Requirements: {country}, {device_type}, {os_type}, ${bidfloor:.2f} floor")
    print("-" * 80)
    
    for i in range(count):
        bid_request = {
            "id": f"req-{datetime.now().timestamp()}",
            "at": 2,
            "tmax": 200,
            "imp": [{
                "id": f"imp-{datetime.now().timestamp()}",
                "bidfloor": bidfloor,
                "banner": {"w": 320, "h": 50, "pos": 1},
                "device": {
                    "devicetype": device_type,
                    "os": os_type,
                    "geo": {"country": country}
                }
            }],
            "site": {"domain": "test-publisher.com"},
            "device": {
                "devicetype": device_type,
                "os": os_type,
                "geo": {"country": country}
            }
        }
        
        # Send to all bidders
        print(f"\nRequest #{i+1}: {bid_request['id']}")
        for name, base_url in BIDDERS.items():
            try:
                resp = requests.post(f"{base_url}/bid", json=bid_request, timeout=2)
                if resp.status_code == 200:
                    data = resp.json()
                    price = data['seatbid'][0]['bid'][0]['price']
                    print(f"  ✓ {name:12} → BID ${price:.2f}")
                else:
                    print(f"  ✗ {name:12} → NO BID")
            except Exception as e:
                print(f"  ✗ {name:12} → ERROR: {e}")
        
        time.sleep(0.3)
    
    # Show stats
    print("\n" + "=" * 80)
    print("Current Stats:")
    print("=" * 80)
    for name, base_url in BIDDERS.items():
        try:
            resp = requests.get(f"{base_url}/stats", timeout=2)
            if resp.status_code == 200:
                stats = resp.json()
                print(f"{name:12} - Bids: {stats['bid_count']}, Spent: ${stats['total_spent']:.2f}, Remaining: ${stats['remaining_budget']:.2f}")
        except:
            pass


def send_all_types():
    """Send one request to each type."""
    print("=" * 80)
    print("Testing All Bidder Types with Targeted Requests")
    print("=" * 80)
    
    for bidder_type in ['conservative', 'aggressive', 'balanced']:
        send_targeted_request(bidder_type, count=3)
        print("\n")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Test bidder with targeted requests')
    parser.add_argument('--type', choices=['conservative', 'aggressive', 'balanced', 'all'], 
                       default='all', help='Which bidder type to test')
    parser.add_argument('--count', type=int, default=3, help='Number of requests per type')
    args = parser.parse_args()
    
    if args.type == 'all':
        send_all_types()
    else:
        send_targeted_request(args.type, args.count)

