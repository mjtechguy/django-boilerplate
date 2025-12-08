import hashlib
import json
from typing import Optional

from django.conf import settings
from django.core.cache import caches
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin


class IdempotencyMiddleware(MiddlewareMixin):
    """
    Simple idempotency guard: rejects duplicate mutating requests with same key.
    Stores a hash of method+path+body under Idempotency-Key with TTL.
    """

    def process_request(self, request):
        if request.method in ("GET", "HEAD", "OPTIONS", "TRACE"):
            return None
        key = request.headers.get(settings.IDEMPOTENCY_HEADER)
        if not key:
            return None
        cache = caches["idempotency"]
        body_hash = self._hash_request(request)
        existing = cache.get(key)
        if existing:
            if existing == body_hash:
                return JsonResponse(
                    {"detail": "Duplicate request", "idempotency_key": key},
                    status=409,
                )
            return JsonResponse(
                {"detail": "Idempotency key reuse with different payload", "idempotency_key": key},
                status=409,
            )
        cache.set(key, body_hash, timeout=settings.IDEMPOTENCY_TTL_SECONDS)
        return None

    def _hash_request(self, request) -> str:
        payload = {
            "method": request.method,
            "path": request.path,
            "body": self._get_body(request),
        }
        data = json.dumps(payload, sort_keys=True)
        return hashlib.sha256(data.encode("utf-8")).hexdigest()

    def _get_body(self, request) -> Optional[str]:
        try:
            body = request.body.decode("utf-8")
        except Exception:  # noqa: BLE001
            body = ""
        return body
