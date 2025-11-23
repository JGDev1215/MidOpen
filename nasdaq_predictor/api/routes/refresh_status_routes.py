"""
Refresh Status API Routes

GET /api/refresh-status
  Returns: Current countdown timer status with color indicators
POST /api/refresh-status/reset
  Returns: Reset status and current countdown (for manual refresh)
"""

import logging
from flask import Blueprint, jsonify
from ...services.refresh_status_service import RefreshStatusService

logger = logging.getLogger(__name__)

refresh_status_bp = Blueprint('refresh_status', __name__, url_prefix='/api')


@refresh_status_bp.route('/refresh-status', methods=['GET'])
def get_refresh_status():
    """
    Get current refresh countdown status

    Returns:
        JSON with countdown timer information and color status
    """
    try:
        status = RefreshStatusService.get_status()
        return jsonify(status), 200

    except Exception as e:
        logger.error(f"Error getting refresh status: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": f"Failed to get refresh status: {str(e)}"
        }), 500


@refresh_status_bp.route('/refresh-status/reset', methods=['POST'])
def reset_refresh_timer():
    """
    Manually reset the refresh timer (for testing/manual refresh)

    Returns:
        JSON with new status after reset
    """
    try:
        RefreshStatusService.reset_timer()
        status = RefreshStatusService.get_status()

        return jsonify({
            "success": True,
            "message": "Refresh timer reset successfully",
            "new_status": status
        }), 200

    except Exception as e:
        logger.error(f"Error resetting refresh timer: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": f"Failed to reset timer: {str(e)}"
        }), 500
