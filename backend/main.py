from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import requests
import os
from urllib.parse import urlparse

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

SERPAPI_KEY = os.getenv("SERPAPI_KEY")

# Sites conhecidos de download — sobem no ranking
WHITELIST = [
    "github.com", "sourceforge.net", "archive.org",
    "mediafire.com", "mega.nz", "drive.google.com",
    "1fichier.com", "pixeldrain.com", "gofile.io",
    "uploadhaven.com", "sendspace.com"
]

# Extensões que indicam arquivo direto
EXTENSOES_DIRETAS = [
    ".exe", ".zip", ".rar", ".7z", ".tar", ".gz",
    ".pdf", ".epub", ".mobi", ".dmg", ".apk",
    ".mp4", ".mkv", ".avi", ".iso", ".jar"
]

# Domínios conhecidos de encurtadores
ENCURTADORES = [
    "bit.ly", "tinyurl.com", "shorte.st", "adf.ly",
    "linkvertise.com", "ouo.io", "bc.vc", "sh.st",
    "cur.lv", "za.gl", "up-4ever.org"
]

def extrair_dominio(url):
    try:
        return urlparse(url).netloc.replace("www.", "")
    except:
        return ""

def verificar_link_direto(url):
    try:
        resposta = requests.head(url, timeout=5, allow_redirects=True)
        content_type = resposta.headers.get("Content-Type", "")
        tipos_arquivo = [
            "application/pdf", "application/zip", "application/x-rar",
            "application/octet-stream", "application/epub+zip",
            "application/x-7z-compressed", "video/mp4", "video/x-matroska"
        ]
        return any(t in content_type for t in tipos_arquivo)
    except:
        return False

def tem_extensao_direta(url):
    url_lower = url.lower().split("?")[0]
    return any(url_lower.endswith(ext) for ext in EXTENSOES_DIRETAS)

def e_encurtador(dominio):
    return any(enc in dominio for enc in ENCURTADORES)

def calcular_score(resultado):
    score = 50
    dominio = resultado["dominio_limpo"]

    if dominio in WHITELIST:
        score += 30
    if resultado["download_direto"]:
        score += 20
    if not resultado["encurtador"]:
        score += 10
    if resultado["download_direto"] and not resultado["encurtador"]:
        score += 10

    return min(score, 100)

@app.get("/buscar")
def buscar(q: str):
    url = "https://serpapi.com/search"

    # Query inteligente focada em download
    query_download = (
        f"{q} download "
        f"site:mediafire.com OR site:mega.nz OR site:drive.google.com OR "
        f"site:archive.org OR site:github.com OR site:sourceforge.net OR "
        f"site:pixeldrain.com OR site:gofile.io OR download OR baixar"
    )

    parametros = {
        "q": query_download,
        "api_key": SERPAPI_KEY,
        "num": 10,
        "hl": "pt",
        "gl": "br"
    }

    resposta = requests.get(url, params=parametros)
    dados = resposta.json()

    resultados = []
    for item in dados.get("organic_results", []):
        link = item.get("link", "")
        dominio_limpo = extrair_dominio(link)

        download_direto = tem_extensao_direta(link)
        encurtador = e_encurtador(dominio_limpo)

        resultado = {
            "titulo": item.get("title", ""),
            "link": link,
            "dominio": item.get("displayed_link", ""),
            "dominio_limpo": dominio_limpo,
            "descricao": item.get("snippet", ""),
            "download_direto": download_direto,
            "encurtador": encurtador,
            "fonte_confiavel": dominio_limpo in WHITELIST,
        }

        resultado["score"] = calcular_score(resultado)
        resultados.append(resultado)

    # Ordena pelo score — melhor primeiro
    resultados.sort(key=lambda x: x["score"], reverse=True)

    return {"resultados": resultados}