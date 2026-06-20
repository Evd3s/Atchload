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

load_dotenv()

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configurações
SERPAPI_KEY = os.getenv("SERPAPI_KEY")
VIRUSTOTAL_API_KEY = os.getenv("VIRUSTOTAL_API_KEY")
NOME_BANCO = "atchload.db"

# MÓDULO DE SEGURANÇA 
def inicializar_banco():
    conexao = sqlite3.connect(NOME_BANCO)
    cursor = conexao.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS historico_seguranca (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        alvo TEXT UNIQUE,
        tag_atchload TEXT,
        data_consulta TEXT
    )
    """)
    conexao.commit()
    conexao.close()

def buscar_cache_local(url: str):
    conexao = sqlite3.connect(NOME_BANCO)
    cursor = conexao.cursor()
    cursor.execute("SELECT tag_atchload FROM historico_seguranca WHERE alvo = ?", (url,))
    resultado = cursor.fetchone()
    conexao.close()
    return resultado[0] if resultado else "Aguardando Análise"

def salvar_no_banco(url: str, tag: str):
    conexao = sqlite3.connect(NOME_BANCO)
    cursor = conexao.cursor()
    data_atual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("INSERT OR REPLACE INTO historico_seguranca (alvo, tag_atchload, data_consulta) VALUES (?, ?, ?)", 
                   (url, tag, data_atual))
    conexao.commit()
    conexao.close()

def gerar_id_url_virustotal(url: str) -> str:
    return base64.urlsafe_b64encode(url.encode("utf-8")).decode("utf-8").strip("=")

def calcular_tag_atchload(malicious: int, suspicious: int) -> str:
    if malicious > 2: return "Perigoso"
    elif malicious > 0 or suspicious > 0: return "Inseguro"
    return "Seguro / Confiável"

inicializar_banco()

#  MÓDULO DE BUSCA  
WHITELIST = ["archive.org", "mediafire.com", "mega.nz", "drive.google.com", "pixeldrain.com", "gofile.io", "sendspace.com", "itch.io", "workupload.com", "1fichier.com", "sourceforge.net"]
SITES_MENCIONAVEIS = {"youtube": ["youtube.com"], "archive": ["archive.org"], "mega": ["mega.nz"], "mediafire": ["mediafire.com"], "drive": ["drive.google.com"], "github": ["github.com"], "itch": ["itch.io"]}
AD_SCRIPTS = ["googlesyndication.com", "doubleclick.net", "adnxs.com", "taboola.com", "outbrain.com"]
PALAVRAS_DOWNLOAD_HTML = ["mega.nz", "mediafire.com", "drive.google.com", "baixar agora", "download here"]
HEADERS = {"User-Agent": "Mozilla/5.0"}

def extrair_dominio(url):
    try: return urlparse(url).netloc.replace("www.", "")
    except: return ""

def analisar_pagina(url):
    try:
        r = requests.get(url, timeout=3, headers=HEADERS)
        html = r.text.lower()
        ads = len([s for s in AD_SCRIPTS if s in html])
        propaganda = "limpo" if ads == 0 else "moderado" if ads <= 2 else "agressivo"
        tem_download = any(p in html for p in PALAVRAS_DOWNLOAD_HTML)
        return propaganda, tem_download
    except: return "desconhecido", False

def calcular_score(r, query_lower, sites_mencionados):
    score = 40
    if r["tag_atchload"] == "Perigoso": return 0
    if r["tag_atchload"] == "Inseguro": score -= 30
    
    if r["dominio_limpo"] in WHITELIST: score += 20
    if r["download_direto"]: score += 20
    if r["propaganda"] == "limpo": score += 10
    elif r["propaganda"] == "agressivo": score -= 15
    
    return max(0, min(score, 100))

def processar_item(item, query, query_lower, sites_mencionados):
    link = item.get("link", "")
    dominio = extrair_dominio(link)
    propaganda, download_direto = analisar_pagina(link)
    tag_seguranca = buscar_cache_local(link)
    
    resultado = {
        "titulo": item.get("title", ""),
        "link": link,
        "dominio_limpo": dominio,
        "descricao": item.get("snippet", ""),
        "download_direto": download_direto,
        "propaganda": propaganda,
        "tag_atchload": tag_seguranca
    }
    
    resultado["score"] = calcular_score(resultado, query_lower, sites_mencionados)
    return resultado

@app.get("/buscar")
def buscar(q: str):
    r = requests.get("https://serpapi.com/search", params={"q": q, "api_key": SERPAPI_KEY, "num": 5})
    itens = r.json().get("organic_results", [])
    
    resultados = [processar_item(i, q, q.lower(), []) for i in itens]
    resultados.sort(key=lambda x: x['score'], reverse=True)
    return {"resultados": resultados}

@app.get("/verificar")
def verificar_url(url: str = Query(...)):
    url_id = gerar_id_url_virustotal(url)
    headers = {"x-apikey": VIRUSTOTAL_API_KEY}
    resp = requests.get(f"https://www.virustotal.com/api/v3/urls/{url_id}", headers=headers)
    
    if resp.status_code == 200:
        stats = resp.json()['data']['attributes']['last_analysis_stats']
        tag = calcular_tag_atchload(stats.get('malicious', 0), stats.get('suspicious', 0))
        salvar_no_banco(url, tag)
        return {"tag_atchload": tag}
    return {"tag_atchload": "Aguardando Análise"}