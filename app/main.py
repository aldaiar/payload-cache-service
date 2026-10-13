from fastapi import FastAPI

app = FastAPI(
    title="Payload Cache Service",
    description="API for storing and retrieving transformed payloads.",
    version="0.1.0",
)


@app.get("/")
def root():
    return {"message": "Payload Cache Service is running"}


@app.get("/health")
def health_check():
    return {"status": "ok"}
