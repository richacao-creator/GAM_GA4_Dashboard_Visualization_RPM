#!/usr/bin/env python3
"""
Minimalistic Bidder Server
Simulates an OpenRTB bidder that responds to bid requests.
"""

from flask import Flask, request, jsonify, render_template_string
import json
from datetime import datetime
import logging
import sqlite3
import os
from ml_predictor import get_predictor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Bidder configuration
BIDDER_ID = "minimal-bidder-v1"
TARGET_COUNTRY = "USA"  # Only bid on requests from this country
TARGET_DEVICES = ["PHONE", "TABLET"]  # Only bid on these device types
TARGET_OS = ["iOS"]  # Only bid on these operating systems
MIN_BID_PRICE = 1.00  # Minimum bid price in CPM
BID_WINDOW_START = 9  # Start hour (24-hour format)
BID_WINDOW_END = 17  # End hour (24-hour format, exclusive)
DAILY_BUDGET = 10.00  # Maximum daily spend in CPM

# Budget tracking
total_spent = 0.00
bid_count = 0
last_reset_day = datetime.now().day

# Database configuration
DATABASE = 'bidder.db'


def init_database():
    """Initialize the SQLite database for logging."""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # Create bid_requests table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bid_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            request_id TEXT NOT NULL,
            country TEXT,
            device_type TEXT,
            os TEXT,
            bidfloor REAL,
            received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            request_json TEXT
        )
    ''')
    
    # Create bid_responses table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bid_responses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            request_id TEXT NOT NULL,
            bid_price REAL,
            response_status TEXT,
            responded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            response_json TEXT,
            predicted_ctr REAL,
            FOREIGN KEY (request_id) REFERENCES bid_requests(request_id)
        )
    ''')
    
    # Check if predicted_ctr column exists, add if not
    cursor.execute("PRAGMA table_info(bid_responses)")
    columns = [row[1] for row in cursor.fetchall()]
    if 'predicted_ctr' not in columns:
        cursor.execute('ALTER TABLE bid_responses ADD COLUMN predicted_ctr REAL')
    
    conn.commit()
    conn.close()
    logger.info("Database initialized successfully")


def log_bid_request(request_id, imp, request_json):
    """Log a bid request to the database."""
    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        country = imp.get('device', {}).get('geo', {}).get('country', '')
        device_type = imp.get('device', {}).get('devicetype', '')
        os = imp.get('device', {}).get('os', '')
        bidfloor = imp.get('bidfloor', 0)
        
        cursor.execute('''
            INSERT INTO bid_requests 
            (request_id, country, device_type, os, bidfloor, request_json)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (request_id, country, device_type, os, bidfloor, json.dumps(request_json)))
        
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Error logging bid request: {e}")


def log_bid_response(request_id, bid_price, status, response_json=None, predicted_ctr=None):
    """Log a bid response to the database."""
    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        response_json_str = json.dumps(response_json) if response_json else None
        
        cursor.execute('''
            INSERT INTO bid_responses 
            (request_id, bid_price, response_status, response_json, predicted_ctr)
            VALUES (?, ?, ?, ?, ?)
        ''', (request_id, bid_price, status, response_json_str, predicted_ctr))
        
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Error logging bid response: {e}")


def reset_budget_if_new_day():
    """Reset budget if it's a new day."""
    global total_spent, bid_count, last_reset_day
    current_day = datetime.now().day
    if current_day != last_reset_day:
        total_spent = 0.00
        bid_count = 0
        last_reset_day = current_day
        logger.info(f"Budget reset for new day. Current day: {current_day}")


def should_bid(imp):
    """
    Determine if we should bid on this impression.
    Simple logic: bid on impressions from target country and device type.
    """
    # Reset budget if new day
    reset_budget_if_new_day()
    
    # Check budget first (global check)
    global total_spent
    if total_spent >= DAILY_BUDGET:
        logger.info(f"Skipping impression: daily budget exhausted (${total_spent:.2f} >= ${DAILY_BUDGET})")
        return False
    
    # Check if impression has required fields
    if not imp.get('bidfloor'):
        return False
    
    # Check time of day
    current_hour = datetime.now().hour
    if not (BID_WINDOW_START <= current_hour < BID_WINDOW_END):
        logger.info(f"Skipping impression: outside bid window (current hour: {current_hour}, window: {BID_WINDOW_START}-{BID_WINDOW_END})")
        return False
    
    # Check device type
    device_type = imp.get('device', {}).get('devicetype', '').upper()
    if device_type not in TARGET_DEVICES:
        logger.info(f"Skipping impression: device type {device_type} not in {TARGET_DEVICES}")
        return False
    
    # Check OS
    device_os = imp.get('device', {}).get('os', '')
    if device_os not in TARGET_OS:
        logger.info(f"Skipping impression: OS {device_os} not in {TARGET_OS}")
        return False
    
    # Check country
    country = imp.get('device', {}).get('geo', {}).get('country', '')
    if country != TARGET_COUNTRY:
        logger.info(f"Skipping impression: country {country} is not {TARGET_COUNTRY}")
        return False
    
    return True


def generate_bid_response(imp, request_id):
    """
    Generate a bid response for the impression with ML-based pricing.
    """
    # Get ML click probability prediction
    try:
        predictor = get_predictor()
        click_probability = predictor.predict(imp)
    except Exception as e:
        logger.error(f"ML prediction failed: {e}")
        click_probability = 0.015  # Default 1.5% CTR
    
    # Base bid pricing
    base_price = max(imp.get('bidfloor', MIN_BID_PRICE), MIN_BID_PRICE) + 0.05
    
    # Apply ML-based price adjustment
    ctr_multiplier = 1.0 + (click_probability / 0.05)  # Scale up to 2x for 5% CTR
    ctr_multiplier = min(ctr_multiplier, 2.0)  # Cap at 2x
    bid_price = base_price * ctr_multiplier
    
    response = {
        "id": request_id,
        "bidid": f"{BIDDER_ID}-{datetime.now().timestamp()}",
        "cur": "USD",
        "seatbid": [
            {
                "seat": BIDDER_ID,
                "bid": [
                    {
                        "id": f"{BIDDER_ID}-bid-{datetime.now().timestamp()}",
                        "impid": imp.get('id'),
                        "price": round(bid_price, 2),
                        "adm": "<div style='width:320px;height:50px;background:#4CAF50;color:white;text-align:center;line-height:50px;'>Your Ad Here</div>",
                        "adomain": ["example.com"],
                        "crid": f"{BIDDER_ID}-creative-1",
                        "ext": {
                            "predicted_ctr": round(click_probability, 4)
                        }
                    }
                ]
            }
        ]
    }
    
    return response, click_probability


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({"status": "healthy", "bidder": BIDDER_ID}), 200


@app.route('/bid', methods=['POST'])
def bid():
    """
    Handle incoming bid requests (OpenRTB-like format).
    """
    try:
        # Log the incoming request
        bid_request = request.get_json()
        logger.info("=" * 80)
        logger.info(f"Received bid request: {bid_request.get('id', 'unknown')}")
        logger.info(f"Request details: {json.dumps(bid_request, indent=2)}")
        
        # Validate request structure
        if not bid_request or 'id' not in bid_request:
            logger.warning("Invalid bid request: missing 'id' field")
            return jsonify({"error": "Invalid bid request"}), 400
        
        if 'imp' not in bid_request or not bid_request['imp']:
            logger.warning("Invalid bid request: missing 'imp' field")
            return jsonify({"error": "Invalid bid request"}), 400
        
        # Process each impression
        bids = []
        request_id = bid_request['id']
        
        for imp in bid_request['imp']:
            # Log all bid requests to database
            log_bid_request(request_id, imp, bid_request)
            
            if should_bid(imp):
                logger.info(f"Deciding to bid on impression {imp.get('id')}")
                bid_response, predicted_ctr = generate_bid_response(imp, request_id)
                
                # Track budget
                global total_spent, bid_count
                bid_price = bid_response['seatbid'][0]['bid'][0]['price']
                total_spent += bid_price
                bid_count += 1
                logger.info(f"Budget update: ${total_spent:.2f} spent ({bid_count} bids)")
                
                bids.append((bid_response, predicted_ctr))
            else:
                logger.info(f"Deciding NOT to bid on impression {imp.get('id')}")
        
        # If we have bids, return the response, otherwise 204 No Content
        if bids:
            # In real OpenRTB, we'd typically combine multiple impressions into one response
            # For simplicity, we'll return the first bid
            response, predicted_ctr = bids[0]
            bid_price = response['seatbid'][0]['bid'][0]['price']
            log_bid_response(request_id, bid_price, "ACCEPTED", response, predicted_ctr)
            logger.info(f"Returning bid response: {json.dumps(response, indent=2)}")
            return jsonify(response), 200
        else:
            log_bid_response(request_id, 0.00, "REJECTED", None, None)
            logger.info("No bid returned (204 No Content)")
            return "", 204
        
    except Exception as e:
        logger.error(f"Error processing bid request: {str(e)}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500


@app.route('/reset', methods=['POST'])
def reset_budget():
    """Manually reset the budget."""
    global total_spent, bid_count
    total_spent = 0.00
    bid_count = 0
    logger.info("Budget manually reset")
    return jsonify({
        "message": "Budget reset successfully",
        "total_spent": 0.00,
        "bid_count": 0
    }), 200


@app.route('/stats', methods=['GET'])
def stats():
    """Get bidder statistics (placeholder for future enhancements)."""
    return jsonify({
        "bidder_id": BIDDER_ID,
        "target_country": TARGET_COUNTRY,
        "target_devices": TARGET_DEVICES,
        "target_os": TARGET_OS,
        "min_bid_price": MIN_BID_PRICE,
        "daily_budget": DAILY_BUDGET,
        "total_spent": round(total_spent, 2),
        "bid_count": bid_count,
        "remaining_budget": round(max(0, DAILY_BUDGET - total_spent), 2)
    }), 200


@app.route('/analytics', methods=['GET'])
def analytics():
    """Get analytics from database."""
    try:
        conn = sqlite3.connect(DATABASE)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Total requests
        cursor.execute('SELECT COUNT(*) as count FROM bid_requests')
        total_requests = cursor.fetchone()['count']
        
        # Total bids
        cursor.execute('SELECT COUNT(*) as count FROM bid_responses WHERE response_status = "ACCEPTED"')
        total_bids = cursor.fetchone()['count']
        
        # Total spend
        cursor.execute('SELECT COALESCE(SUM(bid_price), 0) as total FROM bid_responses WHERE response_status = "ACCEPTED"')
        total_spent_db = cursor.fetchone()['total']
        
        # Bid rate
        bid_rate = (total_bids / total_requests * 100) if total_requests > 0 else 0
        
        # Average bid price
        cursor.execute('SELECT AVG(bid_price) as avg FROM bid_responses WHERE response_status = "ACCEPTED"')
        avg_price = cursor.fetchone()['avg']
        
        # ML metrics
        cursor.execute('SELECT AVG(predicted_ctr) as avg_ctr FROM bid_responses WHERE response_status = "ACCEPTED" AND predicted_ctr IS NOT NULL')
        avg_ctr = cursor.fetchone()['avg_ctr']
        
        cursor.execute('SELECT MIN(predicted_ctr) as min_ctr FROM bid_responses WHERE response_status = "ACCEPTED" AND predicted_ctr IS NOT NULL')
        min_ctr = cursor.fetchone()['min_ctr']
        
        cursor.execute('SELECT MAX(predicted_ctr) as max_ctr FROM bid_responses WHERE response_status = "ACCEPTED" AND predicted_ctr IS NOT NULL')
        max_ctr = cursor.fetchone()['max_ctr']
        
        # Top countries
        cursor.execute('''
            SELECT country, COUNT(*) as count 
            FROM bid_requests 
            GROUP BY country 
            ORDER BY count DESC 
            LIMIT 5
        ''')
        top_countries = [{"country": row['country'], "requests": row['count']} for row in cursor.fetchall()]
        
        # Top devices
        cursor.execute('''
            SELECT device_type, COUNT(*) as count 
            FROM bid_requests 
            GROUP BY device_type 
            ORDER BY count DESC
        ''')
        top_devices = [{"device": row['device_type'], "requests": row['count']} for row in cursor.fetchall()]
        
        conn.close()
        
        return jsonify({
            "summary": {
                "total_requests": total_requests,
                "total_bids": total_bids,
                "bid_rate": round(bid_rate, 2),
                "total_spent": round(total_spent_db, 2),
                "avg_bid_price": round(avg_price, 2) if avg_price else 0
            },
            "ml_metrics": {
                "avg_ctr": round(avg_ctr, 4) if avg_ctr else 0,
                "min_ctr": round(min_ctr, 4) if min_ctr else 0,
                "max_ctr": round(max_ctr, 4) if max_ctr else 0
            },
            "top_countries": top_countries,
            "top_devices": top_devices
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting analytics: {e}")
        return jsonify({"error": "Failed to get analytics"}), 500


DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Bid Request Simulator - Analytics Dashboard</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        
        .header {
            background: white;
            padding: 30px;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            margin-bottom: 30px;
            text-align: center;
        }
        
        .header h1 {
            color: #667eea;
            font-size: 2.5em;
            margin-bottom: 10px;
        }
        
        .header p {
            color: #666;
            font-size: 1.1em;
        }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .stat-card {
            background: white;
            padding: 30px;
            border-radius: 15px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            text-align: center;
            transition: transform 0.3s ease;
        }
        
        .stat-card:hover {
            transform: translateY(-5px);
        }
        
        .stat-value {
            font-size: 2.5em;
            font-weight: bold;
            color: #667eea;
            margin-bottom: 10px;
        }
        
        .stat-label {
            color: #666;
            font-size: 1.1em;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        
        .charts-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 20px;
        }
        
        .chart-card {
            background: white;
            padding: 30px;
            border-radius: 15px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        }
        
        .chart-card h2 {
            color: #333;
            margin-bottom: 20px;
            font-size: 1.5em;
        }
        
        .country-bar {
            display: flex;
            align-items: center;
            margin-bottom: 15px;
        }
        
        .country-name {
            width: 60px;
            font-weight: bold;
            color: #333;
        }
        
        .bar-container {
            flex: 1;
            height: 30px;
            background: #f0f0f0;
            border-radius: 15px;
            overflow: hidden;
            margin: 0 15px;
            position: relative;
        }
        
        .bar {
            height: 100%;
            background: linear-gradient(90deg, #667eea, #764ba2);
            border-radius: 15px;
            transition: width 1s ease;
        }
        
        .bar-value {
            position: absolute;
            right: 10px;
            top: 50%;
            transform: translateY(-50%);
            font-weight: bold;
            color: #333;
        }
        
        .device-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 15px;
            background: #f8f9fa;
            border-radius: 10px;
            margin-bottom: 10px;
        }
        
        .device-name {
            font-weight: bold;
            color: #333;
        }
        
        .device-count {
            font-size: 1.5em;
            color: #667eea;
            font-weight: bold;
        }
        
        .refresh-btn {
            position: fixed;
            bottom: 30px;
            right: 30px;
            background: #667eea;
            color: white;
            border: none;
            padding: 15px 30px;
            border-radius: 50px;
            font-size: 1em;
            cursor: pointer;
            box-shadow: 0 5px 15px rgba(0,0,0,0.3);
            transition: all 0.3s ease;
        }
        
        .refresh-btn:hover {
            background: #764ba2;
            transform: scale(1.05);
        }
        
        .loading {
            text-align: center;
            padding: 50px;
            font-size: 1.5em;
            color: white;
        }
        
        .error {
            background: #ff6b6b;
            color: white;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
        }
        
        @media (max-width: 768px) {
            .header h1 {
                font-size: 1.8em;
            }
            
            .charts-grid {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 Bid Request Simulator</h1>
            <p>Analytics Dashboard - Real-time Performance Metrics</p>
        </div>
        
        <div class="loading" id="loading">Loading data...</div>
        <div id="dashboard" style="display: none;">
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-value" id="total-requests">0</div>
                    <div class="stat-label">Total Requests</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value" id="total-bids">0</div>
                    <div class="stat-label">Bids Accepted</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value" id="bid-rate">0%</div>
                    <div class="stat-label">Bid Rate</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value" id="total-spent">$0</div>
                    <div class="stat-label">Total Spent</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value" id="avg-price">$0</div>
                    <div class="stat-label">Avg Bid Price</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value" id="avg-ctr">0%</div>
                    <div class="stat-label">Avg Predicted CTR</div>
                </div>
            </div>
            
            <div class="charts-grid">
                <div class="chart-card">
                    <h2>🤖 ML Performance</h2>
                    <div id="ml-chart"></div>
                </div>
            </div>
            
            <div class="charts-grid">
                <div class="chart-card">
                    <h2>🌍 Top Countries</h2>
                    <div id="countries-chart"></div>
                </div>
                <div class="chart-card">
                    <h2>📱 Device Distribution</h2>
                    <div id="devices-chart"></div>
                </div>
            </div>
        </div>
        <div id="error" class="error" style="display: none;"></div>
    </div>
    
    <button class="refresh-btn" onclick="loadData()">🔄 Refresh</button>
    
    <script>
        function loadData() {
            document.getElementById('loading').style.display = 'block';
            document.getElementById('dashboard').style.display = 'none';
            document.getElementById('error').style.display = 'none';
            
            fetch('/analytics')
                .then(response => response.json())
                .then(data => {
                    document.getElementById('loading').style.display = 'none';
                    document.getElementById('dashboard').style.display = 'block';
                    
                    // Update stats
                    document.getElementById('total-requests').textContent = data.summary.total_requests;
                    document.getElementById('total-bids').textContent = data.summary.total_bids;
                    document.getElementById('bid-rate').textContent = data.summary.bid_rate.toFixed(1) + '%';
                    document.getElementById('total-spent').textContent = '$' + data.summary.total_spent.toFixed(2);
                    document.getElementById('avg-price').textContent = '$' + data.summary.avg_bid_price.toFixed(2);
                    document.getElementById('avg-ctr').textContent = (data.ml_metrics.avg_ctr * 100).toFixed(2) + '%';
                    
                    // Update ML chart
                    const mlChart = document.getElementById('ml-chart');
                    mlChart.innerHTML = '';
                    const mlItems = [
                        { label: 'Average CTR', value: (data.ml_metrics.avg_ctr * 100).toFixed(2) + '%', type: 'average' },
                        { label: 'Min CTR', value: (data.ml_metrics.min_ctr * 100).toFixed(2) + '%', type: 'min' },
                        { label: 'Max CTR', value: (data.ml_metrics.max_ctr * 100).toFixed(2) + '%', type: 'max' }
                    ];
                    mlItems.forEach(item => {
                        const itemDiv = document.createElement('div');
                        itemDiv.className = 'device-item';
                        itemDiv.innerHTML = `
                            <div class="device-name">${item.label}</div>
                            <div class="device-count">${item.value}</div>
                        `;
                        mlChart.appendChild(itemDiv);
                    });
                    
                    // Update countries chart
                    const countriesChart = document.getElementById('countries-chart');
                    countriesChart.innerHTML = '';
                    const maxCountryRequests = Math.max(...data.top_countries.map(c => c.requests), 1);
                    data.top_countries.forEach(country => {
                        const percentage = (country.requests / maxCountryRequests * 100).toFixed(0);
                        const bar = document.createElement('div');
                        bar.className = 'country-bar';
                        bar.innerHTML = `
                            <div class="country-name">${country.country}</div>
                            <div class="bar-container">
                                <div class="bar" style="width: ${percentage}%"></div>
                                <div class="bar-value">${country.requests}</div>
                            </div>
                        `;
                        countriesChart.appendChild(bar);
                    });
                    
                    // Update devices chart
                    const devicesChart = document.getElementById('devices-chart');
                    devicesChart.innerHTML = '';
                    data.top_devices.forEach(device => {
                        const item = document.createElement('div');
                        item.className = 'device-item';
                        item.innerHTML = `
                            <div class="device-name">${device.device}</div>
                            <div class="device-count">${device.requests}</div>
                        `;
                        devicesChart.appendChild(item);
                    });
                })
                .catch(error => {
                    document.getElementById('loading').style.display = 'none';
                    document.getElementById('error').style.display = 'block';
                    document.getElementById('error').textContent = 'Error loading data: ' + error.message;
                });
        }
        
        // Load data on page load
        loadData();
        
        // Auto-refresh every 5 seconds
        setInterval(loadData, 5000);
    </script>
</body>
</html>
"""


@app.route('/dashboard', methods=['GET'])
def dashboard():
    """Serve the analytics dashboard."""
    return render_template_string(DASHBOARD_HTML)


if __name__ == '__main__':
    # Initialize database
    init_database()
    
    logger.info("=" * 80)
    logger.info("Starting Minimalistic Bidder Server")
    logger.info(f"Bidder ID: {BIDDER_ID}")
    logger.info(f"Target Country: {TARGET_COUNTRY}")
    logger.info(f"Target Devices: {TARGET_DEVICES}")
    logger.info(f"Target OS: {TARGET_OS}")
    logger.info(f"Min Bid Price: ${MIN_BID_PRICE} CPM")
    logger.info(f"Daily Budget: ${DAILY_BUDGET} CPM")
    logger.info(f"Bid Window: {BID_WINDOW_START}:00 - {BID_WINDOW_END}:00")
    logger.info(f"Database: {DATABASE}")
    logger.info("=" * 80)
    app.run(host='0.0.0.0', port=8080, debug=True)

