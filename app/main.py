from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import auth

app = FastAPI(title="Visa Carte Backend")

# --- CORS Middleware ---
origins = [
    "*"  # ⚠️ Pour tests uniquement, autorise toutes les origines. Plus tard, mets l'URL de ton APK ou domaine spécifique
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Routes ---
app.include_router(auth.router)

@app.get("/")
async def root():
    return {"message": "Bienvenue sur le backend Visa Carte!"}
