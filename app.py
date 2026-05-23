from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
import uvicorn
import config
import database
import ghl_client
from sdr_brain import SDRBrain
import datetime
import logging
import asyncio

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="SDR Autônomo B2B")
brain = SDRBrain()

from typing import Optional, Dict, Any

class LeadWebhook(BaseModel):
    contact_id: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    custom_fields: Optional[Dict[str, Any]] = {}
    channel: str = "WhatsApp"  # Default para WhatsApp, suporta SMS/Email

@app.get("/")
def read_root():
    return {"message": "SDR Autônomo B2B API está rodando!"}

def process_new_lead_task(lead: LeadWebhook):
    try:
        nome_dono = f"{lead.first_name or ''} {lead.last_name or ''}".strip() or "Dono(a)"
        nome_imobiliaria = lead.custom_fields.get("nome_imobiliaria", "Imobiliária")
        site = lead.custom_fields.get("site", "seu site")

        # Gera a mensagem para estágio 1
        lead_data = {
            "nome_dono": nome_dono,
            "nome_imobiliaria": nome_imobiliaria,
            "site": site
        }
        logger.info(f"Gerando mensagem de estágio 1 para {lead.contact_id}...")
        brain_response = brain.generate_message(lead_data, 1)
        msg = brain_response.get("reply_message", "")
        
        # Envia via GHL
        logger.info(f"Enviando mensagem para {lead.contact_id} via GHL...")
        success = ghl_client.send_ghl_message(lead.contact_id, msg, channel=lead.channel)
        if success:
            logger.info(f"Sucesso! Primeira mensagem enviada para o lead {lead.contact_id}.")
        else:
            logger.error(f"Falha ao enviar a primeira mensagem para {lead.contact_id}.")
            
    except Exception as e:
        logger.error(f"Erro na task de novo lead para {lead.contact_id}: {e}")

@app.post("/webhook/ghl-lead")
async def receive_ghl_lead(lead: LeadWebhook, background_tasks: BackgroundTasks):
    """
    Recebe um novo lead via Webhook do GHL.
    """
    nome_imobiliaria = lead.custom_fields.get("nome_imobiliaria", "Imobiliária")
    logger.info(f"Novo webhook recebido: Lead {lead.contact_id} ({nome_imobiliaria})")
    
    nome_dono = f"{lead.first_name or ''} {lead.last_name or ''}".strip() or "Dono(a)"
    site = lead.custom_fields.get("site", "seu site")

    # 1. Salvar/Atualizar no banco (Reseta para estágio 1 e active)
    database.insert_or_update_lead(
        ghl_contact_id=lead.contact_id,
        nome_dono=nome_dono,
        nome_imobiliaria=nome_imobiliaria,
        site=site,
        status="active"
    )
    
    # 2. Iniciar task em background para responder rápido ao GHL
    background_tasks.add_task(process_new_lead_task, lead)
    
    return {"status": "success", "message": "Lead salvo e processamento iniciado."}

class MessageWebhook(BaseModel):
    contact_id: str
    body: str
    type: str = "WhatsApp"
    direction: str = "inbound"

async def process_buffered_messages_task(contact_id: str, lead_data: dict):
    """
    Aguarda 8 segundos para garantir que o lead terminou de enviar mensagens.
    Se nenhuma nova mensagem chegar nesse período, agrupa o buffer e gera a resposta da IA.
    """
    logger.info(f"Iniciando timer de debounce de 8 segundos para o lead {contact_id}...")
    await asyncio.sleep(8)
    
    # Verifica se há mensagens no buffer
    last_timestamp_str = database.get_last_buffer_timestamp(contact_id)
    if not last_timestamp_str:
        logger.info(f"Sem mensagens no buffer para o lead {contact_id}. Task finalizada.")
        return
        
    try:
        last_timestamp = datetime.datetime.fromisoformat(last_timestamp_str)
        seconds_since_last_msg = (datetime.datetime.now() - last_timestamp).total_seconds()
        
        # Debounce: Se outra mensagem chegou durante a espera de 8s, o timestamp mudou.
        # Interrompe esta task de resposta antiga e deixa a task mais recente assumir.
        if seconds_since_last_msg < 7.5:
            logger.info(f"Mensagem mais recente detectada ({seconds_since_last_msg:.1f}s atrás). Abortando thread antiga.")
            return
            
        # O cliente parou de digitar!
        logger.info(f"Lead {contact_id} parou de digitar (último envio há {seconds_since_last_msg:.1f}s). Respondendo...")
        
        # Recupera as mensagens agrupadas e limpa o buffer
        full_user_message = database.get_and_clear_buffer(contact_id)
        if not full_user_message:
            return
            
        # Puxa o histórico de mensagens recente do GHL
        history = ghl_client.get_conversation_history(contact_id)
        
        # Garante que a mensagem agrupada do usuário está no final do histórico se não estiver lá
        if not history or history[-1]["content"] != full_user_message:
            history.append({"role": "user", "content": full_user_message})
            
        # Gera a resposta dinâmica e simpática do SDR
        brain_response = brain.generate_message(lead_data, history=history)
        msg = brain_response.get("reply_message", "")
        intent = brain_response.get("detected_intent", "active")
        agreed_time = brain_response.get("agreed_time", None)
        
        # Dispara via WhatsApp
        success = ghl_client.send_ghl_message(contact_id, msg, channel="WhatsApp")
        if success:
            logger.info(f"Resposta de IA enviada com sucesso para {contact_id}: '{msg}' [Intenção: {intent}]")
            
            # Lógica baseada na intenção detectada
            if intent == "meeting_scheduled":
                database.update_followup_stage(contact_id, 1, status="meeting_scheduled")
                lead_name = lead_data.get("nome_dono", "Lead")
                # Move para Reunião Marcada no GHL
                ghl_client.create_or_update_opportunity(contact_id, config.GHL_STAGE_REUNIAO_MARCADA_ID, lead_name)
                # Agenda o compromisso se houver horário acordado
                if agreed_time:
                    ghl_client.book_ghl_calendar_event(contact_id, agreed_time)
            elif intent == "nurture":
                database.update_followup_stage(contact_id, 1, status="nurture")
                lead_name = lead_data.get("nome_dono", "Lead")
                # Move para Nutrição no GHL
                ghl_client.create_or_update_opportunity(contact_id, config.GHL_STAGE_NUTRICAO_ID, lead_name)
            elif intent == "stopped":
                database.update_followup_stage(contact_id, 1, status="stopped")
            else:
                database.update_followup_stage(contact_id, 1, status="active")
        else:
            logger.error(f"Falha ao enviar resposta de IA para {contact_id}.")
            
    except Exception as e:
        logger.error(f"Erro ao processar buffer de mensagens do lead {contact_id}: {e}")

@app.post("/webhook/ghl-message")
async def receive_ghl_message(message: MessageWebhook, background_tasks: BackgroundTasks):
    """
    Recebe respostas do lead em tempo real do webhook de mensagens do GHL.
    """
    if message.direction != "inbound":
        return {"status": "ignored", "message": "Mensagem outbound ignorada."}
        
    logger.info(f"Novo webhook de mensagem recebido do lead {message.contact_id}: '{message.body}'")
    
    # 1. Adiciona a mensagem atual ao buffer
    database.add_to_buffer(message.contact_id, message.body)
    
    # 2. Carrega os dados cadastrais do lead
    lead_info = None
    leads = database.get_active_leads()
    for l in leads:
        if l['ghl_contact_id'] == message.contact_id:
            lead_info = l
            break
            
    if not lead_info:
        lead_info = {
            "nome_dono": "Cliente",
            "nome_imobiliaria": "Imobiliária",
            "site": "seu site"
        }
        
    # 3. Adiciona a tarefa em background para o processamento assíncrono com delay
    background_tasks.add_task(process_buffered_messages_task, message.contact_id, lead_info)
    
    return {"status": "success", "message": "Mensagem adicionada ao buffer de debounce."}

def execute_followups_task():
    logger.info("Iniciando cron job de follow-ups...")
    leads = database.get_active_leads()
    
    if not leads:
        logger.info("Nenhum lead ativo para follow-up no momento.")
        return
        
    for lead in leads:
        contact_id = lead['ghl_contact_id']
        current_stage = lead['followup_stage']
        last_date_str = lead['last_contact_date']
        
        try:
            last_date = datetime.datetime.fromisoformat(last_date_str)
            hours_passed = (datetime.datetime.now() - last_date).total_seconds() / 3600
        except Exception as e:
            logger.error(f"Erro ao ler data do lead {contact_id}: {e}")
            continue
            
        # Regra de 24 horas: só executa follow-up após 24h do último contato
        if hours_passed < 24:
            logger.debug(f"Lead {contact_id} ignorado (aguardando 24h, atual: {hours_passed:.1f}h).")
            continue
            
        # Verifica se o lead já respondeu a mensagem anterior
        logger.info(f"Verificando respostas do lead {contact_id} no GHL...")
        if ghl_client.check_if_replied(contact_id):
            logger.info(f"Lead {contact_id} respondeu! Iniciando conversa de duas vias...")
            
            # Puxa o histórico completo do GHL
            history = ghl_client.get_conversation_history(contact_id)
            
            # Gera a resposta com base no histórico
            lead_data = {
                "nome_dono": lead['nome_dono'],
                "nome_imobiliaria": lead['nome_imobiliaria'],
                "site": lead['site']
            }
            brain_response = brain.generate_message(lead_data, history=history)
            msg = brain_response.get("reply_message", "")
            intent = brain_response.get("detected_intent", "active")
            agreed_time = brain_response.get("agreed_time", None)
            
            # Responde de volta para manter o lead conversando e levá-lo à reunião
            success = ghl_client.send_ghl_message(contact_id, msg, channel="WhatsApp")
            
            if success:
                logger.info(f"Resposta de IA enviada com sucesso para o lead {contact_id} | Intenção: {intent}")
                
                # Lógica baseada na intenção detectada
                if intent == "meeting_scheduled":
                    database.update_followup_stage(contact_id, current_stage, status="meeting_scheduled")
                    ghl_client.create_or_update_opportunity(contact_id, config.GHL_STAGE_REUNIAO_MARCADA_ID, lead['nome_dono'])
                    if agreed_time:
                        ghl_client.book_ghl_calendar_event(contact_id, agreed_time)
                elif intent == "nurture":
                    database.update_followup_stage(contact_id, current_stage, status="nurture")
                    ghl_client.create_or_update_opportunity(contact_id, config.GHL_STAGE_NUTRICAO_ID, lead['nome_dono'])
                elif intent == "stopped":
                    database.update_followup_stage(contact_id, current_stage, status="stopped")
                else:
                    database.update_followup_stage(contact_id, current_stage, status="active")
            else:
                logger.error(f"Falha ao enviar resposta de IA para {contact_id}.")
            continue
            
        # Se não respondeu, avança estágio se menor que 9
        if current_stage >= 9:
            logger.info(f"Lead {contact_id} esgotou os 9 follow-ups. Marcando como 'stopped'.")
            database.update_followup_stage(contact_id, current_stage, status="stopped")
            continue
            
        next_stage = current_stage + 1
        logger.info(f"Gerando follow-up {next_stage}/9 para lead {contact_id}...")
        
        brain_response = brain.generate_message({
            "nome_dono": lead['nome_dono'],
            "nome_imobiliaria": lead['nome_imobiliaria'],
            "site": lead['site']
        }, next_stage)
        msg = brain_response.get("reply_message", "")
        
        # Envia a nova mensagem no mesmo canal (default WhatsApp)
        success = ghl_client.send_ghl_message(contact_id, msg, channel="WhatsApp")
        
        if success:
            database.update_followup_stage(contact_id, next_stage, status="active")
            logger.info(f"Follow-up {next_stage} disparado com sucesso para {contact_id}.")
        else:
            logger.error(f"Falha ao enviar follow-up {next_stage} para {contact_id}.")

@app.post("/cron/execute-followups")
async def cron_execute_followups(background_tasks: BackgroundTasks):
    """
    Endpoint para ser chamado pelo servidor (via cronjob ou schedule do GHL)
    uma vez por hora, ou por dia, para engatilhar as verificações e follow-ups.
    """
    background_tasks.add_task(execute_followups_task)
    return {"status": "success", "message": "Rotina de follow-ups enviada para processamento."}

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
