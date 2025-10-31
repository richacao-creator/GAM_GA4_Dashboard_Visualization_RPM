#!/bin/bash
# Launch all three bidder servers with different strategies

echo "🚀 Starting Multi-Strategy Bidder Setup"
echo "========================================="
echo ""

# Kill any existing bidder processes
pkill -f bidder_multi.py 2>/dev/null
sleep 1

# Start Conservative Bidder (Port 8081)
echo "📊 Starting Conservative Bidder (Port 8081)"
python3 bidder_multi.py --strategy conservative --port 8081 > /tmp/conservative.log 2>&1 &
sleep 1

# Start Aggressive Bidder (Port 8082)
echo "📊 Starting Aggressive Bidder (Port 8082)"
python3 bidder_multi.py --strategy aggressive --port 8082 > /tmp/aggressive.log 2>&1 &
sleep 1

# Start Balanced Bidder (Port 8083)
echo "📊 Starting Balanced Bidder (Port 8083)"
python3 bidder_multi.py --strategy balanced --port 8083 > /tmp/balanced.log 2>&1 &
sleep 1

echo ""
echo "✅ All bidders started!"
echo ""
echo "📋 Endpoints:"
echo "   Conservative: http://localhost:8081"
echo "   Aggressive:   http://localhost:8082"
echo "   Balanced:     http://localhost:8083"
echo ""
echo "🔍 Check logs:"
echo "   tail -f /tmp/conservative.log"
echo "   tail -f /tmp/aggressive.log"
echo "   tail -f /tmp/balanced.log"
echo ""
echo "🛑 Stop all: pkill -f bidder_multi.py"
echo ""

