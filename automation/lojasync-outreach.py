#!/usr/bin/env python3
"""
LojaSync Outreach Bot - MVP
Bot de envio de pitch automatizado para leads capturados.
"""

import sqlite3
import json
import time
from datetime import datetime, timedelta
from pathlib import Path

# ===== CONFIGURAÇÕES =====
DATABASE_PATH = "/mnt/c/Users/user/Desktop/LojaSync/automation/leads.db"
LOG_PATH = "/mnt/c/Users/user/Desktop/LojaSync/automation/outreach_log.json"
DELAY_MIN = 2  # segundos entre mensagens
DELAY_MAX = 5  # segundos entre mensagens

# ===== PITCHS =====
PITCH_WHATSAPP = """Oi {nome}! Sua loja parece ter muitos produtos. O LojaSync automatiza cadastro de NFs e grades em minutos. Posso mostrar como funciona?"""

PITCH_LINKEDIN = """Olá {nome}, vi a {loja} e notei que vocês trabalham com uma boa quantidade de produtos. Criei o LojaSync para automatizar cadastro de notas fiscais e grades - de horas para minutos. Gostaria de ver uma demo rápida?"""

PITCH_INSTAGRAM = """Oi {nome}! Adorei o conteúdo da {loja}. Pelo volume, imagino que cadastro de produtos deve levar tempo. O LojaSync automatiza upload de NFs - quer ver como funciona?"""

FOLLOW_UP_24H = """Oi {nome}, viu minha mensagem? Posso te mandar um vídeo curto de 30s mostrando o LojaSync em ação."""

FOLLOW_UP_48H = """Última tentativa: se cadastro manual de produtos não é um problema agora, sem problemas. Se precisar no futuro, estou à disposição. Sucesso com a {loja}!"""

# ===== DATABASE =====
def get_leads_to_contact(limit=10):
    """Busca leads que ainda não foram contatados"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    # Buscar leads com score >= 5 e status 'novo' ou sem contato registrado
    cursor.execute("""
    SELECT * FROM leads
    WHERE score >= 5 AND status = 'novo'
    ORDER BY score DESC
    LIMIT ?
    """, (limit,))

    leads = cursor.fetchall()
    conn.close()

    return leads

def update_lead_status(lead_id, status):
    """Atualiza status do lead"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    cursor.execute("""
    UPDATE leads SET status = ? WHERE id = ?
    """, (status, lead_id))

    conn.commit()
    conn.close()

def log_outreach(lead_id, canal, mensagem, resultado):
    """Registra envio de mensagem"""
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "lead_id": lead_id,
        "canal": canal,
        "mensagem": mensagem,
        "resultado": resultado
    }

    # Carregar log existente
    try:
        with open(LOG_PATH, 'r', encoding='utf-8') as f:
            logs = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        logs = []

    logs.append(log_entry)

    # Salvar log
    with open(LOG_PATH, 'w', encoding='utf-8') as f:
        json.dump(logs, f, indent=2, ensure_ascii=False)

    return log_entry

# ===== MENSAGENS =====
def create_pitch(lead, canal="whatsapp"):
    """Cria pitch personalizado para lead"""
    # lead[0]=id, [1]=nome, [2]=loja, [3]=telefone, [4]=email, [5]=instagram, [6]=linkedin, [7]=website
    nome = lead[1] or "fornecedor(a)"
    loja = lead[2] or "sua loja"

    if canal == "whatsapp":
        return PITCH_WHATSAPP.format(nome=nome, loja=loja)
    elif canal == "linkedin":
        return PITCH_LINKEDIN.format(nome=nome, loja=loja)
    elif canal == "instagram":
        return PITCH_INSTAGRAM.format(nome=nome, loja=loja)
    else:
        return PITCH_WHATSAPP.format(nome=nome, loja=loja)

def send_whatsapp_message(lead, mensagem):
    """
    Envia mensagem via WhatsApp (simulado - precisa de CDP/Selenium)

    Na versão real, usaria WhatsApp Web com Selenium/Playwright:
    1. Navegar para web.whatsapp.com
    2. Buscar pelo número de telefone
    3. Clicar no chat
    4. Escrever e enviar mensagem
    """
    telefone = lead[3]

    print(f"[WHATSAPP] Simulando envio para {telefone}")
    print(f"  Mensagem: {mensagem[:50]}...")

    # Simulação de delay
    time.sleep(2)

    # Simulação de sucesso
    resultado = {
        "sucesso": True,
        "timestamp": datetime.now().isoformat(),
        "telefone": telefone,
        "canal": "whatsapp"
    }

    return resultado

def send_linkedin_connection(lead, mensagem):
    """
    Envia conexão no LinkedIn (simulado - precisa de CDP/Selenium)

    Na versão real, usaria LinkedIn com Selenium/Playwright:
    1. Navegar para linkedin.com/sales/search
    2. Filtrar por setor: Varejo, Moda, E-commerce
    3. Conectar + enviar mensagem personalizada
    """
    linkedin = lead[6]

    print(f"[LINKEDIN] Simulando conexão com {linkedin}")
    print(f"  Mensagem: {mensagem[:50]}...")

    # Simulação de delay
    time.sleep(2)

    # Simulação de sucesso
    resultado = {
        "sucesso": True,
        "timestamp": datetime.now().isoformat(),
        "linkedin": linkedin,
        "canal": "linkedin"
    }

    return resultado

def send_instagram_message(lead, mensagem):
    """
    Envia mensagem via Instagram (simulado - precisa de CDP/Selenium)

    Na versão real, usaria Instagram com Selenium/Playwright:
    1. Navegar para instagram.com
    2. Buscar perfil da loja
    3. Abrir DM
    4. Escrever e enviar mensagem
    """
    instagram = lead[5]

    print(f"[INSTAGRAM] Simulando mensagem para {instagram}")
    print(f"  Mensagem: {mensagem[:50]}...")

    # Simulação de delay
    time.sleep(2)

    # Simulação de sucesso
    resultado = {
        "sucesso": True,
        "timestamp": datetime.now().isoformat(),
        "instagram": instagram,
        "canal": "instagram"
    }

    return resultado

# ===== FOLLOW-UP =====
def process_follow_ups():
    """
    Processa follow-ups automáticos (24h e 48h após primeiro contato)

    Na versão real, verificaria log de outreach para leads que receberam
    primeira mensagem há 24h ou 48h e ainda não responderam.
    """
    print("[FOLLOW-UP] Verificando follow-ups pendentes...")

    # Carregar log de outreach
    try:
        with open(LOG_PATH, 'r', encoding='utf-8') as f:
            logs = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        print("[FOLLOW-UP] Nenhum log encontrado. Nenhum follow-up necessário.")
        return

    # Calcular thresholds de tempo
    agora = datetime.now()
    threshold_24h = agora - timedelta(hours=24)
    threshold_48h = agora - timedelta(hours=48)

    follow_ups_24h = 0
    follow_ups_48h = 0

    for log in logs:
        if log.get("resultado", {}).get("sucesso"):
            timestamp = datetime.fromisoformat(log["timestamp"])

            # Follow-up 24h
            if timestamp <= threshold_24h and timestamp > threshold_48h:
                follow_ups_24h += 1

            # Follow-up 48h
            elif timestamp <= threshold_48h:
                follow_ups_48h += 1

    print(f"[FOLLOW-UP] {follow_ups_24h} leads elegíveis para follow-up 24h")
    print(f"[FOLLOW-UP] {follow_ups_48h} leads elegíveis para follow-up 48h")

# ===== MAIN =====
def main(max_messages=5):
    """Executa bot de outreach"""
    print("=" * 60)
    print("LojaSync Outreach Bot - MVP")
    print("=" * 60)
    print()

    # Verificar follow-ups pendentes
    process_follow_ups()
    print()

    # Buscar leads para contato
    leads = get_leads_to_contact(limit=max_messages)

    if not leads:
        print("Nenhum lead elegível para contato encontrado.")
        print("Execute o crawler primeiro para gerar leads.")
        return

    print(f"Encontrados {len(leads)} leads para contato.")
    print()

    # Enviar mensagens
    for i, lead in enumerate(leads, 1):
        lead_id = lead[0]
        nome = lead[1]
        loja = lead[2]
        score = lead[8]

        print(f"[{i}/{len(leads)}] Processando lead: {loja} (score: {score})")

        # Determinar canal (WhatsApp tem prioridade)
        if lead[3]:  # telefone
            canal = "whatsapp"
            pitch = create_pitch(lead, canal="whatsapp")
            resultado = send_whatsapp_message(lead, pitch)
        elif lead[6]:  # linkedin
            canal = "linkedin"
            pitch = create_pitch(lead, canal="linkedin")
            resultado = send_linkedin_connection(lead, pitch)
        elif lead[5]:  # instagram
            canal = "instagram"
            pitch = create_pitch(lead, canal="instagram")
            resultado = send_instagram_message(lead, pitch)
        else:
            print(f"  ✗ Lead sem canal de contato válido. Pulando.")
            continue

        # Atualizar status do lead
        if resultado["sucesso"]:
            update_lead_status(lead_id, "contatado")
            log_outreach(lead_id, canal, pitch, resultado)
            print(f"  ✓ Lead marcado como 'contatado'")
        else:
            print(f"  ✗ Erro ao enviar. Lead permanece com status 'novo'")

        # Delay entre mensagens (anti-spam)
        if i < len(leads):
            delay = time.sleep(2 + (i % 3))  # 2-4 segundos simulado
            print()

    print()
    print("=" * 60)
    print("RELATÓRIO FINAL")
    print("=" * 60)
    print(f"Total de leads contatados: {len(leads)}")
    print(f"Logs salvos em: {LOG_PATH}")
    print()

    # Estatísticas
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM leads WHERE status = 'contatado'")
    contatados = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM leads WHERE status = 'novo'")
    novos = cursor.fetchone()[0]

    conn.close()

    print(f"Leads contatados (total): {contatados}")
    print(f"Leads ainda não contatados: {novos}")
    print("=" * 60)
    print("NOTA: Esta versão é um MVP simulado.")
    print("Para funcionar em produção, precisa de:")
    print("  - pip install selenium playwright")
    print("  - Chrome CDP configurado (porta 9333)")
    print("  - Contas ativas em WhatsApp, LinkedIn, Instagram")
    print("=" * 60)

if __name__ == "__main__":
    main(max_messages=3)
