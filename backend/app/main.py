from fastapi import FastAPI

app = FastAPI(
    title="AI Personal Finance Advisor",
    version="0.1.0"
)

@app.get("/")
def read_root():
    return {"message": "Welcome to the AI Personal Finance Advisor API!"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}