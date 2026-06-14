from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import requests
import os

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

SERPAPI_KEY = os.getenv("SERPAPI_KEY")

@app.get("/buscar")
def buscar(q: str):
    url = "https://serpapi.com/search"

    parametros = {
        "q": f"download {q} filetype:exe OR filetype:zip OR filetype:rar OR filetype:pdf",
        "api_key": SERPAPI_KEY,
        "num": 10,
        "hl": "pt",
        "gl": "br"
    }

    resposta = requests.get(url, params=parametros)
    dados = resposta.json()

    resultados = []
    for item in dados.get("organic_results", []):
        resultados.append({
            "titulo": item.get("title", ""),
            "link": item.get("link", ""),
            "dominio": item.get("displayed_link", ""),
            "descricao": item.get("snippet", "")
        })

    return {"resultados": resultados}