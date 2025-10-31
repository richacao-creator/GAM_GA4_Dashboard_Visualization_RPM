#!/usr/bin/env python3
"""
Bid Request Generator
Generates sample OpenRTB-like bid requests for testing the bidder.
"""

import json
import random
import argparse
import requests
import time
from datetime import datetime


# Sample data pools
COUNTRIES = ["USA", "CAN", "GBR", "FRA", "GER", "JPN", "CHN", "BRA", "IND", "AUS"]
DEVICE_TYPES = ["PHONE", "TABLET", "DESKTOP"]
OS_TYPES = ["iOS", "Android", "Windows", "macOS"]
BROWSERS = ["Chrome", "Safari", "Firefox", "Edge"]
CATEGORIES = ["IAB1", "IAB2", "IAB3", "IAB4", "IAB5"]


def generate_bid_request(imp_count=1, usa_ios_only=False):
    """
    Generate a single OpenRTB-like bid request.
    
    Args:
        imp_count: Number of impressions to include in the request
        usa_ios_only: If True, generate only USA iOS requests
    
    Returns:
        dict: Bid request JSON
    """
    if usa_ios_only:
        country = "USA"
        device_type = random.choice(["PHONE", "TABLET"])  # Only PHONE or TABLET
        os_type = "iOS"
        browser = random.choice(BROWSERS)
    else:
        country = random.choice(COUNTRIES)
        device_type = random.choice(DEVICE_TYPES)
        os_type = random.choice(OS_TYPES)
        browser = random.choice(BROWSERS)
    
    # Generate impressions
    impressions = []
    for i in range(imp_count):
        impression = {
            "id": f"imp-{datetime.now().timestamp()}-{i}",
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
        impressions.append(impression)
    
    bid_request = {
        "id": f"req-{datetime.now().timestamp()}",
        "at": 2,  # First price auction
        "tmax": 200,
        "imp": impressions,
        "site": {
            "domain": "test-publisher.com",
            "page": "https://test-publisher.com/page",
            "ref": "https://test-publisher.com/ref"
        },
        "device": {
            "devicetype": device_type,
            "ua": f"Mozilla/5.0 (compatible; {browser})",
            "ip": f"{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}",
            "geo": {
                "country": country
            }
        },
        "user": {
            "id": f"user-{random.randint(1000, 9999)}"
        }
    }
    
    return bid_request


def send_bid_request(url, bid_request):
    """
    Send a bid request to the bidder server.
    
    Args:
        url: Bidder server URL
        bid_request: Bid request JSON
    
    Returns:
        tuple: (status_code, response_json or None)
    """
    try:
        response = requests.post(
            url,
            json=bid_request,
            headers={'Content-Type': 'application/json'},
            timeout=5
        )
        response_json = response.json() if response.text else None
        return response.status_code, response_json
    except requests.exceptions.RequestException as e:
        print(f"Error sending request: {e}")
        return None, None


def main():
    parser = argparse.ArgumentParser(description='Generate and send bid requests to the bidder server')
    parser.add_argument('--url', default='http://localhost:8080/bid', help='Bidder server URL')
    parser.add_argument('--count', type=int, default=10, help='Number of bid requests to generate')
    parser.add_argument('--delay', type=float, default=1.0, help='Delay between requests (seconds)')
    parser.add_argument('--imp-count', type=int, default=1, help='Number of impressions per request')
    parser.add_argument('--stream', action='store_true', help='Stream mode: generate requests indefinitely')
    parser.add_argument('--format', choices=['json', 'pretty'], default='pretty', help='Output format')
    parser.add_argument('--usa-ios', action='store_true', help='Generate only USA iOS requests (guaranteed bids)')
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("Bid Request Generator")
    print(f"Target URL: {args.url}")
    print(f"Requests: {args.count if not args.stream else 'infinite (stream mode)'}")
    print(f"Impressions per request: {args.imp_count}")
    if args.usa_ios:
        print("Mode: USA iOS only (guaranteed bids!)")
    print("=" * 80)
    
    request_count = 0
    
    try:
        while args.stream or request_count < args.count:
            # Generate bid request
            bid_request = generate_bid_request(imp_count=args.imp_count, usa_ios_only=args.usa_ios)
            
            # Print request details
            if args.format == 'pretty':
                print(f"\n[Request #{request_count + 1}]")
                print(f"Request ID: {bid_request['id']}")
                print(f"Country: {bid_request['device']['geo']['country']}")
                print(f"Device Type: {bid_request['device']['devicetype']}")
                for imp in bid_request['imp']:
                    print(f"  - Impression {imp['id']}: ${imp['bidfloor']} bidfloor")
            else:
                print(json.dumps(bid_request))
            
            # Send to bidder
            status_code, response = send_bid_request(args.url, bid_request)
            
            # Print response
            if status_code is not None:
                if status_code == 200:
                    if args.format == 'pretty':
                        print(f"✓ Bid response received (${response['seatbid'][0]['bid'][0]['price']})")
                    else:
                        print(json.dumps(response))
                elif status_code == 204:
                    if args.format == 'pretty':
                        print("○ No bid (204 No Content)")
                    else:
                        print('{"status": 204, "message": "No bid"}')
                else:
                    print(f"✗ Error: Status {status_code}")
                    if response:
                        print(json.dumps(response))
            else:
                print("✗ Failed to send request")
            
            request_count += 1
            
            if not args.stream:
                time.sleep(args.delay)
            else:
                time.sleep(args.delay)
                
    except KeyboardInterrupt:
        print("\n\nStopped by user")
    finally:
        print("\n" + "=" * 80)
        print(f"Total requests sent: {request_count}")
        print("=" * 80)


if __name__ == '__main__':
    main()
