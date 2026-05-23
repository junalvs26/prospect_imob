import requests
import config
import logging
import database

logger = logging.getLogger(__name__)

HEADERS = {
    "Authorization": f"Bearer {config.GHL_API_KEY}",
    "Version": "2021-07-28",
    "Content-Type": "application/json",
    "Accept": "application/json"
}

BASE_URL = "https://services.leadconnectorhq.com"

def send_ghl_message(contact_id: str, message: str, channel: str = "WhatsApp"):
    """
    Envia uma mensagem via GHL (SMS, WhatsApp ou Email).
    """
    url = f"{BASE_URL}/conversations/messages"
    payload = {
        "contactId": contact_id,
        "type": channel,
        "message": message
    }
    
    try:
        response = requests.post(url, json=payload, headers=HEADERS)
        response.raise_for_status()
        logger.info(f"Mensagem enviada para {contact_id} via {channel}.")
        return True
    except Exception as e:
        logger.error(f"Erro ao enviar mensagem para GHL: {e}")
        if 'response' in locals() and hasattr(response, 'text'):
            logger.error(f"GHL Response: {response.text}")
        return False

def check_if_replied(contact_id: str) -> bool:
    """
    Verifica no GHL se o cliente respondeu a última mensagem.
    Retorna True se respondeu, False caso contrário.
    Se respondeu, atualiza o status no DB para 'replied'.
    """
    url = f"{BASE_URL}/conversations/search?contactId={contact_id}"
    try:
        conv_response = requests.get(url, headers=HEADERS)
        conv_response.raise_for_status()
        conversations = conv_response.json().get("conversations", [])
        
        if not conversations:
            return False
            
        # Pega o ID da conversa mais recente
        conversation_id = conversations[0].get("id")
        
        # Busca as mensagens da conversa ordenadas (limite 1 para pegar a mais recente)
        msg_url = f"{BASE_URL}/conversations/{conversation_id}/messages?limit=1"
        msg_response = requests.get(msg_url, headers=HEADERS)
        msg_response.raise_for_status()
        messages = msg_response.json().get("messages", [])
        
        if messages:
            last_message = messages[0]
            # 'inbound' = mensagem recebida do lead
            if last_message.get("direction") == "inbound":
                logger.info(f"Lead {contact_id} respondeu! Marcando como 'replied'.")
                
                # Atualizar o banco de dados diretamente para interromper automação
                import sqlite3
                conn = sqlite3.connect(database.DB_NAME)
                cursor = conn.cursor()
                cursor.execute("UPDATE leads SET status = 'replied' WHERE ghl_contact_id = ?", (contact_id,))
                conn.commit()
                conn.close()
                
                return True
                
        return False
    except Exception as e:
        logger.error(f"Erro ao verificar resposta no GHL para {contact_id}: {e}")
        return False

def get_conversation_history(contact_id: str, limit: int = 6) -> list:
    """
    Busca o histórico de mensagens da conversa mais recente do lead no GHL
    e formata no padrão esperado pela IA: [{"role": "user"/"assistant", "content": "..."}]
    """
    url = f"{BASE_URL}/conversations/search?contactId={contact_id}"
    try:
        conv_response = requests.get(url, headers=HEADERS)
        conv_response.raise_for_status()
        conversations = conv_response.json().get("conversations", [])
        
        if not conversations:
            return []
            
        conversation_id = conversations[0].get("id")
        msg_url = f"{BASE_URL}/conversations/{conversation_id}/messages?limit={limit}"
        msg_response = requests.get(msg_url, headers=HEADERS)
        msg_response.raise_for_status()
        messages = msg_response.json().get("messages", [])
        
        history = []
        if messages:
            # As mensagens do GHL vêm da mais nova para a mais antiga, invertemos
            for msg in reversed(messages):
                direction = msg.get("direction")
                body = msg.get("body", "").strip()
                if body:
                    role = "user" if direction == "inbound" else "assistant"
                    history.append({"role": role, "content": body})
        return history
    except Exception as e:
        logger.error(f"Erro ao buscar histórico no GHL para {contact_id}: {e}")
        return []

def create_or_update_opportunity(contact_id: str, stage_id: str, lead_name: str = "Lead SDR"):
    """
    Busca se o lead já possui uma oportunidade no GHL.
    Se sim, move ela para o estágio especificado.
    Se não, cria uma nova oportunidade no pipeline e estágio configurados.
    """
    # 1. Buscar oportunidades existentes para o contato
    search_url = f"{BASE_URL}/opportunities/search?contactId={contact_id}"
    opportunity_id = None
    
    try:
        response = requests.get(search_url, headers=HEADERS)
        response.raise_for_status()
        opportunities = response.json().get("opportunities", [])
        if opportunities:
            opportunity_id = opportunities[0].get("id")
            logger.info(f"Oportunidade existente encontrada: {opportunity_id}")
    except Exception as e:
        logger.warning(f"Não foi possível buscar oportunidades para {contact_id} (talvez não exista nenhuma ainda): {e}")

    # 2. Atualizar ou Criar
    if opportunity_id:
        # Atualiza estágio da existente
        url = f"{BASE_URL}/opportunities/{opportunity_id}"
        payload = {
            "pipelineStageId": stage_id,
            "status": "open"
        }
        try:
            res = requests.put(url, json=payload, headers=HEADERS)
            res.raise_for_status()
            logger.info(f"Oportunidade {opportunity_id} movida com sucesso para o estágio {stage_id}.")
            return True
        except Exception as e:
            logger.error(f"Erro ao mover oportunidade {opportunity_id} para o estágio {stage_id}: {e}")
            if 'res' in locals() and hasattr(res, 'text'):
                logger.error(f"GHL Response error: {res.text}")
            return False
    else:
        # Cria uma nova oportunidade
        url = f"{BASE_URL}/opportunities/"
        payload = {
            "pipelineId": config.GHL_PIPELINE_ID,
            "pipelineStageId": stage_id,
            "contactId": contact_id,
            "name": f"Oportunidade: {lead_name}",
            "status": "open"
        }
        try:
            res = requests.post(url, json=payload, headers=HEADERS)
            res.raise_for_status()
            logger.info(f"Nova oportunidade criada para o lead {contact_id} no estágio {stage_id}.")
            return True
        except Exception as e:
            logger.error(f"Erro ao criar nova oportunidade para o lead {contact_id}: {e}")
            if 'res' in locals() and hasattr(res, 'text'):
                logger.error(f"GHL Response error: {res.text}")
            return False

def book_ghl_calendar_event(contact_id: str, agreed_time_str: str, timezone_offset: str = "-03:00") -> bool:
    """
    Agenda um compromisso de 15 minutos no calendário do GHL com base no horário combinado (ex: '17:30').
    Calcula o datetime com base no dia de hoje.
    """
    import datetime
    try:
        # Tenta extrair hora e minuto
        # Ex: "17:30" -> hour=17, minute=30
        if ":" not in agreed_time_str:
            logger.error(f"Formato de horário inválido para agendamento: '{agreed_time_str}'")
            return False
            
        time_parts = agreed_time_str.split(":")
        hour = int(time_parts[0].strip())
        minute = int(time_parts[1].strip()[:2]) # Pega os dois primeiros dígitos em caso de "17:30h"
        
        # Constrói o datetime de hoje no horário especificado
        today = datetime.date.today()
        start_dt = datetime.datetime.combine(today, datetime.time(hour, minute))
        end_dt = start_dt + datetime.timedelta(minutes=15)
        
        # Formata em ISO 8601 com timezone offset
        # Ex: "2026-05-22T17:30:00-03:00"
        start_iso = f"{start_dt.isoformat()}{timezone_offset}"
        end_iso = f"{end_dt.isoformat()}{timezone_offset}"
        
        url = f"{BASE_URL}/calendars/events/appointments"
        payload = {
            "calendarId": config.GHL_CALENDAR_ID,
            "contactId": contact_id,
            "startTime": start_iso,
            "endTime": end_iso,
            "title": "Reunião de Diagnóstico (IA)",
            "selectedTimezone": "America/Sao_Paulo"
        }
        
        res = requests.post(url, json=payload, headers=HEADERS)
        res.raise_for_status()
        logger.info(f"Reunião agendada com sucesso no calendário para {start_iso}.")
        return True
    except Exception as e:
        logger.error(f"Erro ao agendar compromisso no calendário GHL para {contact_id}: {e}")
        if 'res' in locals() and hasattr(res, 'text'):
            logger.error(f"GHL Response error: {res.text}")
        return False

