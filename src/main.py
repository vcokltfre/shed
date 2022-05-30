from hmac import compare_digest
from os import environ
from typing import Callable, Coroutine

from fastapi import FastAPI, Request, Response

from .routes import router

app = FastAPI()

app.include_router(router)


@app.middleware("http")  # type: ignore
async def authenticate(request: Request, call_next: Callable[[Request], Coroutine[None, None, Response]]) -> Response:
    auth = request.headers["Authorization"]

    if not compare_digest(environ["AUTH"], auth):
        return Response(status_code=401)

    return await call_next(request)
