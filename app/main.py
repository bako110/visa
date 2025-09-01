from fastapi import FastAPI
from app.routes import auth

app = FastAPI(title="Visa Carte Backend")

app.include_router(auth.router)

@app.get("/")
async def root():
    return {"message": "Bienvenue sur le backend Visa Carte!"}
