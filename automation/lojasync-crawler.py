#!/usr/bin/env python3
"""
LojaSync Crawler - MVP usando urllib básico
Versão inicial que estrutura o sistema de leads e qualificação.
"""

import urllib.request
import urllib.parse
import json
import sqlite3
import re
import time
from datetime import datetime
from urllib.error import URLError, HTTPError

# ===== CONFIGURAÇÕES =====
DATABASE_PATH = "/mnt/c/Users/user/Desktop/LojaSync/automation/leads.db"
DELAY_BETWEEN_REQUESTS = 2  # segundos

# ===== SINAIS DE QUALIFICAÇÃO =====
QUALIFICATION_SIGNALS = [
    "cadastro", "lançamento", "coleção", "nova coleção",
    "grade", "romaneio", "erp", "sistema",
    "venda", "ecommerce", "loja online"
]

# ===== DATABASE =====
def create_database():
    """Cria banco de dados SQLite com schema de leads"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS leads (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT,
        loja TEXT,
        telefone TEXT,
        email TEXT,
        instagram TEXT,
        linkedin TEXT,
        website TEXT,
        evidencia_dor TEXT,
        score INTEGER,
        data_captura TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        canal_origem TEXT,
        status TEXT DEFAULT 'novo'
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS crawler_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        fonte TEXT,
        resultado TEXT,
        mensagem TEXT
    )
    """)

    conn.commit()
    conn.close()
    print(f"✓ Database criado/verificado em {DATABASE_PATH}")

def insert_lead(lead_data):
    """Insere lead no banco de dados"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO leads (nome, loja, telefone, email, instagram, linkedin, website,
                       evidencia_dor, score, canal_origem)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        lead_data.get('nome'),
        lead_data.get('loja'),
        lead_data.get('telefone'),
        lead_data.get('email'),
        lead_data.get('instagram'),
        lead_data.get('linkedin'),
        lead_data.get('website'),
        lead_data.get('evidencia_dor'),
        lead_data.get('score', 0),
        lead_data.get('canal_origem')
    ))

    conn.commit()
    conn.close()

def log_crawler(fonte, resultado, mensagem):
    """Registra atividade do crawler"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO crawler_log (fonte, resultado, mensagem)
    VALUES (?, ?, ?)
    """, (fonte, resultado, mensagem))

    conn.commit()
    conn.close()

# ===== QUALIFICAÇÃO =====
def qualify_text(text):
    """Analisa texto para detectar sinais de dor de cadastro manual"""
    if not text:
        return {"tem_dor": False, "evidencias": [], "score": 0}

    text_lower = text.lower()
    evidencias = []

    for sinal in QUALIFICATION_SIGNALS:
        if sinal in text_lower:
            evidencias.append(sinal)

    tem_dor = len(evidencias) >= 1
    score = min(len(evidencias) * 2, 10)  # máximo 10 pontos

    return {
        "tem_dor": tem_dor,
        "evidencias": evidencias,
        "score": score
    }

# ===== CRAWLER (MVP usando urllib) =====
def fetch_page(url, timeout=10):
    """Busca página usando urllib básico"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        req = urllib.request.Request(url, headers=headers)
        response = urllib.request.urlopen(req, timeout=timeout)
        return response.read().decode('utf-8', errors='ignore')
    except (URLError, HTTPError, Exception) as e:
        print(f"Erro ao buscar {url}: {e}")
        return None

def crawl_google_maps(keyword, location="São Paulo", limit=10):
    """
    Crawler MVP para Google Maps (simulado - precisa de CDP/Selenium para real)

    Na versão real, usaria Chrome CDP para extrair:
    - Nome da loja
    - Telefone
    - Website
    - Endereço

    Esta versão é um placeholder que demonstra a estrutura.
    """
    print(f"[CRAWLER] Buscando '{keyword}' em {location} (simulado)")

    # Simulação - na versão real isso buscaria dados reais do Google Maps
    leads_simulados = [
        {
            "nome": "Loja Modelo 1",
            "loja": "Boutique Fashion",
            "telefone": "(11) 99999-0001",
            "email": "contato@boutique1.com.br",
            "instagram": "@boutique1",
            "linkedin": "",
            "website": "https://boutique1.com.br",
            "evidencia_dor": "Mencionou cadastro manual de coleção",
            "score": 6,
            "canal_origem": "google-maps"
        },
        {
            "nome": "Loja Modelo 2",
            "loja": "Fashion Store",
            "telefone": "(11) 99999-0002",
            "email": "fashion@store.com.br",
            "instagram": "@fashionstore",
            "linkedin": "",
            "website": "https://fashionstore.com.br",
            "evidencia_dor": "Sistema de ERP romaneio mencionado",
            "score": 8,
            "canal_origem": "google-maps"
        }
    ]

    for lead in leads_simulados[:limit]:
        insert_lead(lead)
        print(f"  ✓ Lead inserido: {lead['loja']} (score: {lead['score']})")
        time.sleep(0.5)  # Delay para simular crawler real

    log_crawler("google-maps", "sucesso", f"{len(leads_simulados)} leads simulados")

def crawl_instagram(hashtag, limit=10):
    """
    Crawler MVP para Instagram (simulado - precisa de CDP/Selenium para real)

    Na versão real, usaria Chrome CDP para extrair perfis de lojas.
    """
    print(f"[CRAWLER] Buscando Instagram com hashtag #{hashtag} (simulado)")

    # Simulação - na versão real isso buscaria dados reais do Instagram
    leads_simulados = [
        {
            "nome": "Instagram Lead 1",
            "loja": "Moda Trends",
            "telefone": "",
            "email": "",
            "instagram": "@modatrends",
            "linkedin": "",
            "website": "",
            "evidencia_dor": "Post sobre lançamento de coleção",
            "score": 4,
            "canal_origem": "instagram"
        }
    ]

    for lead in leads_simulados[:limit]:
        insert_lead(lead)
        print(f"  ✓ Lead inserido: {lead['loja']} (score: {lead['score']})")
        time.sleep(0.5)

    log_crawler("instagram", "sucesso", f"{len(leads_simulados)} leads simulados")

# ===== LLM DE QUALIFICAÇÃO (PLACEHOLDER) =====
def llm_qualify_lead(lead_info):
    """
    Usa LLM para qualificar lead com base em informações do site/rede social.

    Na versão real, chamaria API de LLM (OpenAI, Claude, etc.)
    """
    prompt = f"""
    Esta loja parece ter problema de cadastro manual de produtos?

    Loja: {lead_info.get('loja', '')}
    Site: {lead_info.get('website', '')}
    Instagram: {lead_info.get('instagram', '')}
    Descrição: {lead_info.get('evidencia_dor', '')}

    Responda: SIM/COM BASE EM EVIDÊNCIA/SEM EVIDÊNCIA e justifique em 1 frase.
    """

    # Simulação - na versão real chamaria API de LLM
    print(f"[LLM] Analisando lead: {lead_info.get('loja')}")
    return {
        "decisao": "SIM",
        "justificativa": "Mencionou lançamento de coleção e sistema de cadastro",
        "score_ajustado": 7
    }

# ===== MAIN =====
def main():
    """Executa crawler completo"""
    print("=" * 60)
    print("LojaSync Crawler - MVP")
    print("=" * 60)
    print()

    # Criar database
    create_database()
    print()

    # Executar crawlers
    print("--- CRAWLING GOOGLE MAPS ---")
    crawl_google_maps("roupa feminina boutique", "São Paulo", limit=5)
    print()

    print("--- CRAWLING INSTAGRAM ---")
    crawl_instagram("moda", limit=3)
    print()

    # Qualificar leads com LLM (simulado)
    print("--- QUALIFICAÇÃO LLM ---")
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM leads LIMIT 5")
    leads = cursor.fetchall()

    for lead in leads:
        lead_info = {
            "id": lead[0],
            "loja": lead[2],
            "website": lead[7],
            "instagram": lead[5],
            "evidencia_dor": lead[8]
        }
        qualificacao = llm_qualify_lead(lead_info)
        print(f"  Lead {lead_info['loja']}: {qualificacao['decisao']} - {qualificacao['justificativa']}")

    conn.close()
    print()

    # Relatório final
    print("=" * 60)
    print("RELATÓRIO FINAL")
    print("=" * 60)

    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM leads")
    total_leads = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM leads WHERE score >= 5")
    leads_qualificados = cursor.fetchone()[0]

    cursor.execute("SELECT AVG(score) FROM leads")
    avg_score = cursor.fetchone()[0] or 0

    print(f"Total de leads: {total_leads}")
    print(f"Leads qualificados (score >= 5): {leads_qualificados}")
    print(f"Score médio: {avg_score:.1f}")
    print()

    # Mostrar top leads
    cursor.execute("SELECT * FROM leads ORDER BY score DESC LIMIT 5")
    top_leads = cursor.fetchall()

    print("Top 5 leads:")
    for lead in top_leads:
        print(f"  [{lead[8]}/10] {lead[2]} - {lead[8]}")

    conn.close()

    print("=" * 60)
    print("NOTA: Esta versão é um MVP simulado.")
    print("Para funcionar em produção, precisa de:")
    print("  - pip install selenium playwright")
    print("  - Chrome CDP configurado (porta 9333)")
    print("  - API de LLM (OpenAI, Claude, etc.)")
    print("=" * 60)

if __name__ == "__main__":
    main()
