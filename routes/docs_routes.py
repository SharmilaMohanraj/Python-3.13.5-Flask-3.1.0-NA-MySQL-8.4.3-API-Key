"""Public, unauthenticated endpoints: health check and API documentation.

Never behind login_required/role_required — the deploy contract requires
/health and /docs to work with no auth whatsoever.
"""
import logging

from flask import Blueprint, jsonify

from openapi_spec import get_openapi_spec

logger = logging.getLogger(__name__)

docs_bp = Blueprint("docs_bp", __name__)

_SWAGGER_HTML = """<!DOCTYPE html>
<html>
<head>
  <title>LMS API Docs</title>
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css">
</head>
<body>
  <div id="swagger-ui"></div>
  <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
  <script>
    window.onload = function() {
      window.ui = SwaggerUIBundle({
        url: '/openapi.json',
        dom_id: '#swagger-ui',
      });
    };
  </script>
</body>
</html>"""


@docs_bp.route("/health", methods=["GET"])
def health():
    """Liveness probe. Always returns 200, never requires auth."""
    return jsonify({"status": "ok"}), 200


@docs_bp.route("/docs", methods=["GET"])
def docs():
    """Serve Swagger UI, pointed at /openapi.json."""
    return _SWAGGER_HTML, 200, {"Content-Type": "text/html"}


@docs_bp.route("/openapi.json", methods=["GET"])
def openapi_json():
    """Serve the hand-written OpenAPI 3.0 spec as JSON."""
    return jsonify(get_openapi_spec()), 200
