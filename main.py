import time
import uuid
from collections import deque

from fastapi import FastAPI, Request
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response

app = FastAPI()

start_time = time.time()

logs = deque(maxlen=1000)

REQUEST_COUNTER = Counter(
    "http_requests_total",
    "Total HTTP requests"
)


@app.middleware("http")
async def log_requests(request: Request, call_next):

    request_id = str(uuid.uuid4())

    response = await call_next(request)

    REQUEST_COUNTER.inc()

    logs.append(
        {
            "level": "INFO",
            "ts": time.time(),
            "path": request.url.path,
            "request_id": request_id,
        }
    )

    response.headers["X-Request-ID"] = request_id

    return response


@app.get("/work")
def work(n: int):

    total = 0

    for i in range(n):
        total += i

    return {
        "email": "YOUR_EMAIL",
        "done": n
    }


@app.get("/metrics")
def metrics():
    return Response(
        generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )


@app.get("/healthz")
def health():

    return {
        "status": "ok",
        "uptime_s": time.time() - start_time
    }


@app.get("/logs/tail")
def tail(limit: int = 10):

    return list(logs)[-limit:]