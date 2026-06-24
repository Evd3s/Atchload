from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv
from urllib.parse import urlparse, quote
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict
import requests, os, re, unicodedata

load_dotenv()
SERPAPI_KEY = os.getenv("SERPAPI_KEY")
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

HOSTS = ["archive.org","mediafire.com","mega.nz","drive.google.com","pixeldrain.com","gofile.io","sendspace.com","workupload.com","1fichier.com","sourceforge.net","github.com","itch.io"]
HOSTS_DIRETOS = ["archive.org","pixeldrain.com","gofile.io","sourceforge.net","github.com","mediafire.com","1fichier.com","sendspace.com","workupload.com","itch.io"]
SOCIAL_LINK = ["x.com","twitter.com","reddit.com"]
SOCIAL_RUIDO = ["tiktok.com","instagram.com","facebook.com","threads.net","kwai.com"]
ENCURTADORES = ["bit.ly","tinyurl.com","shorte.st","adf.ly","linkvertise.com","ouo.io","bc.vc","sh.st","cutt.ly","is.gd","shrinke.me"]
BLOQUEADOS = ["wikipedia.org","wikimedia.org","imdb.com","adorocinema.com","filmow.com","letterboxd.com","rottentomatoes.com","themoviedb.org","metacritic.com","ucicinemas.com.br","ingresso.com","cinemark.com.br","cinepolis.com.br","moviecom.com.br","netflix.com","disneyplus.com","primevideo.com","globoplay.globo.com","telecine.com.br","max.com","hbomax.com","paramountplus.com","movies.disney.com","disney.com","pixar.com","marvel.com","warnerbros.com","universalpictures.com","sonypictures.com","dreamworks.com","paramountpictures.com","lionsgate.com","play.google.com","apps.apple.com"]
EXTS = [".exe",".msi",".zip",".rar",".7z",".tar",".gz",".epub",".mobi",".pdf",".dmg",".apk",".iso",".jar",".mp4",".mkv",".avi",".mov",".mp3",".flac",".wav",".cbz",".cbr"]
EXTS_PERIGOSAS = [".bat",".cmd",".scr",".vbs",".ps1"]
VIDEO_WORDS = ["filme","movie","film","anime","animacao","animação","serie","série","episodio","episódio","temporada","dublado","legendado","assistir","cartoon","desenho"]
DOWNLOAD_WORDS = ["download","baixar","instalar","installer","setup","apk","mod","mods","rom","iso","emulador","programa","software"]
DOC_WORDS = ["pdf","livro","ebook","epub","manga","mangá","quadrinho","hq"]
TRAILER_WORDS = ["trailer","teaser","making of","featurette","clipe oficial"]
CINEMA_WORDS = ["ingresso","sessões","sessoes","cinema","estreia","em cartaz"]
LINK_WORDS = ["mega.nz","mediafire.com","drive.google.com","pixeldrain.com","gofile.io","1fichier.com","sendspace.com","workupload.com","archive.org/download","archive.org/details","sourceforge.net","github.com","baixar","download","link","pasta","arquivo",".zip",".rar",".7z",".pdf",".mp4",".mkv",".iso",".epub"]
AD_SCRIPTS = ["googlesyndication.com","doubleclick.net","adnxs.com","taboola.com","outbrain.com","propellerads.com","popads.net","adcash.com","exoclick.com"]
STOP = {"download","baixar","filme","movie","film","jogo","game","anime","serie","série","episodio","episódio","temporada","dublado","legendado","assistir","online","completo","completa","gratis","grátis","site","oficial","youtube","drive","google","mega","mediafire","archive","reddit","twitter","x"}

SITES_MENCIONAVEIS = {
    "youtube":["youtube.com","youtu.be"], "youtu":["youtube.com","youtu.be"], "archive":["archive.org"], "internet archive":["archive.org"],
    "mega":["mega.nz"], "mediafire":["mediafire.com"], "drive":["drive.google.com"], "gdrive":["drive.google.com"], "google drive":["drive.google.com"],
    "github":["github.com"], "itch":["itch.io"], "pixeldrain":["pixeldrain.com"], "gofile":["gofile.io"], "reddit":["reddit.com"], "twitter":["x.com","twitter.com"], "x":["x.com","twitter.com"]
}
OFICIAIS = {"minecraft":["minecraft.net"],"mojang":["minecraft.net"],"vlc":["videolan.org"],"blender":["blender.org"],"gimp":["gimp.org"],"python":["python.org"],"java":["java.com","oracle.com"],"audacity":["audacityteam.org"],"obs":["obsproject.com"],"vscode":["code.visualstudio.com"],"visual studio code":["code.visualstudio.com"],"firefox":["mozilla.org"],"chrome":["google.com"],"7zip":["7-zip.org"],"7-zip":["7-zip.org"],"libreoffice":["libreoffice.org"],"winrar":["win-rar.com","rarlab.com"]}


def norm(t):
    t = unicodedata.normalize("NFD", t or "")
    return "".join(c for c in t if unicodedata.category(c) != "Mn").lower()

def dominio(url):
    try: return urlparse(url).netloc.lower().replace("www.","")
    except Exception: return ""

def path(url):
    try: return urlparse(url).path.lower()
    except Exception: return ""

def bate(dom, lista):
    dom = (dom or "").lower()
    return any(dom == d or dom.endswith("." + d) for d in lista)

def palavra(texto, p):
    return re.search(r"\b" + re.escape(norm(p)) + r"\b", norm(texto)) is not None

def tokens(q):
    ps = re.findall(r"[a-z0-9]+", norm(q))
    bons = [p for p in ps if len(p) > 2 and p not in STOP]
    return bons or [p for p in ps if len(p) > 2]

def relevancia(q, texto):
    ts = tokens(q)
    if not ts: return 0
    tx = norm(texto)
    return sum(1 for t in ts if t in tx) / len(ts)

def intencao(q):
    qn = norm(q)
    if any(w in qn for w in DOC_WORDS): return "documento"
    if any(w in qn for w in DOWNLOAD_WORDS): return "download"
    if "youtube" in qn or "video" in qn or "assistir" in qn or any(w in qn for w in VIDEO_WORDS): return "video"
    return "geral"

def sites_pedidos(q):
    qn, out = norm(q), []
    for k, ds in SITES_MENCIONAVEIS.items():
        if palavra(qn, k): out += ds
    return sorted(set(out))

def oficial(q, dom):
    qn = norm(q)
    return any(palavra(qn, nome) and bate(dom, ds) for nome, ds in OFICIAIS.items())

def pede_antigo(q):
    qn = norm(q)
    return any(w in qn for w in ["antigo","antiga","classico","classica","original","1967","anos 60","anos 70","old"])

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
    u = url.lower()
    return "drive.google.com" in u and ("/folders/" in u or ("?usp=sharing" in u and "/file/" not in u))

def archive_details(url): return "archive.org/details/" in url.lower()
def archive_download(url): return "archive.org/download/" in url.lower()

def archive_id(url):
    p = urlparse(url).path
    if "/details/" in p: return p.split("/details/",1)[1].split("/")[0]
    if "/download/" in p: return p.split("/download/",1)[1].split("/")[0]
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

def head_arquivo(url):
    if drive_pasta(url): return False
    if tem_ext(url): return True
    try:
        r = requests.head(url, timeout=5, allow_redirects=True, headers=HEADERS)
        ct = (r.headers.get("Content-Type") or "").lower()
        cd = (r.headers.get("Content-Disposition") or "").lower()
        tipos = ["application/zip","application/x-rar","application/x-7z-compressed","application/octet-stream","application/pdf","application/epub+zip","application/x-msdownload","application/vnd.android.package-archive","video/","audio/"]
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
            if any(x in low for x in ["_meta","_files.xml","_thumb","torrent"]): continue
            size = int(f.get("size") or 0)
            sc = 20 + (15 if size > 5_000_000 else 0) + sum(5 for t in ts if t in norm(name))
            cand.append((sc, name))
        if not cand: return None
        cand.sort(reverse=True)
        return f"https://archive.org/download/{ident}/{quote(cand[0][1])}"
    except Exception:
        return None

def download_url(link, dom, q):
    if not link.startswith("http") or ext_perigosa(link): return None
    if archive_details(link): return arquivo_archive(link, q)
    if archive_download(link) and head_arquivo(link): return link
    if "drive.google.com" in dom: return None
    if bate(dom, SOCIAL_LINK) or bate(dom, SOCIAL_RUIDO): return None
    if (bate(dom, HOSTS_DIRETOS) or tem_ext(link)) and head_arquivo(link): return link
    return None


def classificar(item, q, inten, pedidos):
    link = item.get("link", "") or ""
    tit = item.get("title", "") or ""
    desc = item.get("snippet", "") or ""
    disp = item.get("displayed_link", "") or ""
    dom = dominio(link)
    texto = f"{tit} {desc} {link} {disp}"
    tx = norm(texto)

    yt = bate(dom, ["youtube.com","youtu.be"])
    soc = bate(dom, SOCIAL_LINK)
    ruido = bate(dom, SOCIAL_RUIDO)
    host = bate(dom, HOSTS)
    off = oficial(q, dom)
    blocked = bate(dom, BLOQUEADOS)
    enc = bate(dom, ENCURTADORES)
    trail = any(norm(w) in tx for w in TRAILER_WORDS) and not pede_trailer(q)
    cine = any(norm(w) in tx for w in CINEMA_WORDS)
    antigo = pede_antigo(q)
    old_ok = antigo and any(w in tx for w in ["1967","classico","classic","antigo","original"])
    old_bad = antigo and any(w in tx for w in ["2016","2018","2019","live action","novo","remake"])

    prop, link_pagina = "desconhecido", False
    if not (blocked or yt or enc or trail or cine) and (soc or host or off):
        prop, link_pagina = ads_e_links(link)

    link_texto = any(norm(w) in tx for w in LINK_WORDS)
    util = link_texto or link_pagina
    durl = download_url(link, dom, q)

    tipo = "geral"
    if off: tipo = "oficial"
    elif durl: tipo = "download_direto"
    elif host: tipo = "hospedagem"
    elif soc and util: tipo = "social_com_link"
    elif yt: tipo = "youtube"
    elif ruido: tipo = "social_ruido"

    return {"titulo":tit,"descricao":desc,"link":link,"dominio":disp or dom,"dominio_limpo":dom,"tipo":tipo,"relevancia":relevancia(q,texto),"download_direto":bool(durl),"download_url":durl,"fonte_confiavel":host or off,"oficial":off,"youtube":yt,"social_link":soc,"social_ruido":ruido,"host_bom":host,"tem_link_util":util,"encurtador":enc,"bloqueado":blocked,"trailer":trail,"cinema":cine,"sinal_antigo":old_ok,"sinal_novo":old_bad,"propaganda":prop,"score":0,"motivos":[]}


def teto(score, r, inten, site_pedido):
    if r["bloqueado"] or r["cinema"] or r["trailer"]: return 0
    if r["encurtador"]: return min(score, 35)
    if r["oficial"]: return min(max(score, 76), 94) if inten in ["download","geral","documento"] else min(score,55)
    if r["download_direto"]: return min(max(score, 72), 96)
    if r["tipo"] == "hospedagem": return min(max(score, 52), 86)
    if r["tipo"] == "social_com_link": return min(max(score, 60 if site_pedido else 48), 82 if site_pedido else 72)
    if r["youtube"]:
        if site_pedido: return min(max(score,72),92)
        if inten == "video" and r["relevancia"] >= .70: return min(max(score,55),72)
        if inten == "video" and r["relevancia"] >= .40: return min(max(score,45),65)
        return min(score,45)
    if r["social_ruido"] and not site_pedido: return min(score,30)
    if inten in ["download","video"] and not r["tem_link_util"]: return min(score,48)
    return score


def pontuar(r, q, inten, pedidos):
    score, motivos = 20, ["base 20"]
    site_pedido = bate(r["dominio_limpo"], pedidos) if pedidos else False
    add = int(r["relevancia"] * 38); score += add; motivos.append(f"+{add} relevância")

    if r["oficial"]: score += 30; motivos.append("+30 oficial")
    if r["download_direto"]: score += 36; motivos.append("+36 arquivo direto real")
    elif r["host_bom"]: score += 22; motivos.append("+22 hospedagem conhecida")
    if r["tipo"] == "social_com_link": score += 18; motivos.append("+18 post com link útil")
    elif r["social_link"] and not r["tem_link_util"]: score -= 12; motivos.append("-12 social sem link claro")
    if r["youtube"]: score += 12 if inten == "video" else -8; motivos.append("YouTube ajustado")
    if r["sinal_antigo"]: score += 14; motivos.append("+14 antigo/clássico")
    if r["sinal_novo"]: score -= 22; motivos.append("-22 parece versão nova")
    if r["propaganda"] == "limpo": score += 5; motivos.append("+5 sem anúncios")
    elif r["propaganda"] == "moderado": score -= 3; motivos.append("-3 anúncios moderados")
    elif r["propaganda"] == "agressivo": score -= 12; motivos.append("-12 muitos anúncios")
    if r["encurtador"]: score -= 20; motivos.append("-20 encurtador")
    if pedidos: score += 20 if site_pedido else -8; motivos.append("site pedido" if site_pedido else "outro site")

    if inten == "download": score += 12 if r["download_direto"] else 6 if (r["host_bom"] or r["tipo"] == "social_com_link") else -12
    elif inten == "video": score += 8 if (r["download_direto"] or r["host_bom"] or r["tipo"] == "social_com_link" or r["youtube"]) else -10
    elif inten == "documento" and (r["download_direto"] or r["host_bom"]): score += 10

    antes = score
    score = teto(score, r, inten, site_pedido)
    if score != antes: motivos.append(f"teto {antes}->{score}")
    r["score"], r["motivos"] = max(0, min(int(score),100)), motivos
    return r


def montar_queries(q, inten, pedidos):
    excluir = "-site:wikipedia.org -site:imdb.com -site:adorocinema.com -site:filmow.com -site:letterboxd.com -site:rottentomatoes.com -site:themoviedb.org -site:netflix.com -site:disneyplus.com -site:primevideo.com -site:globoplay.globo.com -site:ucicinemas.com.br -site:ingresso.com -site:cinemark.com.br -site:movies.disney.com"
    qs = []
    if pedidos:
        site_query = " OR ".join(f"site:{d}" for d in pedidos)
        qs.append(f'"{q}" ({site_query})')
    if inten in ["download","geral","documento"]: qs.append(f'"{q}" "official download" OR "download oficial" OR "site oficial"')
    qs += [
        f'"{q}" site:archive.org',
        f'"{q}" (site:mediafire.com OR site:mega.nz OR site:drive.google.com OR site:pixeldrain.com OR site:gofile.io OR site:sourceforge.net OR site:itch.io)',
        f'"{q}" (download OR baixar OR "google drive" OR mega OR mediafire) (site:x.com OR site:twitter.com OR site:reddit.com)',
    ]
    if inten == "video" or bate("youtube.com", pedidos): qs.append(f'"{q}" site:youtube.com -trailer')
    qs.append(f'{q} download OR baixar {excluir}')
    return qs


def serp(query, num=8):
    if not SERPAPI_KEY: raise HTTPException(status_code=500, detail="SERPAPI_KEY não encontrada no .env")
    try:
        r = requests.get("https://serpapi.com/search", params={"q":query,"api_key":SERPAPI_KEY,"num":num,"hl":"pt","gl":"br"}, timeout=12)
        r.raise_for_status()
        return r.json().get("organic_results", []) or []
    except HTTPException: raise
    except Exception: return []


def visivel(r):
    if r["score"] <= 0 or r["bloqueado"] or r["trailer"] or r["cinema"]: return False
    if r["social_ruido"] and r["score"] < 45: return False
    if r["relevancia"] < .34 and not (r["oficial"] or r["download_direto"] or r["tipo"] == "social_com_link"): return False
    return True


def limitar_dominios(rs):
    out, cont = [], defaultdict(int)
    for r in rs:
        lim = 2 if r["oficial"] else 3 if (r["youtube"] or r["social_link"]) else 2
        if cont[r["dominio_limpo"]] >= lim: continue
        cont[r["dominio_limpo"]] += 1
        out.append(r)
    return out

@app.get("/buscar")
def buscar(q: str):
    q = (q or "").strip()
    if not q: return {"resultados": []}
    inten, pedidos = intencao(q), sites_pedidos(q)

    brutos, vistos = [], set()
    for query in montar_queries(q, inten, pedidos):
        for item in serp(query):
            link = item.get("link", "")
            if link and link not in vistos:
                vistos.add(link); brutos.append(item)

    resultados = []
    with ThreadPoolExecutor(max_workers=8) as ex:
        futs = [ex.submit(classificar, item, q, inten, pedidos) for item in brutos]
        for f in as_completed(futs):
            try:
                r = pontuar(f.result(), q, inten, pedidos)
                if visivel(r): resultados.append(r)
            except Exception:
                pass

    resultados.sort(key=lambda r: r["score"], reverse=True)
    resultados = limitar_dominios(resultados)
    return {"query": q, "intencao": inten, "total": len(resultados), "resultados": resultados[:60]}

@app.get("/baixar")
def baixar(url: str):
    if not url or not url.startswith("http"): raise HTTPException(status_code=400, detail="URL inválida")
    dom = dominio(url)
    if drive_pasta(url) or bate(dom, SOCIAL_LINK) or bate(dom, SOCIAL_RUIDO):
        raise HTTPException(status_code=400, detail="Este link não é um arquivo direto para download.")
    if not head_arquivo(url):
        raise HTTPException(status_code=400, detail="Não parece ser um arquivo direto para download.")
    try:
        r = requests.get(url, stream=True, timeout=15, headers=HEADERS)
        r.raise_for_status()
        name = urlparse(url).path.rstrip("/").split("/")[-1] or "arquivo"
        return StreamingResponse(r.iter_content(chunk_size=8192), media_type=r.headers.get("Content-Type","application/octet-stream"), headers={"Content-Disposition": f'attachment; filename="{name}"'})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Não foi possível baixar: {str(e)}")
