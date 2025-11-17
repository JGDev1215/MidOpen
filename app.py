"""
NQ=F Real-Time Market Data Dashboard
Flask application with live data endpoints and dashboard UI
"""

import logging
from flask import Flask, jsonify, render_template
from flask_cors import CORS

# Import all route blueprints
from nasdaq_predictor.api.routes.market_status_routes import market_status_bp
from nasdaq_predictor.api.routes.price_routes import price_bp
from nasdaq_predictor.api.routes.reference_levels_routes import reference_levels_bp
from nasdaq_predictor.api.routes.session_ranges_routes import session_ranges_bp
from nasdaq_predictor.api.routes.fibonacci_routes import fibonacci_bp
from nasdaq_predictor.api.routes.block_routes import block_bp

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Register blueprints
app.register_blueprint(market_status_bp)
app.register_blueprint(price_bp)
app.register_blueprint(reference_levels_bp)
app.register_blueprint(session_ranges_bp)
app.register_blueprint(fibonacci_bp)
app.register_blueprint(block_bp)


@app.route('/', methods=['GET'])
def index():
    """Root endpoint with API documentation"""
    return jsonify({
        "success": True,
        "application": "NQ=F Real-Time Market Data Dashboard",
        "version": "1.0.0",
        "ui": {
            "dashboard": "GET /dashboard - Interactive real-time dashboard UI"
        },
        "api_endpoints": {
            "market_status": {
                "GET /api/market-status/<ticker>": "Full market status with countdown",
                "GET /api/market-status/<ticker>/is-open": "Quick market open check",
                "GET /api/market-status/<ticker>/next-event": "Next market open/close event"
            },
            "price": {
                "GET /api/current-price/<ticker>": "Current price with change",
                "GET /api/current-price/<ticker>/ohlc": "Current minute OHLC"
            },
            "reference_levels": {
                "GET /api/reference-levels/<ticker>": "All 16 reference levels",
                "GET /api/reference-levels/<ticker>/summary": "Key levels for dashboard",
                "GET /api/reference-levels/<ticker>/closest": "Closest level to price"
            },
            "session_ranges": {
                "GET /api/session-ranges/<ticker>": "Current and previous session ranges",
                "GET /api/session-ranges/<ticker>/current": "Current session ranges",
                "GET /api/session-ranges/<ticker>/previous": "Previous day session ranges"
            },
            "fibonacci_pivots": {
                "GET /api/fibonacci-pivots/<ticker>": "Weekly and daily pivots",
                "GET /api/fibonacci-pivots/<ticker>/daily": "Daily pivots only",
                "GET /api/fibonacci-pivots/<ticker>/weekly": "Weekly pivots only"
            },
            "hourly_blocks": {
                "GET /api/hourly-blocks/<ticker>": "7-block hourly segmentation",
                "GET /api/hourly-blocks/<ticker>/current-block": "Current block only",
                "GET /api/hourly-blocks/<ticker>/summary": "Progress bar summary"
            }
        },
        "default_ticker": "NQ=F",
        "market_hours": "Sunday 6 PM ET - Friday 5 PM ET",
        "refresh_interval": "75 seconds"
    }), 200


@app.route('/dashboard', methods=['GET'])
def dashboard():
    """Real-time market data dashboard UI"""
    logger.info("Serving dashboard UI")
    return render_template('dashboard.html')


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "version": "1.0.0"
    }), 200


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({
        "success": False,
        "error": "Endpoint not found",
        "path": error.description
    }), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    logger.error(f"Internal server error: {error}")
    return jsonify({
        "success": False,
        "error": "Internal server error"
    }), 500


if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 8080))
    logger.info(f"Starting NQ=F Market Data Dashboard API on port {port}")
    app.run(
        host='0.0.0.0',
        port=port,
        debug=False,
        use_reloader=False
    )
