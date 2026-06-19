from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import requests
import os
import sqlite3
import base64
from datetime import datetime
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed

# Carrega as chaves do arquivo .env
load_dotenv()
SERPAPI_KEY = os.getenv("SERPAPI_KEY")
VIRUSTOTAL_API_KEY = os.getenv("VIRUSTOTAL_API_KEY")

app = FastAPI(
    title="Atchload API - Completa",
    description="Backend Integrado: Busca Inteligente + Motor de Segurança",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

NOME_BANCO = "atchload.db"


# MÓDULO DE SEGURANÇA E BANCO DE DADOS


def inicializar_banco():
    conexao = sqlite3.connect(NOME_BANCO)
    cursor = conexao.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS historico_seguranca (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        alvo TEXT UNIQUE,
        tipo TEXT,
        harmless INTEGER,
        suspicious INTEGER,
        malicious INTEGER,
        tag_atchload TEXT,
        data_consulta TEXT
    )
    """)
    conexao.commit()
    conexao.close()

def buscar_cache_local(url: str):
    conexao = sqlite3.connect(NOME_BANCO)
    cursor = conexao.cursor()
    cursor.execute("SELECT tag_atchload, harmless, suspicious, malicious, data_consulta FROM historico_seguranca WHERE alvo = ?", (url,))
    resultado = cursor.fetchone()
    conexao.close()
    return resultado

def salvar_no_banco(url: str, harmless: int, suspicious: int, malicious: int, tag: str):
    conexao = sqlite3.connect(NOME_BANCO)
    cursor = conexao.cursor()
    data_atual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
    INSERT OR REPLACE INTO historico_seguranca 
    (alvo, tipo, harmless, suspicious, malicious, tag_atchload, data_consulta)
    VALUES (?, 'url', ?, ?, ?, ?, ?)
    """, (url, harmless, suspicious, malicious, tag, data_atual))
    conexao.commit()
    conexao.close()

def gerar_id_url_virustotal(url: str) -> str:
    return base64.urlsafe_b64encode(url.encode("utf-8")).decode("utf-8").strip("=")

def calcular_tag_atchload(malicious: int, suspicious: int) -> str:
    if malicious > 2: return "Perigoso"
    elif malicious > 0 or suspicious > 0: return "Inseguro"
    return "Seguro / Confiável"

inicializar_banco()


# MÓDULO DE BUSCA 


WHITELIST = ["archive.org", "mediafire.com", "mega.nz", "drive.google.com", "pixeldrain.com", "gofile.io", "sendspace.com", "itch.io", "workupload.com", "1fichier.com", "sourceforge.net"]
SITES_MENCIONAVEIS = {"youtube": ["youtube.com", "youtu.be"], "archive": ["archive.org"], "mega": ["mega.nz"], "mediafire": ["mediafire.com"], "drive": ["drive.google.com"], "github": ["github.com"], "itch": ["itch.io"]}
EXTENSOES_DIRETAS = [".exe", ".zip", ".rar", ".7z", ".tar", ".gz", ".epub", ".mobi", ".dmg", ".apk", ".mp4", ".mkv", ".avi", ".iso", ".jar", ".mp3"]
URL_INUTILS = ["/comments", "/discussion", "/reviews", "/forum", "/profile", "/user/", "/community"]
AD_SCRIPTS = ["googlesyndication.com", "doubleclick.net", "adnxs.com", "taboola.com", "outbrain.com"]
PALAVRAS_DOWNLOAD_HTML = ["mega.nz", "mediafire.com", "drive.google.com", "pixeldrain.com", "gofile.io", "baixar agora", "download here"]
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

def extrair_dominio(url):
    try: return urlparse(url).netloc.replace("www.", "")
    except: return ""

def detectar_site_mencionado(query_lower):
    mencionados = []
    for keyword, dominios in SITES_MENCIONAVEIS.items():
        if keyword in query_lower: mencionados.extend(dominios)
    return mencionados

def e_url_inutil(url): return any(p in url.lower() for p in URL_INUTILS)

def verificar_head(url):
    try:
        ct = requests.head(url, timeout=4, allow_redirects=True).headers.get("Content-Type", "")
        tipos = ["application/zip", "application/x-rar", "application/octet-stream", "video/mp4"]
        return any(t in ct for t in tipos)
    except: return False

def analisar_pagina(url):
    try:
        html = requests.get(url, timeout=5, headers=HEADERS).text.lower()
        ads = len([s for s in AD_SCRIPTS if s in html])
        propaganda = "limpo" if ads == 0 else "agressivo"
        tem_download = len([p for p in PALAVRAS_DOWNLOAD_HTML if p in html]) >= 1
        return propaganda, tem_download
    except: return "desconhecido", False

def processar_item(item, query, query_lower, sites_mencionados):
    link = item.get("link", "")
    dominio = extrair_dominio(link)
    cache_seguranca = buscar_cache_local(link)
    tag_seguranca = cache_seguranca[0] if cache_seguranca else "Aguardando Análise"
    
    propaganda, download_direto = analisar_pagina(link)
    
    return {
        "titulo": item.get("title", ""),
        "link": link,
        "dominio_limpo": dominio,
        "descricao": item.get("snippet", ""),
        "tag_atchload": tag_seguranca,
        "download_direto": download_direto,
        "score": 50 # Simplificado
    }


#  ENDPOINTS DA API


@app.get("/buscar")
def buscar(q: str):
    query_lower = q.lower()
    sites_mencionados = detectar_site_mencionado(query_lower)
    
    queries = [f'"{q}" site:drive.google.com OR site:mega.nz OR site:mediafire.com']
    itens_brutos = []
    
    for query_str in queries:
        try:
            r = requests.get("https://serpapi.com/search", params={"q": query_str, "api_key": SERPAPI_KEY, "num": 5})
            itens_brutos.extend(r.json().get("organic_results", []))
        except: pass

    resultados = []
    with ThreadPoolExecutor(max_workers=5) as executor:
        futuros = {executor.submit(processar_item, item, q, query_lower, sites_mencionados): item for item in itens_brutos}
        for futuro in as_completed(futuros):
            resultados.append(futuro.result())
    
    return {"termo_buscado": q, "resultados": resultados}

@app.get("/verificar")
def verificar_url(url: str = Query(...)):
    cache = buscar_cache_local(url)
    if cache:
        return {"tag_atchload": cache[0]}
    
    url_id = gerar_id_url_virustotal(url)
    headers = {"x-apikey": VIRUSTOTAL_API_KEY}
    resp = requests.get(f"https://www.virustotal.com/api/v3/urls/{url_id}", headers=headers)
    
    if resp.status_code == 404:
        requests.post("https://www.virustotal.com/api/v3/urls", headers=headers, data={"url": url})
        return {"tag_atchload": "Análise em Processo"}
    
    if resp.status_code == 200:
        stats = resp.json()['data']['attributes']['last_analysis_stats']
        m, s = stats.get('malicious', 0), stats.get('suspicious', 0)
        tag = calcular_tag_atchload(m, s)
        salvar_no_banco(url, stats.get('harmless', 0), s, m, tag)
        return {"tag_atchload": tag}
        
    return {"tag_atchload": "Erro"}