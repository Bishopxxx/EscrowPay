from fastapi import FastAPI

app = FastAPI(title="EscrowPay", version="0.1.0")


@app.get("/health")
def health():
    return {"status": "ok", "service": "EscrowPay"}