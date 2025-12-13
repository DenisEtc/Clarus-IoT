from fastapi import FastAPI

app = FastAPI(title="Clarus-IoT")

@app.get("/health")
def health():
    return {"status": "ok"}
