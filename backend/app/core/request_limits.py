"""Bounded process-local login throttling for the single-process deployment."""
from collections import OrderedDict, deque
from threading import Lock
from time import monotonic

from fastapi import Request
from starlette.responses import JSONResponse

_attempts = OrderedDict()
_lock = Lock()


async def request_limits(request: Request, call_next):
    if request.method == "POST" and request.url.path == "/api/v1/auth/login":
        address = request.client.host if request.client else "unknown"
        now = monotonic()
        with _lock:
            attempts = _attempts.setdefault(address, deque())
            while attempts and attempts[0] < now - 60:
                attempts.popleft()
            if len(attempts) >= 10:
                return JSONResponse({"detail": "Muitas tentativas. Aguarde um minuto."}, status_code=429, headers={"Retry-After": "60"})
            attempts.append(now)
            _attempts.move_to_end(address)
            while len(_attempts) > 10000:
                _attempts.popitem(last=False)
    return await call_next(request)


class BoundedBody:
    """Limit streamed HTTP bodies, including requests without Content-Length."""
    def __init__(self, app, max_bytes=12 * 1024 * 1024):
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            return await self.app(scope, receive, send)
        from starlette.exceptions import HTTPException
        count = 0
        async def limited_receive():
            nonlocal count
            message = await receive()
            if message['type'] == 'http.request':
                count += len(message.get('body', b''))
                if count > self.max_bytes:
                    raise HTTPException(413, 'Corpo da requisição excede o limite permitido')
            return message
        return await self.app(scope, limited_receive, send)
