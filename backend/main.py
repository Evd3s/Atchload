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

WHITELIST = [
    "github.com", "sourceforge.net", "archive.org",
    "mediafire.com", "mega.nz", "drive.google.com",
    "1fichier.com", "pixeldrain.com", "gofile.io",
    "sendspace.com", "itch.io", "fitgirl-repacks.site",
    "uploadhaven.com", "workupload.com", "bayfiles.com"
]

EXTENSOES_DIRETAS = [
    ".exe", ".zip", ".rar", ".7z", ".tar", ".gz",
    ".pdf", ".epub", ".mobi", ".dmg", ".apk",
    ".mp4", ".mkv", ".avi", ".iso", ".jar", ".mp3"
]

ENCURTADORES = [
    "bit.ly", "tinyurl.com", "shorte.st", "adf.ly",
    "linkvertise.com", "ouo.io", "bc.vc", "sh.st"
]

STREAMING = [
    "youtube.com", "youtu.be", "netflix.com", "disneyplus.com",
    "primevideo.com", "globoplay.globo.com", "telecine.com.br",
    "spotify.com", "deezer.com", "play.google.com",
    "open.spotify.com", "music.youtube.com", "adorocinema.com",
    "filmow.com", "letterboxd.com", "imdb.com", "telecine.com.br"
]

AD_SCRIPTS = [
    "googlesyndication.com", "doubleclick.net", "adnxs.com",
    "taboola.com", "outbrain.com", "propellerads.com",
    "popads.net", "adcash.com", "exoclick.com"
]

# Palavras no HTML que indicam presença de download real
PALAVRAS_DOWNLOAD = [
    "mega.nz", "mediafire.com", "drive.google.com", "pixeldrain.com",
    "gofile.io", "1fichier.com", "sendspace.com", "workupload.com",
    "download now", "baixar agora", "download here", "clique aqui para baixar",
    "direct download", "download link", "link de download", "gdrive",
    ".zip", ".rar", ".exe", ".mkv", ".mp4", ".iso", ".epub"
]

def extrair_dominio(url):
    try:
        return urlparse(url).netloc.replace("www.", "")
    except:
        return ""

def tem_extensao_direta(url):
    url_lower = url.lower().split("?")[0]
    return any(url_lower.endswith(ext) for ext in EXTENSOES_DIRETAS)

def verificar_link_direto_head(url):
    try:
        r = requests.head(url, timeout=4, allow_redirects=True)
        ct = r.headers.get("Content-Type", "")
        tipos = [
            "application/pdf", "application/zip", "application/x-rar",
            "application/octet-stream", "application/epub+zip",
            "application/x-7z-compressed", "video/mp4", "audio/mpeg"
        ]
        return any(t in ct for t in tipos)
    except:
        return False

def verificar_download_na_pagina(url):
    """Acessa a página e verifica se tem link de download real dentro dela."""
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        r = requests.get(url, timeout=6, headers=headers)
        html = r.text.lower()
        encontrados = [p for p in PALAVRAS_DOWNLOAD if p in html]
        return len(encontrados) >= 2
    except:
        return False

def analisar_propagandas(html):
    if not html:
        return "desconhecido"
    encontrados = [s for s in AD_SCRIPTS if s in html]
    qtd = len(encontrados)
    if qtd == 0:
        return "limpo"
    elif qtd <= 2:
        return "moderado"
    else:
        return "agressivo"

def e_encurtador(dominio):
    return any(enc in dominio for enc in ENCURTADORES)

def e_streaming(dominio):
    return any(s in dominio for s in STREAMING)

def e_youtube(dominio):
    return "youtube.com" in dominio or "youtu.be" in dominio

def buscar_html(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        r = requests.get(url, timeout=6, headers=headers)
        return r.text.lower()
    except:
        return ""

def calcular_score(r):
    score = 40
    if r["fonte_confiavel"]:   score += 30
    if r["download_direto"]:   score += 25
    if r["tem_download"]:      score += 20
    if not r["encurtador"]:    score += 5
    if r["propaganda"] == "limpo":      score += 10
    elif r["propaganda"] == "moderado": score += 3
    elif r["propaganda"] == "agressivo": score -= 10
    if r["youtube"]:   score -= 15
    if r["streaming"]: score -= 25
    return max(0, min(score, 100))

@app.get("/buscar")
def buscar(q: str):
    # Query principal focada em downloads reais
    queries = [
        # Busca em sites de hospedagem conhecidos
        f'"{q}" site:drive.google.com OR site:mega.nz OR site:mediafire.com OR site:pixeldrain.com OR site:gofile.io OR site:archive.org',
        # Busca geral com termos de download
        f'{q} download OR baixar OR "direct download" OR "link de download"'
    ]

    todos_resultados = []
    links_vistos = set()

    for query_str in queries:
        parametros = {
            "q": query_str,
            "api_key": SERPAPI_KEY,
            "num": 5,
            "hl": "pt",
            "gl": "br"
        }
        resposta = requests.get("https://serpapi.com/search", params=parametros)
        dados = resposta.json()

        for item in dados.get("organic_results", []):
            link = item.get("link", "")
            if link in links_vistos:
                continue
            links_vistos.add(link)

            dominio_limpo = extrair_dominio(link)
            youtube   = e_youtube(dominio_limpo)
            streaming = e_streaming(dominio_limpo) and not youtube
            encurtador = e_encurtador(dominio_limpo)

            # Download direto pela extensão (rápido)
            download_direto = tem_extensao_direta(link)

            # Se não achou pela extensão e não é streaming, tenta HEAD
            if not download_direto and not streaming and not youtube:
                download_direto = verificar_link_direto_head(link)

            # Busca o HTML uma vez e reutiliza para propaganda e detecção de download
            html = ""
            tem_download = False
            propaganda = "desconhecido"

            if not streaming and not youtube:
                html = buscar_html(link)
                propaganda = analisar_propagandas(html)
                if not download_direto:
                    palavras = [p for p in PALAVRAS_DOWNLOAD if p in html]
                    tem_download = len(palavras) >= 2
                else:
                    tem_download = True

            resultado = {
                "titulo":          item.get("title", ""),
                "link":            link,
                "dominio":         item.get("displayed_link", ""),
                "dominio_limpo":   dominio_limpo,
                "descricao":       item.get("snippet", ""),
                "download_direto": download_direto,
                "tem_download":    tem_download,
                "encurtador":      encurtador,
                "fonte_confiavel": dominio_limpo in WHITELIST,
                "youtube":         youtube,
                "streaming":       streaming,
                "propaganda":      propaganda,
            }

            resultado["score"] = calcular_score(resultado)
            todos_resultados.append(resultado)

    todos_resultados.sort(key=lambda x: x["score"], reverse=True)
    return {"resultados": todos_resultados}