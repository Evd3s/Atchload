from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import requests
import os
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed

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
    "github.com", "sourceforge.net", "archive.org", "scholar.archive.org",
    "mediafire.com", "mega.nz", "drive.google.com",
    "pixeldrain.com", "gofile.io", "sendspace.com",
    "itch.io", "workupload.com", "1fichier.com"
]

EXTENSOES_DIRETAS = [
    ".exe", ".zip", ".rar", ".7z", ".tar", ".gz",
    ".pdf", ".epub", ".mobi", ".dmg", ".apk",
    ".mp4", ".mkv", ".avi", ".iso", ".jar", ".mp3"
]

EXTENSOES_PDF = [".pdf"]

ENCURTADORES = [
    "bit.ly", "tinyurl.com", "shorte.st", "adf.ly",
    "linkvertise.com", "ouo.io", "bc.vc", "sh.st"
]

STREAMING = [
    "netflix.com", "disneyplus.com", "primevideo.com",
    "globoplay.globo.com", "telecine.com.br", "spotify.com",
    "deezer.com", "play.google.com", "open.spotify.com",
    "music.youtube.com", "adorocinema.com", "filmow.com",
    "letterboxd.com", "imdb.com", "google.com/store"
]

# Sites bloqueados manualmente
BLOQUEADOS = [
    "play.google.com",
]

AD_SCRIPTS = [
    "googlesyndication.com", "doubleclick.net", "adnxs.com",
    "taboola.com", "outbrain.com", "propellerads.com",
    "popads.net", "adcash.com", "exoclick.com"
]

PALAVRAS_DOWNLOAD = [
    "mega.nz", "mediafire.com", "drive.google.com", "pixeldrain.com",
    "gofile.io", "1fichier.com", "sendspace.com", "workupload.com",
    "download now", "baixar agora", "download here", "clique aqui para baixar",
    "direct download", "download link", "link de download",
    ".zip", ".rar", ".exe", ".mkv", ".mp4", ".iso", ".epub"
]

PALAVRAS_TRAILER = [
    "trailer", "teaser", "behind the scenes", "making of",
    "clip oficial", "featurette"
]

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

def extrair_dominio(url):
    try:
        return urlparse(url).netloc.replace("www.", "")
    except:
        return ""

def e_pdf_url(url):
    return url.lower().split("?")[0].endswith(".pdf") or "/article/" in url.lower()

def tem_extensao_direta(url):
    url_lower = url.lower().split("?")[0]
    return any(url_lower.endswith(ext) for ext in EXTENSOES_DIRETAS)

def e_encurtador(dominio):
    return any(enc in dominio for enc in ENCURTADORES)

def e_streaming(dominio):
    return any(s in dominio for s in STREAMING)

def e_youtube(dominio):
    return "youtube.com" in dominio or "youtu.be" in dominio

def e_bloqueado(dominio, url):
    return any(b in dominio or b in url for b in BLOQUEADOS)

def e_trailer(titulo, descricao):
    texto = (titulo + " " + descricao).lower()
    return any(p in texto for p in PALAVRAS_TRAILER)

def analisar_pagina(url):
    """Busca o HTML e retorna propaganda + tem_download. Timeout curto."""
    try:
        r = requests.get(url, timeout=5, headers=HEADERS)
        html = r.text.lower()
        ads = len([s for s in AD_SCRIPTS if s in html])
        if ads == 0:
            propaganda = "limpo"
        elif ads <= 2:
            propaganda = "moderado"
        else:
            propaganda = "agressivo"
        palavras = [p for p in PALAVRAS_DOWNLOAD if p in html]
        tem_download = len(palavras) >= 2
        return propaganda, tem_download
    except:
        return "desconhecido", False

def verificar_head(url):
    try:
        r = requests.head(url, timeout=4, allow_redirects=True)
        ct = r.headers.get("Content-Type", "")
        tipos = [
            "application/pdf", "application/zip", "application/x-rar",
            "application/octet-stream", "application/epub+zip",
            "video/mp4", "audio/mpeg"
        ]
        return any(t in ct for t in tipos)
    except:
        return False

def calcular_score(r):
    score = 40

    # Fonte confiável sobe bastante
    if r["fonte_confiavel"]:
        score += 25

    # Download direto é o melhor cenário
    if r["download_direto"]:
        score += 25

    # Página tem link de download detectado
    if r["tem_download"] and not r["download_direto"]:
        score += 15

    # Propaganda
    if r["propaganda"] == "limpo":
        score += 8
    elif r["propaganda"] == "moderado":
        score += 2
    elif r["propaganda"] == "agressivo":
        score -= 10

    # Penalidades
    if r["youtube"]:
        score -= 5       # YouTube não é ideal mas pode ter o conteúdo
    if r["streaming"]:
        score -= 30
    if r["trailer"]:
        score -= 25
    if r["pdf_irrelevante"]:
        score -= 30
    if r["encurtador"]:
        score -= 5
    if r["bloqueado"]:
        score -= 50

    return max(0, min(score, 100))

def processar_item(item, query_lower):
    link      = item.get("link", "")
    titulo    = item.get("title", "")
    descricao = item.get("snippet", "")
    dominio   = extrair_dominio(link)

    youtube    = e_youtube(dominio)
    streaming  = e_streaming(dominio) and not youtube
    encurtador = e_encurtador(dominio)
    bloqueado  = e_bloqueado(dominio, link)
    trailer    = e_trailer(titulo, descricao)

    # PDF irrelevante: é PDF mas o usuário não pediu PDF
    pdf_irrelevante = e_pdf_url(link) and "pdf" not in query_lower and "artigo" not in query_lower

    # Download direto pela extensão
    download_direto = tem_extensao_direta(link)

    propaganda    = "desconhecido"
    tem_download  = False

    if not streaming and not youtube and not bloqueado:
        # Tenta HEAD primeiro (rápido)
        if not download_direto:
            download_direto = verificar_head(link)
        # Analisa HTML
        propaganda, tem_download = analisar_pagina(link)
        if download_direto:
            tem_download = True

    resultado = {
        "titulo":          titulo,
        "link":            link,
        "dominio":         item.get("displayed_link", ""),
        "dominio_limpo":   dominio,
        "descricao":       descricao,
        "download_direto": download_direto,
        "tem_download":    tem_download,
        "encurtador":      encurtador,
        "fonte_confiavel": dominio in WHITELIST,
        "youtube":         youtube,
        "streaming":       streaming,
        "trailer":         trailer,
        "pdf_irrelevante": pdf_irrelevante,
        "bloqueado":       bloqueado,
        "propaganda":      propaganda,
    }
    resultado["score"] = calcular_score(resultado)
    return resultado

@app.get("/buscar")
def buscar(q: str):
    query_lower = q.lower()

    queries = [
        f'"{q}" site:drive.google.com OR site:mega.nz OR site:mediafire.com OR site:pixeldrain.com OR site:gofile.io OR site:archive.org OR site:itch.io',
        f'{q} download OR baixar -trailer -teaser -site:spotify.com -site:netflix.com -site:play.google.com'
    ]

    itens_brutos = []
    links_vistos = set()

    for query_str in queries:
        try:
            r = requests.get("https://serpapi.com/search", params={
                "q": query_str,
                "api_key": SERPAPI_KEY,
                "num": 6,
                "hl": "pt",
                "gl": "br"
            })
            dados = r.json()
            for item in dados.get("organic_results", []):
                link = item.get("link", "")
                if link and link not in links_vistos:
                    links_vistos.add(link)
                    itens_brutos.append(item)
        except:
            pass

    # Processa todos em paralelo — muito mais rápido
    resultados = []
    with ThreadPoolExecutor(max_workers=8) as executor:
        futuros = {
            executor.submit(processar_item, item, query_lower): item
            for item in itens_brutos
        }
        for futuro in as_completed(futuros):
            try:
                resultados.append(futuro.result())
            except:
                pass

    resultados.sort(key=lambda x: x["score"], reverse=True)
    return {"resultados": resultados}