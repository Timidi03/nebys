from fastapi import FastAPI, Request, Response

from src.common.logger import logger

app = FastAPI()
received = []


@app.post("/webhooks/ok")
async def ok(request: Request):
    body = await request.json()
    received.append(body)
    logger.info("received: %s", body)
    return Response(status_code=200)


@app.post("/webhooks/fail")
async def fail(request: Request):
    logger.info("received (answering 500): %s", await request.json())
    return Response(status_code=500)


@app.get("/webhooks")
async def list_received():
    return received[-100:]
