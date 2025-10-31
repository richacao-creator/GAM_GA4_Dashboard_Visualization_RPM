#!/usr/bin/env python3
"""
Multi-Strategy Bidder Server
Supports running different bidder strategies on different ports.
"""

from flask import Flask, request, jsonify, render_template_string
import json
from datetime import datetime
import logging
import sqlite3
import sys
import argparse
from ml_predictor import get_predictor

# Parse command line arguments
parser = argparse.ArgumentParser(description='Bidder server with configurable strategy')
parser.add_argument('--strategy', required=True, choices=['conservative', 'aggressive', 'balanced'], 
                    help='Bidder strategy')
parser.add_argument('--port', type=int, required=True, help='Port to run on')
args = parser.parse_args()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format=f'%(asctime)s - {args.strategy} - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Strategy configurations
STRATEGIES = {
    'conservative': {
        'bidder_id': 'conservative-bidder',
        'target_country': 'USA',
        'target_devices': ['PHONE'],  # Only phones
        'target_os': ['iOS'],
        'min_bid_price': 2.00,  # Higher minimum
        'bid_window_start': 9,
        'bid_window_end': 17,  # Business hours
        'daily_budget': 15.00,
        'description': 'Conservative: High quality, narrow targeting'
    },
    'aggressive': {
        'bidder_id': 'aggressive-bidder',
        'target_country': 'USA',
        'target_devices': ['PHONE', 'TABLET', 'DESKTOP'],  # All devices
        'target_os': ['iOS', 'Android'],  # Both OSes
        'min_bid_price': 0.50,  # Lower minimum
        'bid_window_start': 8,
        'bid_window_end': 22,  # Longer window
        'daily_budget': 25.00,
        'description': 'Aggressive: Maximize volume, lower barriers'
    },
    'balanced': {
        'bidder_id': 'balanced-bidder',
        'target_country': 'USA',
        'target_devices': ['PHONE', 'TABLET'],
        'target_os': ['iOS'],
        'min_bid_price': 1.00,
        'bid_window_start': 9,
        'bid_window_end': 17,
        'daily_budget': 20.00,
        'description': 'Balanced: Moderate targeting and pricing'
    }
}

# Get strategy config
config = STRATEGIES[args.strategy]

# Budget tracking
total_spent = 0.00
bid_count = 0
last_reset_day = datetime.now().day

# Database configuration
DATABASE = f'{args.strategy}_bidder.db'


def init_database():
    """Initialize the SQLite database for logging."""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bid_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            request_id TEXT NOT NULL,
            country TEXT,
            device_type TEXT,
            os TEXT,
            bidfloor REAL,
            received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bid_responses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            request_id TEXT NOT NULL,
            bid_price REAL,
            response_status TEXT,
            responded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()


def reset_budget_if_new_day():
    """Reset budget if it's a new day."""
    global total_spent, bid_count, last_reset_day
    current_day = datetime.now().day
    if current_day != last_reset_day:
        total_spent = 0.00
        bid_count = 0
        last_reset_day = current_day


def should_bid(imp):
    """Determine if we should bid on this impression."""
    reset_budget_if_new_day()
    
    global total_spent
    if total_spent >= config['daily_budget']:
        return False
    
    if not imp.get('bidfloor'):
        return False
    
    current_hour = datetime.now().hour
    if not (config['bid_window_start'] <= current_hour < config['bid_window_end']):
        return False
    
    device_type = imp.get('device', {}).get('devicetype', '').upper()
    if device_type not in config['target_devices']:
        return False
    
    device_os = imp.get('device', {}).get('os', '')
    if device_os not in config['target_os']:
        return False
    
    country = imp.get('device', {}).get('geo', {}).get('country', '')
    if country != config['target_country']:
        return False
    
    return True


def generate_bid_response(imp, request_id):
    """Generate a bid response for the impression."""
    # Get ML click probability prediction
    try:
        predictor = get_predictor()
        click_probability = predictor.predict(imp)
        logger.debug(f"ML click probability: {click_probability:.1%}")
    except Exception as e:
        logger.error(f"ML prediction failed: {e}")
        click_probability = 0.015  # Default 1.5% CTR
    
    # Strategy-specific base pricing
    if args.strategy == 'conservative':
        # Conservative: higher base bid
        base_price = max(imp.get('bidfloor', config['min_bid_price']), config['min_bid_price']) + 0.20
    elif args.strategy == 'aggressive':
        # Aggressive: minimum base bid
        base_price = max(imp.get('bidfloor', config['min_bid_price']), config['min_bid_price']) + 0.01
    else:  # balanced
        # Balanced: moderate base
        base_price = max(imp.get('bidfloor', config['min_bid_price']), config['min_bid_price']) + 0.05
    
    # Apply ML-based price adjustment
    # Higher predicted CTR = higher bid price (up to 2x)
    ctr_multiplier = 1.0 + (click_probability / 0.05)  # Scale up to 2x for 5% CTR
    ctr_multiplier = min(ctr_multiplier, 2.0)  # Cap at 2x
    bid_price = base_price * ctr_multiplier
    
    response = {
        "id": request_id,
        "bidid": f"{config['bidder_id']}-{datetime.now().timestamp()}",
        "cur": "USD",
        "seatbid": [{
            "seat": config['bidder_id'],
            "bid": [{
                "id": f"{config['bidder_id']}-bid-{datetime.now().timestamp()}",
                "impid": imp.get('id'),
                "price": round(bid_price, 2),
                "adm": f"<div style='width:320px;height:50px;background:#4CAF50;color:white;text-align:center;line-height:50px;'>Ad from {config['bidder_id']}</div>",
                "adomain": ["example.com"],
                "crid": f"{config['bidder_id']}-creative-1",
                "ext": {
                    "predicted_ctr": round(click_probability, 4)
                }
            }]
        }]
    }
    
    return response


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({"status": "healthy", "bidder": config['bidder_id'], "strategy": args.strategy}), 200


@app.route('/stats', methods=['GET'])
def stats():
    """Get bidder statistics."""
    return jsonify({
        "bidder_id": config['bidder_id'],
        "strategy": args.strategy,
        "description": config['description'],
        "config": config,
        "total_spent": round(total_spent, 2),
        "bid_count": bid_count,
        "remaining_budget": round(max(0, config['daily_budget'] - total_spent), 2),
        "ml_enabled": True
    }), 200


@app.route('/predict', methods=['POST'])
def predict_ctr():
    """ML prediction endpoint to estimate click probability."""
    try:
        data = request.get_json()
        if not data or 'imp' not in data:
            return jsonify({"error": "Invalid request"}), 400
        
        predictions = []
        for imp in data['imp']:
            try:
                predictor = get_predictor()
                ctr = predictor.predict(imp)
                
                # Calculate suggested bid based on CTR
                base_price = max(imp.get('bidfloor', 1.0), config['min_bid_price'])
                ctr_multiplier = 1.0 + (ctr / 0.05)
                ctr_multiplier = min(ctr_multiplier, 2.0)
                suggested_bid = base_price * ctr_multiplier
                
                predictions.append({
                    "impid": imp.get('id', 'unknown'),
                    "predicted_ctr": round(ctr, 4),
                    "ctr_percent": round(ctr * 100, 2),
                    "suggested_bid": round(suggested_bid, 2),
                    "confidence": "medium"
                })
            except Exception as e:
                predictions.append({
                    "impid": imp.get('id', 'unknown'),
                    "error": str(e)
                })
        
        return jsonify({"predictions": predictions}), 200
    
    except Exception as e:
        logger.error(f"Prediction error: {e}")
        return jsonify({"error": "Internal server error"}), 500


@app.route('/bid', methods=['POST'])
def bid():
    """Handle incoming bid requests."""
    try:
        bid_request = request.get_json()
        logger.info("=" * 80)
        logger.info(f"Received bid request: {bid_request.get('id', 'unknown')}")
        
        if not bid_request or 'id' not in bid_request:
            return jsonify({"error": "Invalid bid request"}), 400
        
        if 'imp' not in bid_request or not bid_request['imp']:
            return jsonify({"error": "Invalid bid request"}), 400
        
        bids = []
        request_id = bid_request['id']
        
        for imp in bid_request['imp']:
            if should_bid(imp):
                logger.info(f"Deciding to bid on impression {imp.get('id')}")
                bid_response = generate_bid_response(imp, request_id)
                
                global total_spent, bid_count
                bid_price = bid_response['seatbid'][0]['bid'][0]['price']
                total_spent += bid_price
                bid_count += 1
                logger.info(f"Budget: ${total_spent:.2f} spent ({bid_count} bids)")
                
                bids.append(bid_response)
            else:
                logger.info(f"Deciding NOT to bid on impression {imp.get('id')}")
        
        if bids:
            response = bids[0]
            return jsonify(response), 200
        else:
            return "", 204
        
    except Exception as e:
        logger.error(f"Error processing bid request: {str(e)}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500


if __name__ == '__main__':
    init_database()
    
    logger.info("=" * 80)
    logger.info(f"Starting {config['bidder_id']} ({args.strategy.upper()} strategy)")
    logger.info(f"Description: {config['description']}")
    logger.info(f"Port: {args.port}")
    logger.info(f"Target Country: {config['target_country']}")
    logger.info(f"Target Devices: {config['target_devices']}")
    logger.info(f"Target OS: {config['target_os']}")
    logger.info(f"Min Bid Price: ${config['min_bid_price']} CPM")
    logger.info(f"Daily Budget: ${config['daily_budget']} CPM")
    logger.info(f"Bid Window: {config['bid_window_start']}:00 - {config['bid_window_end']}:00")
    logger.info("=" * 80)
    
    app.run(host='0.0.0.0', port=args.port, debug=False)

