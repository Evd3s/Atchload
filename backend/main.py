from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv
from urllib.parse import urlparse, quote
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict
import requests, os, re, unicodedata, sqlite3, base64
from datetime import datetime

load_dotenv()
SERPAPI_KEY = os.getenv("SERPAPI_KEY")
VIRUSTOTAL_API_KEY = os.getenv("VIRUSTOTAL_API_KEY")
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
NOME_BANCO = os.path.join(BASE_DIR, "atchload_seguranca.db")

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


# ──────────────────────────────────────────────
# Segurança: cache local + VirusTotal
# Mantém a busca rápida: /buscar só usa cache. A API do VT só é chamada
# quando o usuário clica em "Verificar segurança" no frontend.
# ──────────────────────────────────────────────
def inicializar_banco():
    conexao = sqlite3.connect(NOME_BANCO)
    cursor = conexao.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS historico_seguranca (
        alvo TEXT PRIMARY KEY,
        tag_atchload TEXT,
        hash_arquivo TEXT,
        malicious INTEGER DEFAULT 0,
        suspicious INTEGER DEFAULT 0,
        data_consulta TEXT
    )
    """)
    conexao.commit()
    conexao.close()

def buscar_cache_local(alvo: str):
    try:
        conexao = sqlite3.connect(NOME_BANCO)
        cursor = conexao.cursor()
        cursor.execute(
            "SELECT tag_atchload, hash_arquivo, malicious, suspicious, data_consulta FROM historico_seguranca WHERE alvo = ?",
            (alvo,)
        )
        res = cursor.fetchone()
        conexao.close()
        if not res:
            return None
        return {
            "tag": res[0] or "Aguardando Análise",
            "hash": res[1] or None,
            "malicious": int(res[2] or 0),
            "suspicious": int(res[3] or 0),
            "data_consulta": res[4]
        }
    except Exception:
        return None

def salvar_no_banco(alvo: str, tag: str, hash_arq: str | None, malicious: int, suspicious: int):
    conexao = sqlite3.connect(NOME_BANCO)
    cursor = conexao.cursor()
    data_atual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
        INSERT OR REPLACE INTO historico_seguranca
        (alvo, tag_atchload, hash_arquivo, malicious, suspicious, data_consulta)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (alvo, tag, hash_arq or "", int(malicious or 0), int(suspicious or 0), data_atual))
    conexao.commit()
    conexao.close()

def gerar_id_url_virustotal(url: str) -> str:
    return base64.urlsafe_b64encode(url.encode("utf-8")).decode("utf-8").strip("=")

def calcular_tag_atchload(malicious: int, suspicious: int) -> str:
    if malicious >= 3:
        return "Perigoso"
    if malicious >= 1 or suspicious > 2:
        return "Alerta de Cuidado"
    return "Seguro / Confiável"

def penalidade_seguranca(tag: str) -> int:
    if tag == "Perigoso":
        return -80
    if tag == "Alerta de Cuidado":
        return -22
    if tag == "Seguro / Confiável":
        return 3
    return 0

inicializar_banco()

# ──────────────────────────────────────────────
# Domínios por categoria. A ideia aqui NÃO é decidir resultado na mão,
# e sim classificar o que o Google/SerpAPI devolver.
# ──────────────────────────────────────────────
HOSTS_ARQUIVO = [
    "archive.org", "mediafire.com", "mega.nz", "drive.google.com", "pixeldrain.com", "gofile.io",
    "sendspace.com", "workupload.com", "1fichier.com", "sourceforge.net", "github.com", "itch.io"
]
HOSTS_DIRETOS = [
    "archive.org", "pixeldrain.com", "gofile.io", "sourceforge.net", "github.com", "mediafire.com",
    "1fichier.com", "sendspace.com", "workupload.com", "itch.io"
]
# Drive só entra em HOSTS_DIRETOS quando for arquivo individual (tratado em drive_arquivo_link)
# Mega.nz não entra em HOSTS_DIRETOS pois não expõe download direto por HEAD request
GAME_STORES = [
    "store.steampowered.com", "steampowered.com", "store.epicgames.com", "epicgames.com", "gog.com",
    "itch.io", "xbox.com", "playstation.com", "nintendo.com", "microsoft.com", "humblebundle.com"
]
SOFTWARE_OFICIAL = [
    "microsoft.com", "visualstudio.microsoft.com", "code.visualstudio.com", "github.com", "sourceforge.net",
    "videolan.org", "blender.org", "gimp.org", "python.org", "java.com", "oracle.com", "audacityteam.org",
    "obsproject.com", "mozilla.org", "google.com", "7-zip.org", "libreoffice.org", "rarlab.com", "win-rar.com"
]
STREAMING_LEGAL = [
    "youtube.com", "youtu.be", "primevideo.com", "amazon.com", "disneyplus.com", "netflix.com", "globoplay.globo.com",
    "telecine.com.br", "max.com", "hbomax.com", "paramountplus.com", "crunchyroll.com", "apple.com"
]
SOCIAL_LINK = ["x.com", "twitter.com", "reddit.com"]
SOCIAL_RUIDO = ["tiktok.com", "instagram.com", "facebook.com", "threads.net", "kwai.com"]
ENCURTADORES = ["bit.ly", "tinyurl.com", "shorte.st", "adf.ly", "linkvertise.com", "ouo.io", "bc.vc", "sh.st", "cutt.ly", "is.gd", "shrinke.me"]

# Bloqueio forte: quase nunca ajuda em buscador de download/visualização.
BLOQUEADOS_GERAIS = [
    "wikipedia.org", "wikimedia.org", "imdb.com", "adorocinema.com", "filmow.com", "letterboxd.com",
    "rottentomatoes.com", "themoviedb.org", "metacritic.com", "ucicinemas.com.br", "ingresso.com",
    "cinemark.com.br", "cinepolis.com.br", "moviecom.com.br", "movies.disney.com", "disney.com", "pixar.com",
    "marvel.com", "warnerbros.com", "universalpictures.com", "sonypictures.com", "dreamworks.com",
    "paramountpictures.com", "lionsgate.com", "apps.apple.com", "play.google.com"
]
ACADEMICOS = [
    "scholar.archive.org", "scielo.br", "scielo.org", "doi.org", "researchgate.net", "academia.edu",
    "semanticscholar.org", "springer.com", "tandfonline.com", "jstor.org", "periodicos", "revistas"
]

EXTS = [".exe", ".msi", ".zip", ".rar", ".7z", ".tar", ".gz", ".epub", ".mobi", ".pdf", ".dmg", ".apk", ".iso", ".jar", ".mp4", ".mkv", ".avi", ".mov", ".mp3", ".flac", ".wav", ".cbz", ".cbr"]
EXTS_PERIGOSAS = [".bat", ".cmd", ".scr", ".vbs", ".ps1"]

MEDIA_WORDS = ["filme", "movie", "film", "anime", "animacao", "animação", "serie", "série", "episodio", "episódio", "temporada", "dublado", "legendado", "assistir", "cartoon", "desenho"]
GAME_WORDS = ["jogo", "game", "games", "steam", "pc game", "nintendo", "playstation", "xbox", "switch", "rom", "iso", "emulador", "emulator"]
SOFTWARE_WORDS = ["programa", "software", "app", "aplicativo", "ide", "editor", "studio", "vscode", "visual studio", "windows", "linux", "mac", "installer", "setup"]
DOWNLOAD_WORDS = ["download", "baixar", "instalar", "installer", "setup", "apk", "mod", "mods", "rom", "iso"]
DOC_WORDS = ["pdf", "livro", "ebook", "epub", "manga", "mangá", "quadrinho", "hq"]
TRAILER_WORDS = ["trailer", "teaser", "making of", "featurette", "clipe oficial"]
CINEMA_WORDS = ["ingresso", "sessões", "sessoes", "cinema", "estreia", "em cartaz"]
ARTIGO_WORDS = ["artigo", "paper", "pesquisa", "journal", "tese", "dissertação", "resumo", "abstract", "scielo", "scholar", "doi"]
LINK_WORDS = ["mega.nz", "mediafire.com", "drive.google.com", "pixeldrain.com", "gofile.io", "1fichier.com", "sendspace.com", "workupload.com", "archive.org/download", "archive.org/details", "sourceforge.net", "github.com", "baixar", "download", "link", "pasta", "arquivo", ".zip", ".rar", ".7z", ".pdf", ".mp4", ".mkv", ".iso", ".epub"]
AD_SCRIPTS = ["googlesyndication.com", "doubleclick.net", "googleadservices.com", "adnxs.com", "taboola.com", "outbrain.com", "propellerads.com", "popads.net", "adcash.com", "exoclick.com", "onclickads.net", "adsterra.com", "mgid.com"]

STOP = {
    "download", "baixar", "filme", "movie", "film", "jogo", "game", "anime", "serie", "série", "episodio",
    "episódio", "temporada", "dublado", "legendado", "assistir", "online", "completo", "completa", "gratis",
    "grátis", "site", "oficial", "youtube", "drive", "google", "mega", "mediafire", "archive", "reddit", "twitter", "x"
}

SITES_MENCIONAVEIS = {
    "youtube": ["youtube.com", "youtu.be"], "youtu": ["youtube.com", "youtu.be"],
    "archive": ["archive.org"], "internet archive": ["archive.org"],
    "mega": ["mega.nz"], "mediafire": ["mediafire.com"], "drive": ["drive.google.com"],
    "gdrive": ["drive.google.com"], "google drive": ["drive.google.com"],
    "github": ["github.com"], "itch": ["itch.io"], "pixeldrain": ["pixeldrain.com"],
    "gofile": ["gofile.io"], "reddit": ["reddit.com"], "twitter": ["x.com", "twitter.com"], "x": ["x.com", "twitter.com"],
    "steam": ["store.steampowered.com", "steampowered.com"], "epic": ["store.epicgames.com", "epicgames.com"],
    "gog": ["gog.com"], "nintendo": ["nintendo.com"], "xbox": ["xbox.com"], "playstation": ["playstation.com"],
    "prime video": ["primevideo.com", "amazon.com"], "netflix": ["netflix.com"], "disney plus": ["disneyplus.com"],
}

# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────
def norm(t):
    t = unicodedata.normalize("NFD", t or "")
    return "".join(c for c in t if unicodedata.category(c) != "Mn").lower()

def dominio(url):
    try:
        return urlparse(url).netloc.lower().replace("www.", "")
    except Exception:
        return ""

def path(url):
    try:
        return urlparse(url).path.lower()
    except Exception:
        return ""

def bate(dom, lista):
    dom = (dom or "").lower()
    return any(dom == d or dom.endswith("." + d) for d in lista)

def palavra(texto, p):
    return re.search(r"\b" + re.escape(norm(p)) + r"\b", norm(texto)) is not None

def tem_alguma(texto, lista):
    tx = norm(texto)
    return any(norm(w) in tx for w in lista)

def tokens(q):
    ps = re.findall(r"[a-z0-9]+", norm(q))
    bons = [p for p in ps if len(p) > 2 and p not in STOP]
    return bons or [p for p in ps if len(p) > 2]

def relevancia(q, texto):
    ts = tokens(q)
    if not ts:
        return 0
    tx = norm(texto)
    return sum(1 for t in ts if t in tx) / len(ts)

def intencao(q):
    qn = norm(q)
    if tem_alguma(qn, DOC_WORDS): return "documento"
    if tem_alguma(qn, MEDIA_WORDS): return "media"
    if tem_alguma(qn, GAME_WORDS): return "jogo"
    if tem_alguma(qn, SOFTWARE_WORDS): return "software"
    if tem_alguma(qn, DOWNLOAD_WORDS): return "download"
    return "geral"

def sites_pedidos(q):
    qn, out = norm(q), []
    for k, ds in SITES_MENCIONAVEIS.items():
        if palavra(qn, k):
            out += ds
    return sorted(set(out))

def pede_antigo(q):
    qn = norm(q)
    return any(w in qn for w in ["antigo", "antiga", "classico", "classica", "original", "anos 60", "anos 70", "anos 80", "anos 90", "old", "retro"])

def tem_versao_ano(q):
    qn = norm(q)
    return bool(re.search(r"\b(19\d{2}|20\d{2}|v\d+|\d+\.\d+|2008|2010|2013|2019|2022)\b", qn))

def pede_trailer(q):
    qn = norm(q)
    return "trailer" in qn or "teaser" in qn

def tem_ext(url):
    p = path(url).split("?")[0]
    return any(p.endswith(e) for e in EXTS)

def ext_perigosa(url):
    p = path(url).split("?")[0]
    return any(p.endswith(e) for e in EXTS_PERIGOSAS)

def drive_pasta(url):
    """
    Retorna True SOMENTE para links de PASTA do Drive (não baixáveis diretamente).
    Links de ARQUIVO (/file/d/...) são permitidos — o usuário pode abrir e baixar.
    """
    u = url.lower()
    if "drive.google.com" not in u:
        return False
    if "/folders/" in u:
        return True  # pasta — bloqueia
    if "/file/" in u:
        return False  # arquivo individual — permite
    # Outros formatos do Drive sem /file/ e sem /folders/ — trata como pasta por segurança
    return True

def archive_details(url): return "archive.org/details/" in url.lower()
def archive_download(url): return "archive.org/download/" in url.lower()

def archive_id(url):
    p = urlparse(url).path
    if "/details/" in p: return p.split("/details/", 1)[1].split("/")[0]
    if "/download/" in p: return p.split("/download/", 1)[1].split("/")[0]
    return None

def ads_e_links(url):
    try:
        r = requests.get(url, timeout=5, headers=HEADERS)
        html = norm(r.text[:250000])
        ads = sum(1 for s in AD_SCRIPTS if s in html)
        prop = "limpo" if ads == 0 else "moderado" if ads <= 2 else "agressivo"
        return prop, any(norm(w) in html for w in LINK_WORDS)
    except Exception:
        return "desconhecido", False

def github_existe(url):
    """
    Retorna False se o repositório do GitHub retornar 404.
    Só faz a requisição se a URL parecer um repositório específico
    (tem pelo menos /user/repo no caminho).
    """
    try:
        p = urlparse(url).path.strip("/")
        partes = [x for x in p.split("/") if x]
        # Se não tiver pelo menos user/repo, confia sem verificar
        if len(partes) < 2:
            return True
        r = requests.head(url, timeout=4, allow_redirects=True, headers=HEADERS)
        return r.status_code != 404
    except Exception:
        return True  # em caso de erro de rede, não penaliza

def head_arquivo(url):
    if drive_pasta(url): return False
    if tem_ext(url): return True
    try:
        r = requests.head(url, timeout=5, allow_redirects=True, headers=HEADERS)
        ct = (r.headers.get("Content-Type") or "").lower()
        cd = (r.headers.get("Content-Disposition") or "").lower()
        tipos = ["application/zip", "application/x-rar", "application/x-7z-compressed", "application/octet-stream", "application/pdf", "application/epub+zip", "application/x-msdownload", "application/vnd.android.package-archive", "video/", "audio/"]
        return "attachment" in cd or "filename=" in cd or any(t in ct for t in tipos)
    except Exception:
        return False

def arquivo_archive(url, q):
    ident = archive_id(url)
    if not ident: return None
    try:
        data = requests.get(f"https://archive.org/metadata/{ident}", timeout=7, headers=HEADERS).json()
        cand, ts = [], tokens(q)
        for f in data.get("files", []):
            name = f.get("name", "")
            low = name.lower()
            if not name or not any(low.endswith(e) for e in EXTS): continue
            if any(x in low for x in ["_meta", "_files.xml", "_thumb", "torrent"]): continue
            size = int(f.get("size") or 0)
            sc = 20 + (15 if size > 5_000_000 else 0) + sum(5 for t in ts if t in norm(name))
            cand.append((sc, name))
        if not cand: return None
        cand.sort(reverse=True)
        return f"https://archive.org/download/{ident}/{quote(cand[0][1])}"
    except Exception:
        return None

def drive_arquivo_link(url):
    """Retorna True se for link direto para um arquivo no Google Drive (/file/d/...)."""
    u = url.lower()
    return "drive.google.com" in u and "/file/" in u

def download_url(link, dom, q):
    if not link.startswith("http") or ext_perigosa(link): return None
    if archive_details(link): return arquivo_archive(link, q)
    if archive_download(link) and head_arquivo(link): return link
    # Drive: pasta bloqueia, arquivo individual mantém o link para o usuário abrir
    if "drive.google.com" in dom:
        if drive_arquivo_link(link):
            return link  # retorna o link do Drive — usuário abre e baixa lá
        return None  # pasta — não tem download direto
    if bate(dom, SOCIAL_LINK) or bate(dom, SOCIAL_RUIDO): return None
    if (bate(dom, HOSTS_DIRETOS) or tem_ext(link)) and head_arquivo(link): return link
    return None

def parece_oficial_generico(q, dom, texto):
    # Não depende de lista por título. Usa domínio confiável + sinais de oficialidade/relevância.
    if not bate(dom, SOFTWARE_OFICIAL + GAME_STORES + STREAMING_LEGAL):
        return False
    rel = relevancia(q, texto)
    compacto = "".join(tokens(q))
    dom_norm = norm(dom).replace(".", "")
    sinais = tem_alguma(texto, ["official", "oficial", "download", "downloads", "store", "loja", "comprar", "play", "windows", "pc"])
    return rel >= 0.34 or (compacto and compacto in dom_norm) or sinais

def documento_irrelevante(dom, texto, inten):
    if inten == "documento":
        return False
    tx = norm(texto)
    if bate(dom, ACADEMICOS):
        return True
    if any(w in tx for w in ["scholar", "scielo", "doi", "artigo", "paper", "resumo", "journal"]):
        return True
    # PDF é ruído para qualquer busca que não seja documento.
    # Inclui "geral" — um PDF do Archive com menção casual ao nome pesquisado não deve rankear alto.
    if inten in ["media", "jogo", "software", "geral", "download"] and (".pdf" in tx or "/pdf" in tx or "_djvu" in tx):
        return True
    # URL de texto/djvu do Archive é quase sempre conteúdo acadêmico ou livro antigo — bloqueia.
    lnk = norm(dom + texto)
    if "archive.org" in lnk and any(x in lnk for x in ["_djvu.txt", "magazine", "journal", "dragon_magazine"]):
        return True
    return False

# ──────────────────────────────────────────────
# Classificação + score
# ──────────────────────────────────────────────
def classificar(item, q, inten, pedidos):
    link = item.get("link", "") or ""
    tit = item.get("title", "") or ""
    desc = item.get("snippet", "") or ""
    disp = item.get("displayed_link", "") or ""
    dom = dominio(link)
    texto = f"{tit} {desc} {link} {disp}"
    tx = norm(texto)

    yt = bate(dom, ["youtube.com", "youtu.be"])
    streaming = bate(dom, STREAMING_LEGAL) and not yt
    social = bate(dom, SOCIAL_LINK)
    social_ruido = bate(dom, SOCIAL_RUIDO)
    host = bate(dom, HOSTS_ARQUIVO)
    game_store = bate(dom, GAME_STORES)

    # GitHub com 404 não deve receber bônus de hospedagem.
    github_ok = True
    if bate(dom, ["github.com"]):
        github_ok = github_existe(link)
        if not github_ok:
            host = False  # tira o bônus de host

    oficial = parece_oficial_generico(q, dom, texto) or game_store
    bloqueado = bate(dom, BLOQUEADOS_GERAIS)
    encurtador = bate(dom, ENCURTADORES)
    trailer = tem_alguma(texto, TRAILER_WORDS) and not pede_trailer(q)
    cinema = tem_alguma(texto, CINEMA_WORDS)
    doc_ruim = documento_irrelevante(dom, texto, inten)

    antigo = pede_antigo(q)
    old_ok = antigo and any(w in tx for w in ["1967", "classico", "classic", "antigo", "original"])
    old_bad = antigo and any(w in tx for w in ["2016", "2018", "2019", "live action", "novo", "remake"])

    prop, link_pagina = "desconhecido", False
    # Evita gastar request em página ruim/irrelevante.
    if not (bloqueado or yt or encurtador or trailer or cinema or doc_ruim) and (social or host or oficial or game_store or streaming):
        prop, link_pagina = ads_e_links(link)

    link_texto = any(norm(w) in tx for w in LINK_WORDS)
    util = link_texto or link_pagina
    durl = download_url(link, dom, q)

    tipo = "geral"
    if oficial and game_store: tipo = "loja_jogo"
    elif oficial: tipo = "oficial"
    elif durl: tipo = "download_direto"
    elif host: tipo = "hospedagem"
    elif social and util: tipo = "social_com_link"
    elif yt: tipo = "youtube"
    elif streaming: tipo = "streaming"
    elif social_ruido: tipo = "social_ruido"

    cache_seg = buscar_cache_local(link)
    tag_seg = cache_seg["tag"] if cache_seg else "Aguardando Análise"

    return {
        "titulo": tit, "descricao": desc, "link": link, "dominio": disp or dom, "dominio_limpo": dom,
        "tipo": tipo, "relevancia": relevancia(q, texto),
        "download_direto": bool(durl), "download_url": durl,
        "fonte_confiavel": host or oficial or game_store,
        "oficial": oficial, "loja_jogo": game_store,
        "youtube": yt, "streaming": streaming,
        "social_link": social, "social_compartilhamento": social and util,
        "social_ruido": social_ruido,
        "host_bom": host, "tem_link_util": util, "tem_download_na_pagina": util and not bool(durl),
        "github_404": bate(dom, ["github.com"]) and not github_ok,
        "encurtador": encurtador, "bloqueado": bloqueado, "trailer": trailer,
        "cinema": cinema, "documento_irrelevante": doc_ruim,
        "catalogo": bloqueado or doc_ruim,
        "sinal_antigo": old_ok, "sinal_novo": old_bad,
        "propaganda": prop,
        "tag_atchload": tag_seg,
        "hash": cache_seg["hash"] if cache_seg else None,
        "malicious": cache_seg["malicious"] if cache_seg else 0,
        "suspicious": cache_seg["suspicious"] if cache_seg else 0,
        "score": 0, "motivos": []
    }

def teto(score, r, inten, site_pedido, q):
    if r["bloqueado"] or r["cinema"] or r["trailer"] or r["documento_irrelevante"]:
        return 0
    if r.get("github_404"): return min(score, 10)
    if r["encurtador"]: return min(score, 35)

    # Loja de jogo: sempre piso alto, independente da intenção detectada.
    # O usuário pode não ter escrito "jogo" mas pesquisou o nome de um jogo.
    if r["loja_jogo"]:
        return min(max(score, 84), 96)

    # Oficial: piso alto para software/jogo/geral.
    if r["oficial"]:
        return min(max(score, 84), 97) if inten in ["software", "jogo", "download", "geral", "documento"] else min(max(score, 50), 68)

    # Archive é ótimo, mas não pode vencer site oficial em software/jogo moderno genérico.
    if r["download_direto"]:
        if r["dominio_limpo"].endswith("archive.org") and inten in ["software", "jogo", "geral"] and not (pede_antigo(q) or tem_versao_ano(q)):
            return min(max(score, 64), 78)
        return min(max(score, 72), 96)

    if r["tipo"] == "hospedagem": return min(max(score, 50), 84)
    if r["tipo"] == "social_com_link": return min(max(score, 58 if site_pedido else 46), 80 if site_pedido else 70)

    if r["youtube"]:
        if site_pedido: return min(max(score, 72), 92)
        if inten == "media" and r["relevancia"] >= .70: return min(max(score, 58), 74)
        if inten == "media" and r["relevancia"] >= .40: return min(max(score, 48), 66)
        return min(score, 45)

    if r["streaming"]:
        if inten == "media" and r["relevancia"] >= .40: return min(max(score, 45), 68)
        return min(score, 42)

    if r["social_ruido"] and not site_pedido: return min(score, 30)
    if inten in ["media", "jogo", "software", "download"] and not r["tem_link_util"]: return min(score, 45)
    return score

def pontuar(r, q, inten, pedidos):
    score, motivos = 18, ["base 18"]
    site_pedido = bate(r["dominio_limpo"], pedidos) if pedidos else False

    rel_pts = int(r["relevancia"] * 40)
    score += rel_pts; motivos.append(f"+{rel_pts} relevância")

    if r["loja_jogo"]: score += 38; motivos.append("+38 loja/plataforma de jogo")
    elif r["oficial"]: score += 38; motivos.append("+38 oficial/confiável")

    if r["download_direto"]: score += 34; motivos.append("+34 arquivo direto real")
    elif r["host_bom"]: score += 20; motivos.append("+20 hospedagem/acervo")

    if r["tipo"] == "social_com_link": score += 16; motivos.append("+16 post com link útil")
    elif r["social_link"] and not r["tem_link_util"]: score -= 14; motivos.append("-14 social sem link claro")

    if r["youtube"]:
        score += 14 if inten == "media" else -6
        motivos.append("YouTube ajustado")

    if r["streaming"]:
        score += 12 if inten == "media" else -6
        motivos.append("streaming ajustado")

    if r["sinal_antigo"]: score += 14; motivos.append("+14 antigo/clássico")
    if r["sinal_novo"]: score -= 22; motivos.append("-22 parece versão nova")

    if r["propaganda"] == "limpo": score += 5; motivos.append("+5 sem anúncios")
    elif r["propaganda"] == "moderado": score -= 3; motivos.append("-3 anúncios moderados")
    elif r["propaganda"] == "agressivo": score -= 12; motivos.append("-12 muitos anúncios")

    if r["encurtador"]: score -= 20; motivos.append("-20 encurtador")
    if r.get("github_404"): score -= 60; motivos.append("-60 GitHub 404")
    if pedidos:
        score += 20 if site_pedido else -8
        motivos.append("site pedido" if site_pedido else "outro site")

    if inten == "jogo":
        if r["loja_jogo"] or r["oficial"]: score += 16
        elif r["download_direto"] or r["host_bom"] or r["tipo"] == "social_com_link": score += 7
        else: score -= 10
    elif inten == "software":
        if r["oficial"]: score += 16
        elif r["download_direto"] or r["host_bom"]: score += 6
        else: score -= 8
    elif inten == "media":
        if r["youtube"] or r["streaming"] or r["download_direto"] or r["host_bom"] or r["tipo"] == "social_com_link": score += 8
        else: score -= 14
    elif inten == "download":
        score += 12 if r["download_direto"] else 6 if (r["host_bom"] or r["tipo"] == "social_com_link" or r["oficial"]) else -12
    elif inten == "documento" and (r["download_direto"] or r["host_bom"]):
        score += 10

    tag_seg = r.get("tag_atchload")
    delta_seg = penalidade_seguranca(tag_seg)
    if tag_seg == "Perigoso":
        score = min(score, 12)
        motivos.append("segurança: perigoso pelo VirusTotal")
    elif tag_seg == "Alerta de Cuidado":
        score += delta_seg
        motivos.append("-22 alerta do VirusTotal")
    elif tag_seg == "Seguro / Confiável":
        score += delta_seg
        motivos.append("+3 segurança verificada")

    antes = score
    score = teto(score, r, inten, site_pedido, q)
    if score != antes: motivos.append(f"teto {antes}->{score}")
    r["score"], r["motivos"] = max(0, min(int(score), 100)), motivos
    return r


# ──────────────────────────────────────────────
# Filtros controlados pelo usuário
# positivos: domínios que o usuário quer priorizar e buscar diretamente.
# negativos: domínios que o usuário quer bloquear.
# ──────────────────────────────────────────────
def limpar_dominio_usuario(valor: str) -> str:
    valor = norm((valor or "").strip())
    valor = valor.replace("https://", "").replace("http://", "")
    valor = valor.split("/")[0].split("?")[0].strip()
    if valor.startswith("www."):
        valor = valor[4:]
    return valor

def dominios_csv(valor: str | None):
    if not valor:
        return []
    saida = []
    for parte in valor.split(","):
        dom = limpar_dominio_usuario(parte)
        if dom and "." in dom and dom not in saida:
            saida.append(dom)
    return saida

def url_ou_download_tem_ext(r, exts):
    alvo = f"{r.get('link','')} {r.get('download_url','')}".lower()
    return any(e in alvo for e in exts)

def passa_filtros_usuario(
    r,
    positivos=None,
    negativos=None,
    sem_video: bool = False,
    sem_jogos: bool = False,
    sem_software: bool = False,
    sem_documentos: bool = False,
    sem_sociais: bool = False,
    somente_download: bool = False,
):
    positivos = positivos or []
    negativos = negativos or []
    dom = r.get("dominio_limpo", "")

    # Negativo manual sempre vence.
    if bate(dom, negativos):
        return False

    # Filtros rápidos por tipo.
    if sem_video:
        if r.get("youtube") or r.get("streaming") or url_ou_download_tem_ext(r, [".mp4", ".mkv", ".avi", ".mov", ".mp3", ".flac", ".wav"]):
            return False

    if sem_jogos:
        if r.get("loja_jogo") or bate(dom, GAME_STORES):
            return False

    if sem_software:
        if (r.get("oficial") and bate(dom, SOFTWARE_OFICIAL)) or any(w in norm(f"{r.get('titulo','')} {r.get('descricao','')}") for w in SOFTWARE_WORDS):
            return False

    if sem_documentos:
        if r.get("documento_irrelevante") or bate(dom, ACADEMICOS) or url_ou_download_tem_ext(r, [".pdf", ".epub", ".mobi", ".cbz", ".cbr"]):
            return False

    if sem_sociais:
        if r.get("social_link") or r.get("social_ruido") or r.get("social_compartilhamento"):
            return False

    if somente_download:
        if not (r.get("download_direto") or r.get("tem_download_na_pagina") or r.get("tem_link_util") or r.get("host_bom")):
            return False

    return True

def aplicar_boost_filtros(r, positivos):
    if positivos and bate(r.get("dominio_limpo", ""), positivos):
        r["score"] = min(100, int(r.get("score", 0)) + 25)
        r.setdefault("motivos", []).append("+25 filtro positivo do usuário")
        r["filtro_positivo"] = True
    else:
        r["filtro_positivo"] = False
    return r

# ──────────────────────────────────────────────
# Busca: consulta ampla + classificação forte.
# Quanto menos travar a busca em domínio específico, melhor.
# ──────────────────────────────────────────────
def montar_queries(q, inten, pedidos, positivos=None):
    # Ruído que nunca ajuda — exclui em todas as queries
    excluir_sempre = (
        "-site:wikipedia.org -site:imdb.com -site:adorocinema.com -site:filmow.com "
        "-site:letterboxd.com -site:rottentomatoes.com -site:themoviedb.org "
        "-site:ucicinemas.com.br -site:ingresso.com -site:cinemark.com.br "
        "-site:scholar.archive.org -site:scielo.br -site:scielo.org "
        "-site:doi.org -site:researchgate.net -site:academia.edu"
    )
    qs = []
    positivos = positivos or []

    # ── 0. Sites pedidos explicitamente pelo usuário — máxima prioridade ──
    if positivos:
        site_q = " OR ".join(f"site:{d}" for d in positivos)
        qs.append(f'"{q}" ({site_q})')

    if pedidos:
        site_q = " OR ".join(f"site:{d}" for d in pedidos)
        qs.append(f'"{q}" ({site_q})')

    # ── 1. Oficial/loja — uma única query ampla por intenção ──
    if inten in ["jogo", "geral", "download"]:
        qs.append(
            f'"{q}" (site:store.steampowered.com OR site:gog.com OR site:itch.io '
            f'OR site:store.epicgames.com OR site:nintendo.com OR site:xbox.com '
            f'OR site:playstation.com OR official OR oficial)'
        )
    if inten in ["software", "geral", "download"]:
        qs.append(
            f'"{q}" (official OR oficial OR download OR installer) '
            f'(site:github.com OR site:sourceforge.net OR site:microsoft.com '
            f'OR site:code.visualstudio.com)'
        )

    # ── 2. Google Drive público — busca direta por arquivos compartilhados ──
    # Busca o arquivo pelo nome dentro do Drive sem forçar pasta específica.
    qs.append(f'"{q}" site:drive.google.com')

    # ── 3. Archive.org — acervo de mídias antigas e software ──
    qs.append(f'"{q}" site:archive.org -site:scholar.archive.org')

    # ── 4. Hospedagens de arquivo — uma query unificada ──
    qs.append(
        f'"{q}" (site:mediafire.com OR site:mega.nz OR site:pixeldrain.com '
        f'OR site:gofile.io OR site:1fichier.com OR site:sendspace.com '
        f'OR site:workupload.com)'
    )

    # ── 5. Posts em redes sociais com link de download ──
    qs.append(
        f'"{q}" (download OR baixar OR "google drive" OR mega OR mediafire OR pixeldrain) '
        f'(site:x.com OR site:twitter.com OR site:reddit.com)'
    )

    # ── 6. YouTube — só para mídia ──
    if inten == "media":
        qs.append(f'"{q}" site:youtube.com -trailer -teaser')

    # ── 7. DESCOBERTA ABERTA — sem site: nenhum, pega tudo que o Google achar ──
    # Esta é a query que vai achar sites desconhecidos com o conteúdo certo.
    # Dois formatos: um com aspas (mais preciso) e um sem (mais amplo).
    if inten == "media":
        qs.append(f'"{q}" (download OR baixar OR assistir OR watch) {excluir_sempre}')
        qs.append(f'{q} download filme completo OR assistir gratis {excluir_sempre}')
    elif inten == "jogo":
        qs.append(f'"{q}" (download OR baixar OR "pc game" OR rom OR iso) {excluir_sempre}')
        qs.append(f'{q} download gratis pc OR rom OR iso {excluir_sempre}')
    elif inten == "software":
        qs.append(f'"{q}" (download OR baixar OR installer OR setup OR gratis) {excluir_sempre}')
    elif inten == "documento":
        qs.append(f'"{q}" (download OR baixar OR pdf OR epub OR ebook) {excluir_sempre}')
    else:
        qs.append(f'"{q}" (download OR baixar) {excluir_sempre}')
        qs.append(f'{q} download OR baixar {excluir_sempre}')

    # Remove duplicadas mantendo ordem.
    out = []
    for x in qs:
        if x not in out:
            out.append(x)
    return out

def serp(query, num=10):
    if not SERPAPI_KEY:
        raise HTTPException(status_code=500, detail="SERPAPI_KEY não encontrada no .env")
    try:
        r = requests.get("https://serpapi.com/search", params={"q": query, "api_key": SERPAPI_KEY, "num": num, "hl": "pt", "gl": "br"}, timeout=12)
        r.raise_for_status()
        return r.json().get("organic_results", []) or []
    except HTTPException:
        raise
    except Exception:
        return []

def visivel(r):
    if r["score"] <= 0 or r["bloqueado"] or r["trailer"] or r["cinema"] or r["documento_irrelevante"]:
        return False
    if r.get("github_404"):
        return False
    if r["social_ruido"] and r["score"] < 45:
        return False
    if r["relevancia"] < .30 and not (r["oficial"] or r["download_direto"] or r["loja_jogo"] or r["tipo"] == "social_com_link"):
        return False
    return True

def limitar_dominios(rs):
    out, cont = [], defaultdict(int)
    for r in rs:
        if r["loja_jogo"] or r["oficial"]:
            lim = 2
        elif r["youtube"] or r["social_link"]:
            lim = 3
        else:
            lim = 2
        if cont[r["dominio_limpo"]] >= lim:
            continue
        cont[r["dominio_limpo"]] += 1
        out.append(r)
    return out

@app.get("/buscar")
def buscar(
    q: str,
    sem_video: bool = False,
    sem_jogos: bool = False,
    sem_software: bool = False,
    sem_documentos: bool = False,
    sem_sociais: bool = False,
    somente_download: bool = False,
    positivos: str = "",
    negativos: str = "",
):
    q = (q or "").strip()
    if not q:
        return {"resultados": []}
    inten, pedidos = intencao(q), sites_pedidos(q)
    filtros_positivos = dominios_csv(positivos)
    filtros_negativos = dominios_csv(negativos)

    brutos, vistos = [], set()
    for query in montar_queries(q, inten, pedidos, filtros_positivos):
        for item in serp(query):
            link = item.get("link", "")
            if link and link not in vistos:
                vistos.add(link)
                brutos.append(item)

    resultados = []
    with ThreadPoolExecutor(max_workers=8) as ex:
        futs = [ex.submit(classificar, item, q, inten, pedidos) for item in brutos]
        for f in as_completed(futs):
            try:
                r = pontuar(f.result(), q, inten, pedidos)
                r = aplicar_boost_filtros(r, filtros_positivos)
                if visivel(r) and passa_filtros_usuario(
                    r,
                    positivos=filtros_positivos,
                    negativos=filtros_negativos,
                    sem_video=sem_video,
                    sem_jogos=sem_jogos,
                    sem_software=sem_software,
                    sem_documentos=sem_documentos,
                    sem_sociais=sem_sociais,
                    somente_download=somente_download,
                ):
                    resultados.append(r)
            except Exception:
                pass

    resultados.sort(key=lambda r: r["score"], reverse=True)
    resultados = limitar_dominios(resultados)
    return {
        "query": q,
        "intencao": inten,
        "filtros": {
            "sem_video": sem_video,
            "sem_jogos": sem_jogos,
            "sem_software": sem_software,
            "sem_documentos": sem_documentos,
            "sem_sociais": sem_sociais,
            "somente_download": somente_download,
            "positivos": filtros_positivos,
            "negativos": filtros_negativos,
        },
        "total": len(resultados),
        "resultados": resultados[:60]
    }

@app.get("/verificar")
def verificar_url(url: str = Query(...)):
    url = (url or "").strip()
    if not url.startswith("http"):
        raise HTTPException(status_code=400, detail="URL inválida")

    cache = buscar_cache_local(url)
    if cache and cache["tag"] not in ["Aguardando Análise", "Enviado ao VT", "Erro na API"]:
        tag = cache["tag"]
        return {
            "tag_atchload": tag,
            "hash": cache["hash"],
            "malicious": cache["malicious"],
            "suspicious": cache["suspicious"],
            "score_delta": penalidade_seguranca(tag)
        }

    if not VIRUSTOTAL_API_KEY:
        return {
            "tag_atchload": "VT indisponível",
            "hash": None,
            "malicious": 0,
            "suspicious": 0,
            "score_delta": 0,
            "detail": "VIRUSTOTAL_API_KEY não encontrada no .env"
        }

    headers_vt = {"x-apikey": VIRUSTOTAL_API_KEY}
    url_id = gerar_id_url_virustotal(url)

    try:
        resp = requests.get(f"https://www.virustotal.com/api/v3/urls/{url_id}", headers=headers_vt, timeout=12)

        # Se o VT ainda não conhece a URL, envia para análise. O resultado costuma não sair na hora.
        if resp.status_code == 404:
            post = requests.post("https://www.virustotal.com/api/v3/urls", headers=headers_vt, data={"url": url}, timeout=12)
            if post.status_code in [200, 202]:
                salvar_no_banco(url, "Enviado ao VT", None, 0, 0)
                return {"tag_atchload": "Enviado ao VT", "hash": None, "malicious": 0, "suspicious": 0, "score_delta": 0}
            salvar_no_banco(url, "Erro na API", None, 0, 0)
            return {"tag_atchload": "Erro na API", "hash": None, "malicious": 0, "suspicious": 0, "score_delta": 0}

        if resp.status_code == 200:
            dados = resp.json().get("data", {}).get("attributes", {})
            stats = dados.get("last_analysis_stats", {}) or {}
            malicious = int(stats.get("malicious", 0) or 0)
            suspicious = int(stats.get("suspicious", 0) or 0)
            tag = calcular_tag_atchload(malicious, suspicious)
            hash_arquivo = dados.get("last_http_response_content_sha256") or dados.get("last_final_url") or None
            salvar_no_banco(url, tag, hash_arquivo, malicious, suspicious)
            return {
                "tag_atchload": tag,
                "hash": hash_arquivo,
                "malicious": malicious,
                "suspicious": suspicious,
                "score_delta": penalidade_seguranca(tag)
            }

        if resp.status_code == 429:
            return {"tag_atchload": "Limite do VT", "hash": None, "malicious": 0, "suspicious": 0, "score_delta": 0}

        return {"tag_atchload": "Erro na API", "hash": None, "malicious": 0, "suspicious": 0, "score_delta": 0}

    except Exception as e:
        return {"tag_atchload": "Erro na API", "hash": None, "malicious": 0, "suspicious": 0, "score_delta": 0, "detail": str(e)}

@app.get("/baixar")
def baixar(url: str):
    if not url or not url.startswith("http"):
        raise HTTPException(status_code=400, detail="URL inválida")
    dom = dominio(url)
    if drive_pasta(url) or bate(dom, SOCIAL_LINK) or bate(dom, SOCIAL_RUIDO):
        raise HTTPException(status_code=400, detail="Este link não é um arquivo direto para download.")
    if not head_arquivo(url):
        raise HTTPException(status_code=400, detail="Não parece ser um arquivo direto para download.")
    try:
        r = requests.get(url, stream=True, timeout=15, headers=HEADERS)
        r.raise_for_status()
        name = urlparse(url).path.rstrip("/").split("/")[-1] or "arquivo"
        return StreamingResponse(
            r.iter_content(chunk_size=8192),
            media_type=r.headers.get("Content-Type", "application/octet-stream"),
            headers={"Content-Disposition": f'attachment; filename="{name}"'}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Não foi possível baixar: {str(e)}")

