"""Hand-written OpenAPI 3.0 specification for the LMS API.

Flask has no built-in OpenAPI generator, so per the project's documentation
standard this spec is maintained by hand as a plain Python dict and served
as JSON at /openapi.json; /docs renders Swagger UI (via swagger-ui-dist on
a CDN) pointed at that spec. Whenever an endpoint is added or changed,
this dict is updated in the same change.
"""

_ERROR_SCHEMA = {
    "type": "object",
    "properties": {
        "error": {"type": "string"},
        "code": {"type": "string"},
        "timestamp": {"type": "string", "format": "date-time"},
        "correlation_id": {"type": "string"},
    },
}

_BEARER_AUTH = [{"bearerAuth": []}]


def _error_response(description: str) -> dict:
    return {
        "description": description,
        "content": {"application/json": {"schema": _ERROR_SCHEMA}},
    }


def get_openapi_spec() -> dict:
    """Return the full OpenAPI 3.0 document for this API."""
    return {
        "openapi": "3.0.3",
        "info": {
            "title": "LMS REST API",
            "description": "Learning Management System API: courses, modules, lessons, enrollment, progress tracking, and certificates.",
            "version": "1.0.0",
        },
        "servers": [{"url": "/"}],
        "components": {
            "securitySchemes": {
                "bearerAuth": {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"}
            },
            "schemas": {
                "Error": _ERROR_SCHEMA,
                "User": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer"},
                        "name": {"type": "string"},
                        "email": {"type": "string"},
                        "role": {"type": "string", "enum": ["instructor", "student"]},
                    },
                },
                "Course": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer"},
                        "instructor_id": {"type": "integer"},
                        "title": {"type": "string"},
                        "description": {"type": "string"},
                        "category": {"type": "string"},
                    },
                },
                "Module": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer"},
                        "course_id": {"type": "integer"},
                        "title": {"type": "string"},
                        "order_index": {"type": "integer"},
                    },
                },
                "Lesson": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer"},
                        "module_id": {"type": "integer"},
                        "title": {"type": "string"},
                        "order_index": {"type": "integer"},
                    },
                },
                "Enrollment": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer"},
                        "student_id": {"type": "integer"},
                        "course_id": {"type": "integer"},
                        "enrolled_at": {"type": "string", "format": "date-time"},
                        "status": {"type": "string", "enum": ["active", "completed"]},
                    },
                },
                "LessonProgress": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer"},
                        "student_id": {"type": "integer"},
                        "lesson_id": {"type": "integer"},
                        "status": {"type": "string", "enum": ["NOT_STARTED", "IN_PROGRESS", "COMPLETED"]},
                        "module_completed": {"type": "boolean"},
                        "updated_at": {"type": "string", "format": "date-time"},
                        "module_completed_now": {"type": "boolean"},
                        "course_completed_now": {"type": "boolean"},
                    },
                },
                "Certificate": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer"},
                        "student_id": {"type": "integer"},
                        "course_id": {"type": "integer"},
                        "issued_at": {"type": "string", "format": "date-time"},
                    },
                },
            },
        },
        "paths": {
            "/health": {
                "get": {
                    "summary": "Health check",
                    "security": [],
                    "responses": {"200": {"description": "Service is healthy"}},
                }
            },
            "/auth/register": {
                "post": {
                    "summary": "Register a new user",
                    "security": [],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["name", "email", "password", "role"],
                                    "properties": {
                                        "name": {"type": "string"},
                                        "email": {"type": "string"},
                                        "password": {"type": "string"},
                                        "role": {"type": "string", "enum": ["instructor", "student"]},
                                    },
                                }
                            }
                        },
                    },
                    "responses": {
                        "201": {"description": "User registered"},
                        "400": _error_response("Validation error"),
                        "409": _error_response("Email already exists"),
                    },
                }
            },
            "/auth/login": {
                "post": {
                    "summary": "Login and receive a JWT",
                    "security": [],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["email", "password"],
                                    "properties": {
                                        "email": {"type": "string"},
                                        "password": {"type": "string"},
                                    },
                                }
                            }
                        },
                    },
                    "responses": {
                        "200": {"description": "Login successful"},
                        "401": _error_response("Invalid credentials"),
                    },
                }
            },
            "/courses": {
                "post": {
                    "summary": "Create a course (instructor only)",
                    "security": _BEARER_AUTH,
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["title"],
                                    "properties": {
                                        "title": {"type": "string"},
                                        "description": {"type": "string"},
                                        "category": {"type": "string"},
                                    },
                                }
                            }
                        },
                    },
                    "responses": {
                        "201": {"description": "Course created", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Course"}}}},
                        "400": _error_response("Validation error"),
                        "401": _error_response("Unauthenticated"),
                        "403": _error_response("Not an instructor"),
                    },
                },
                "get": {
                    "summary": "List/search courses",
                    "security": _BEARER_AUTH,
                    "parameters": [
                        {"name": "category", "in": "query", "schema": {"type": "string"}},
                        {"name": "enrollment_status", "in": "query", "schema": {"type": "string", "enum": ["enrolled", "not_enrolled"]}},
                    ],
                    "responses": {
                        "200": {
                            "description": "List of courses",
                            "content": {"application/json": {"schema": {"type": "array", "items": {"$ref": "#/components/schemas/Course"}}}},
                        },
                        "401": _error_response("Unauthenticated"),
                    },
                },
            },
            "/courses/{course_id}": {
                "get": {
                    "summary": "Get course detail with nested modules/lessons",
                    "security": _BEARER_AUTH,
                    "parameters": [{"name": "course_id", "in": "path", "required": True, "schema": {"type": "integer"}}],
                    "responses": {
                        "200": {"description": "Course detail"},
                        "401": _error_response("Unauthenticated"),
                        "404": _error_response("Course not found"),
                    },
                }
            },
            "/courses/{course_id}/stats": {
                "get": {
                    "summary": "Enrollment statistics for a course (owning instructor only)",
                    "security": _BEARER_AUTH,
                    "parameters": [{"name": "course_id", "in": "path", "required": True, "schema": {"type": "integer"}}],
                    "responses": {
                        "200": {"description": "Course stats: enrollment_count, completed_count, completion_rate"},
                        "401": _error_response("Unauthenticated"),
                        "403": _error_response("Not the course owner"),
                        "404": _error_response("Course not found"),
                    },
                }
            },
            "/courses/{course_id}/modules": {
                "post": {
                    "summary": "Create a module in a course (owning instructor only)",
                    "security": _BEARER_AUTH,
                    "parameters": [{"name": "course_id", "in": "path", "required": True, "schema": {"type": "integer"}}],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["title", "order_index"],
                                    "properties": {"title": {"type": "string"}, "order_index": {"type": "integer"}},
                                }
                            }
                        },
                    },
                    "responses": {
                        "201": {"description": "Module created", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Module"}}}},
                        "400": _error_response("Validation error"),
                        "401": _error_response("Unauthenticated"),
                        "403": _error_response("Not the course owner"),
                        "404": _error_response("Course not found"),
                    },
                },
                "get": {
                    "summary": "List modules (with nested lessons) for a course",
                    "security": _BEARER_AUTH,
                    "parameters": [{"name": "course_id", "in": "path", "required": True, "schema": {"type": "integer"}}],
                    "responses": {
                        "200": {"description": "List of modules with nested lessons"},
                        "401": _error_response("Unauthenticated"),
                        "404": _error_response("Course not found"),
                    },
                },
            },
            "/modules/{module_id}/lessons": {
                "post": {
                    "summary": "Create a lesson in a module (owning instructor only)",
                    "security": _BEARER_AUTH,
                    "parameters": [{"name": "module_id", "in": "path", "required": True, "schema": {"type": "integer"}}],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["title", "order_index"],
                                    "properties": {"title": {"type": "string"}, "order_index": {"type": "integer"}},
                                }
                            }
                        },
                    },
                    "responses": {
                        "201": {"description": "Lesson created", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Lesson"}}}},
                        "400": _error_response("Validation error"),
                        "401": _error_response("Unauthenticated"),
                        "403": _error_response("Not the course owner"),
                        "404": _error_response("Module not found"),
                    },
                }
            },
            "/courses/{course_id}/enroll": {
                "post": {
                    "summary": "Enroll the authenticated student in a course",
                    "security": _BEARER_AUTH,
                    "parameters": [{"name": "course_id", "in": "path", "required": True, "schema": {"type": "integer"}}],
                    "responses": {
                        "201": {"description": "Enrolled", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Enrollment"}}}},
                        "401": _error_response("Unauthenticated"),
                        "403": _error_response("Not a student"),
                        "404": _error_response("Course not found"),
                        "409": _error_response("Already enrolled"),
                    },
                }
            },
            "/lessons/{lesson_id}/progress": {
                "put": {
                    "summary": "Update the authenticated student's progress on a lesson",
                    "security": _BEARER_AUTH,
                    "parameters": [{"name": "lesson_id", "in": "path", "required": True, "schema": {"type": "integer"}}],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["status"],
                                    "properties": {"status": {"type": "string", "enum": ["NOT_STARTED", "IN_PROGRESS", "COMPLETED"]}},
                                }
                            }
                        },
                    },
                    "responses": {
                        "200": {"description": "Progress updated", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/LessonProgress"}}}},
                        "400": _error_response("Invalid status"),
                        "401": _error_response("Unauthenticated"),
                        "403": _error_response("Not a student"),
                        "404": _error_response("Lesson not found"),
                    },
                }
            },
            "/students/{student_id}/certificates": {
                "get": {
                    "summary": "List a student's certificates",
                    "security": _BEARER_AUTH,
                    "parameters": [{"name": "student_id", "in": "path", "required": True, "schema": {"type": "integer"}}],
                    "responses": {
                        "200": {
                            "description": "List of certificates",
                            "content": {"application/json": {"schema": {"type": "array", "items": {"$ref": "#/components/schemas/Certificate"}}}},
                        },
                        "401": _error_response("Unauthenticated"),
                        "403": _error_response("Not permitted to view this student's certificates"),
                    },
                }
            },
        },
    }
