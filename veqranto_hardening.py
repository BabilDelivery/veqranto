def register_hardening(app):
    app.config.setdefault("MAX_CONTENT_LENGTH", 16 * 1024 * 1024)

    @app.after_request
    def veqranto_security_headers(response):
        response.headers.setdefault("X-Content-Type-Options","nosniff")
        response.headers.setdefault("X-Frame-Options","SAMEORIGIN")
        response.headers.setdefault("Referrer-Policy","strict-origin-when-cross-origin")
        response.headers.setdefault(
            "Permissions-Policy",
            "camera=(), microphone=(), geolocation=()"
        )
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self' 'unsafe-inline' 'unsafe-eval' data: blob: https:;"
        )
        return response
