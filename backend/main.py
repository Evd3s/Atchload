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
    "archive.org", "mediafire.com", "mega.nz", "drive.google.com",
    "pixeldrain.com", "gofile.io", "sendspace.com", "itch.io",
    "workupload.com", "1fichier.com", "sourceforge.net"
]

# Sites que o usuário pode mencionar explicitamente na busca
SITES_MENCIONAVEIS = {
    "youtube":    ["youtube.com", "youtu.be"],
    "archive":    ["archive.org"],
    "mega":       ["mega.nz"],
    "mediafire":  ["mediafire.com"],
    "drive":      ["drive.google.com"],
    "gdrive":     ["drive.google.com"],
    "github":     ["github.com"],
    "itch":       ["itch.io"],
    "pixeldrain": ["pixeldrain.com"],
    "gofile":     ["gofile.io"],
}

EXTENSOES_DIRETAS = [
    ".exe", ".zip", ".rar", ".7z", ".tar", ".gz",
    ".epub", ".mobi", ".dmg", ".apk",
    ".mp4", ".mkv", ".avi", ".iso", ".jar", ".mp3"
]

EXTENSOES_DOCUMENTO = [".pdf", "_djvu.txt", ".txt", ".djvu"]

ENCURTADORES = [
    "bit.ly", "tinyurl.com", "shorte.st", "adf.ly",
    "linkvertise.com", "ouo.io", "bc.vc", "sh.st"
]

STREAMING = [
    "netflix.com", "disneyplus.com", "primevideo.com",
    "globoplay.globo.com", "telecine.com.br", "spotify.com",
    "deezer.com", "open.spotify.com", "music.youtube.com",
    "adorocinema.com", "filmow.com", "letterboxd.com", "imdb.com"
]

# Studios e sites de filmes que não têm download
STUDIOS_BLOQUEADOS = [
    "disney.com", "movies.disney.com", "pixar.com",
    "warnerbros.com", "universalpictures.com", "sonypictures.com",
    "marvel.com", "starwars.com", "dreamworks.com",
    "paramountpictures.com", "mgm.com", "lionsgatefilms.com"
]

BLOQUEADOS = [
    "play.google.com",
]

# Padrões de URL inúteis — páginas de comentários, perfis, etc.
URL_INUTILS = [
    "/comments", "/discussion", "/reviews", "/forum",
    "/profile", "/user/", "/community", "?after=", "?before=",
    "/blog/", "/news/", "/about", "/contact"
]

AD_SCRIPTS = [
    "googlesyndication.com", "doubleclick.net", "adnxs.com",
    "taboola.com", "outbrain.com", "propellerads.com",
    "popads.net", "adcash.com", "exoclick.com"
]

PALAVRAS_DOWNLOAD_HTML = [
    "mega.nz", "mediafire.com", "drive.google.com", "pixeldrain.com",
    "gofile.io", "1fichier.com", "sendspace.com", "workupload.com",
    "baixar agora", "download here", "clique aqui para baixar",
    "direct download", "download link", "link de download",
    ".zip", ".rar", ".exe", ".mkv", ".mp4", ".iso", ".epub"
]

PALAVRAS_TRAILER   = ["trailer", "teaser", "making of", "featurette"]
PALAVRAS_DOCUMENTO = ["artigo", "article", "research", "journal", "paper", "tese"]

TIPOS_VIDEO = [
    "filme", "movie", "film", "anime", "animação", "animacao",
    "serie", "série", "episodio", "episódio", "temporada",
    "dublado", "legendado", "assistir", "cartoon", "animacao"
]

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}


def extrair_dominio(url):
    try:
        return urlparse(url).netloc.replace("www.", "")
    except:
        return ""

def detectar_site_mencionado(query_lower):
    """Retorna lista de domínios que o usuário mencionou explicitamente."""
    mencionados = []
    for keyword, dominios in SITES_MENCIONAVEIS.items():
        if keyword in query_lower:
            mencionados.extend(dominios)
    return mencionados

def e_url_inutil(url):
    url_lower = url.lower()
    return any(p in url_lower for p in URL_INUTILS)

def e_url_documento(url):
    url_lower = url.lower()
    return any(url_lower.endswith(ext) for ext in EXTENSOES_DOCUMENTO)

def tem_extensao_direta(url, quer_pdf):
    url_lower = url.lower().split("?")[0]
    exts = EXTENSOES_DIRETAS + ([".pdf"] if quer_pdf else [])
    return any(url_lower.endswith(ext) for ext in exts)

def e_encurtador(dominio):
    return any(enc in dominio for enc in ENCURTADORES)

def e_streaming(dominio):
    return any(s in dominio for s in STREAMING)

def e_youtube(dominio):
    return "youtube.com" in dominio or "youtu.be" in dominio

def e_studio(dominio):
    return any(s in dominio for s in STUDIOS_BLOQUEADOS)

def e_bloqueado(dominio, url):
    return any(b in dominio or b in url for b in BLOQUEADOS)

def e_reddit(dominio):
    return "reddit.com" in dominio

def e_github(dominio):
    return "github.com" in dominio

def e_trailer(titulo, descricao, query_lower):
    if "trailer" in query_lower:
        return False
    return any(p in (titulo + " " + descricao).lower() for p in PALAVRAS_TRAILER)

def e_documento_irrelevante(titulo, descricao, url, query_lower):
    if any(p in query_lower for p in ["pdf", "artigo", "paper", "epub", "livro", "ebook", "manga", "mangá"]):
        return False
    texto = (titulo + " " + descricao + " " + url).lower()
    return e_url_documento(url) or any(p in texto for p in PALAVRAS_DOCUMENTO)

def quer_video(query_lower):
    return any(p in query_lower for p in TIPOS_VIDEO)

def contar_relevancia(query, texto):
    # Remove palavras de site da query para não contar "youtube" como palavra de conteúdo
    stop = list(SITES_MENCIONAVEIS.keys()) + ["download", "baixar", "filme", "anime", "game", "jogo"]
    palavras = [p for p in query.lower().split() if len(p) > 2 and p not in stop]
    if not palavras:
        # Se só tinha stop words, usa todas
        palavras = [p for p in query.lower().split() if len(p) > 2]
    if not palavras:
        return 0
    texto_lower = texto.lower()
    encontradas = sum(1 for p in palavras if p in texto_lower)
    return encontradas / len(palavras)

def verificar_head(url):
    try:
        r = requests.head(url, timeout=4, allow_redirects=True)
        ct = r.headers.get("Content-Type", "")
        tipos = [
            "application/zip", "application/x-rar",
            "application/octet-stream", "application/epub+zip",
            "application/x-7z-compressed", "video/mp4", "audio/mpeg"
        ]
        return any(t in ct for t in tipos)
    except:
        return False

def analisar_pagina(url, e_reddit_url=False):
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

        palavras = [p for p in PALAVRAS_DOWNLOAD_HTML if p in html]
        tem_download = len(palavras) >= 2

        reddit_tem_link = False
        if e_reddit_url:
            dominios_dl = ["mega.nz", "mediafire.com", "drive.google.com",
                           "pixeldrain.com", "gofile.io", "1fichier.com"]
            reddit_tem_link = any(d in html for d in dominios_dl)

        return propaganda, tem_download, reddit_tem_link
    except:
        return "desconhecido", False, False

def calcular_score(r, query, query_lower, sites_mencionados, busca_video):
    score = 30

    titulo_desc = r["titulo"] + " " + r["descricao"]
    relevancia  = contar_relevancia(query, titulo_desc)

    # Relevância é o fator principal
    score += int(relevancia * 35)

    # ── BOOST por site mencionado explicitamente ──
    # Se o usuário pediu um site específico, esse site vai ao topo
    if sites_mencionados and r["dominio_limpo"] in sites_mencionados:
        score += 40   # boost forte — usuário pediu esse site
    elif sites_mencionados:
        score -= 10   # outros sites caem um pouco quando um foi pedido

    # Fonte confiável (whitelist) — só conta se não for busca de vídeo no github
    if r["fonte_confiavel"]:
        score += 15

    # Download direto
    if r["download_direto"]:
        score += 20

    # Propaganda
    if r["propaganda"] == "limpo":
        score += 5
    elif r["propaganda"] == "agressivo":
        score -= 8

    # YouTube
    if r["youtube"]:
        if "youtube" in sites_mencionados or "youtu.be" in sites_mencionados:
            pass  # já ganhou o boost de 40 acima
        elif relevancia >= 0.5:
            score += 12   # tem o conteúdo certo
        else:
            score -= 5

    # Reddit
    if r["reddit"]:
        if r["reddit_tem_link"]:
            score += 5
        else:
            score -= 25

    # GitHub para vídeo não faz sentido
    if r["github_video"]:
        score -= 30

    # Studio — site de estúdio não tem download
    if r["studio"]:
        score -= 40

    # URL inútil (comentários, perfis)
    if r["url_inutil"]:
        score -= 40

    # Penalidades gerais
    if r["streaming"]:   score -= 25
    if r["trailer"]:     score -= 20
    if r["documento"]:   score -= 30
    if r["encurtador"]:  score -= 5
    if r["bloqueado"]:   score  = 0

    return max(0, min(score, 100))

def processar_item(item, query, query_lower, quer_pdf, busca_video, sites_mencionados):
    link      = item.get("link", "")
    titulo    = item.get("title", "")
    descricao = item.get("snippet", "")
    dominio   = extrair_dominio(link)

    youtube    = e_youtube(dominio)
    streaming  = e_streaming(dominio) and not youtube
    encurtador = e_encurtador(dominio)
    bloqueado  = e_bloqueado(dominio, link)
    studio     = e_studio(dominio)
    trailer    = e_trailer(titulo, descricao, query_lower)
    documento  = e_documento_irrelevante(titulo, descricao, link, query_lower)
    reddit     = e_reddit(dominio)
    github     = e_github(dominio)
    github_video = github and busca_video
    url_inutil = e_url_inutil(link)

    download_direto = tem_extensao_direta(link, quer_pdf)
    propaganda      = "desconhecido"
    reddit_tem_link = False

    # Não analisa páginas inúteis, studios ou bloqueados
    if not streaming and not youtube and not bloqueado and not studio and not url_inutil:
        if not download_direto:
            download_direto = verificar_head(link)
        propaganda, _, reddit_tem_link = analisar_pagina(link, e_reddit_url=reddit)

    resultado = {
        "titulo":          titulo,
        "link":            link,
        "dominio":         item.get("displayed_link", ""),
        "dominio_limpo":   dominio,
        "descricao":       descricao,
        "download_direto": download_direto,
        "encurtador":      encurtador,
        "fonte_confiavel": dominio in WHITELIST and not github_video,
        "youtube":         youtube,
        "streaming":       streaming,
        "trailer":         trailer,
        "documento":       documento,
        "bloqueado":       bloqueado or studio,
        "reddit":          reddit,
        "reddit_tem_link": reddit_tem_link,
        "github_video":    github_video,
        "url_inutil":      url_inutil,
        "studio":          studio,
        "propaganda":      propaganda,
    }

    resultado["score"] = calcular_score(resultado, query, query_lower, sites_mencionados, busca_video)
    return resultado

@app.get("/buscar")
def buscar(q: str):
    query_lower      = q.lower()
    quer_pdf         = "pdf" in query_lower
    busca_video      = quer_video(query_lower)
    sites_mencionados = detectar_site_mencionado(query_lower)

    # Monta exclusões para busca geral
    excluir = (
        "-site:spotify.com -site:netflix.com -site:play.google.com "
        "-site:disney.com -site:pixar.com -site:imdb.com "
        "-site:adorocinema.com -site:filmow.com"
    )

    queries = [
        # Sites de hospedagem diretos
        (
            f'"{q}" site:drive.google.com OR site:mega.nz OR site:mediafire.com '
            f'OR site:pixeldrain.com OR site:gofile.io OR site:archive.org OR site:itch.io'
        ),
        # X: pessoas compartilham links
        f'"{q}" download OR baixar site:x.com',
        # Busca geral sem ruído
        f'{q} download OR baixar {excluir}',
    ]

    # Se o usuário pediu um site específico, adiciona uma busca direcionada
    if sites_mencionados:
        site_query = " OR ".join(f"site:{s}" for s in sites_mencionados)
        queries.insert(0, f'"{q}" {site_query}')

    itens_brutos = []
    links_vistos = set()

    for query_str in queries:
        try:
            r = requests.get("https://serpapi.com/search", params={
                "q":       query_str,
                "api_key": SERPAPI_KEY,
                "num":     5,
                "hl":      "pt",
                "gl":      "br"
            })
            for item in r.json().get("organic_results", []):
                link = item.get("link", "")
                if link and link not in links_vistos:
                    links_vistos.add(link)
                    itens_brutos.append(item)
        except:
            pass

    resultados = []
    with ThreadPoolExecutor(max_workers=8) as executor:
        futuros = {
            executor.submit(
                processar_item, item, q, query_lower, quer_pdf, busca_video, sites_mencionados
            ): item
            for item in itens_brutos
        }
        for futuro in as_completed(futuros):
            try:
                res = futuro.result()
                if not res["bloqueado"]:
                    resultados.append(res)
            except:
                pass

    resultados.sort(key=lambda x: x["score"], reverse=True)
    return {"resultados": resultados}