from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import using the package name so it works both when running locally
# (python -m src.main) and when Render imports src.main via uvicorn.
from src.api.routers import algorithms

app = FastAPI(title="CPU Scheduling Visualizer API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(algorithms.router)

@app.get("/")
def read_root():
    return {"message": "Welcome to the CPU Scheduling Algorithms API"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)