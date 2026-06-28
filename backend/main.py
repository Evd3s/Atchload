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

SERPAPI_KEY = os.getenv("SERPAPI_KEY")
VIRUSTOTAL_API_KEY = os.getenv("VIRUSTOTAL_API_KEY")
NOME_BANCO = "atchload.db"

# --- MÓDULO DE SEGURANÇA E BANCO DE DADOS ---
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
    # Lógica refinada para lidar com Falsos Positivos
    if malicious >= 3: 
        return "Perigoso"
    elif malicious >= 1 or suspicious > 2: 
        return "Alerta de Cuidado"
    return "Seguro / Confiável"

inicializar_banco()

# --- MÓDULO DE BUSCA E ANÁLISE ---
WHITELIST = ["archive.org", "mediafire.com", "mega.nz", "drive.google.com", "pixeldrain.com", "gofile.io", "sendspace.com", "itch.io", "workupload.com", "1fichier.com", "sourceforge.net"]
SITES_MENCIONAVEIS = {"youtube": ["youtube.com"], "archive": ["archive.org"], "mega": ["mega.nz"], "mediafire": ["mediafire.com"], "drive": ["drive.google.com"], "github": ["github.com"], "itch": ["itch.io"]}

AD_SCRIPTS = [
    "googlesyndication.com", "doubleclick.net", "googleadservices.com",
    "adnxs.com", "taboola.com", "outbrain.com", "propellerads.com",
    "popads.net", "adcash.com", "exoclick.com", "onclickads.net",
    "adsterra.com", "mgid.com"
]

PALAVRAS_DOWNLOAD_HTML = ["mega.nz", "mediafire.com", "drive.google.com", "baixar agora", "download here"]
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

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

def calcular_score(r):
    score = 40
    # Ajuste do Score baseado na nova tag
    if r["tag_atchload"] == "Perigoso": return 0
    if r["tag_atchload"] == "Alerta de Cuidado": score -= 15 # Penalidade menor por ser possível falso positivo
    
    SITES_INFORMATIVOS = ["imdb.com", "wikipedia.org", "adorocinema.com", "play.google.com"]
    if r["dominio_limpo"] in SITES_INFORMATIVOS: score += 20
    
    if r["dominio_limpo"] in WHITELIST: score += 20
    if r["download_direto"]: score += 20
    
    if r["propaganda"] == "limpo": score += 10
    elif r["propaganda"] == "agressivo": score -= 15
    
    return max(0, min(score, 100))

def processar_item(item):
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
    
    resultado["score"] = calcular_score(resultado)
    return resultado

@app.get("/buscar")
def buscar(q: str):
    try:
        r = requests.get("https://serpapi.com/search", params={"q": q, "api_key": SERPAPI_KEY, "num": 5})
        itens = r.json().get("organic_results", [])
    except:
        itens = []
    
    resultados = []
    with ThreadPoolExecutor(max_workers=5) as executor:
        futuros = {executor.submit(processar_item, item): item for item in itens}
        for futuro in as_completed(futuros):
            resultados.append(futuro.result())
            
    resultados.sort(key=lambda x: x['score'], reverse=True)
    return {"resultados": resultados}

@app.get("/verificar")
def verificar_url(url: str = Query(...)):
    cache = buscar_cache_local(url)
    if cache != "Aguardando Análise" and cache != "Enviado ao VT": 
        return {"tag_atchload": cache}
    
    url_id = gerar_id_url_virustotal(url)
    headers = {"x-apikey": VIRUSTOTAL_API_KEY}
    
    resp = requests.get(f"https://www.virustotal.com/api/v3/urls/{url_id}", headers=headers)
    
    if resp.status_code == 404:
        post_headers = {
            "x-apikey": VIRUSTOTAL_API_KEY,
            "accept": "application/json",
            "content-type": "application/x-www-form-urlencoded"
        }
        requests.post("https://www.virustotal.com/api/v3/urls", headers=post_headers, data={"url": url})
        
        salvar_no_banco(url, "Enviado ao VT")
        return {"tag_atchload": "Enviado ao VT"}
    
    if resp.status_code == 200:
        stats = resp.json()['data']['attributes']['last_analysis_stats']
        m, s = stats.get('malicious', 0), stats.get('suspicious', 0)
        tag = calcular_tag_atchload(m, s)
        salvar_no_banco(url, tag)
        return {"tag_atchload": tag}
        
    return {"tag_atchload": "Erro na API"}