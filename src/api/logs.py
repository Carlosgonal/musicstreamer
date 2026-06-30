from flask import Blueprint, jsonify, request

from services.logging import tail_log_lines


logs_api = Blueprint("logs_api", __name__)


@logs_api.get("/recent")
def recent():
    try:
        limit = int(request.args.get("limit", "200"))
    except ValueError:
        limit = 200

    query = request.args.get("query", "")
    lines = tail_log_lines(limit=limit, query=query)

    return jsonify({
        "lines": lines,
        "count": len(lines),
    })
