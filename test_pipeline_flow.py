import unittest
from unittest.mock import patch, MagicMock
import asyncio
import sys

# Garante UTF-8 no terminal
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

# Importa os módulos do projeto
import config
import database
import ghl_client
import app
from sdr_brain import SDRBrain

class TestPipelineFlow(unittest.TestCase):
    
    @patch('app.ghl_client')
    @patch('app.database')
    @patch('app.brain')
    def test_active_intent_flow(self, mock_brain, mock_database, mock_ghl):
        """
        Caso A: O lead responde de forma normal (fluxo ativo).
        Garante que a mensagem é enviada e o status permanece 'active'.
        """
        print("\n🧪 Testando Caso A: Intenção 'active' (Conversa em andamento)...")
        
        # 1. Configura mocks
        contact_id = "contact_active_123"
        lead_data = {
            "nome_dono": "Carlos",
            "nome_imobiliaria": "A Imóveis",
            "site": "aimoveis.com"
        }
        
        # Simula o buffer de mensagens com timestamp
        mock_database.get_last_buffer_timestamp.return_value = "2026-05-22T18:00:00"
        mock_database.get_and_clear_buffer.return_value = "Quero entender como funciona."
        mock_ghl.get_conversation_history.return_value = []
        
        # Simula o cérebro retornando 'active'
        mock_brain.generate_message.return_value = {
            "reply_message": "Legal Carlos! Vcs focam mais em alto padrão?",
            "detected_intent": "active",
            "agreed_time": None
        }
        
        mock_ghl.send_ghl_message.return_value = True
        
        # 2. Executa a tarefa em background de processamento de mensagens
        # Como é uma função assíncrona, rodamos via event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Patch datetime para evitar que o debounce de 8 segundos aborte a thread no test_pipeline_flow
        with patch('datetime.datetime') as mock_date:
            # Simula que o tempo passou e o debounce de 8 segundos foi satisfeito
            mock_date.now.return_value = MagicMock()
            mock_date.fromisoformat.return_value = MagicMock()
            # Diferença de tempo grande para satisfazer o debounce
            (mock_date.now.return_value - mock_date.fromisoformat.return_value).total_seconds.return_value = 10.0
            
            loop.run_until_complete(app.process_buffered_messages_task(contact_id, lead_data))
            
        loop.close()
        
        # 3. Asserções
        mock_brain.generate_message.assert_called_once()
        mock_ghl.send_ghl_message.assert_called_once_with(contact_id, "Legal Carlos! Vcs focam mais em alto padrão?", channel="WhatsApp")
        mock_database.update_followup_stage.assert_called_once_with(contact_id, 1, status="active")
        
        # Garante que não chamou movimentação de pipeline nem calendário
        mock_ghl.create_or_update_opportunity.assert_not_called()
        mock_ghl.book_ghl_calendar_event.assert_not_called()
        
        print("✅ Sucesso! O lead continuou ativo no funil.")

    @patch('app.ghl_client')
    @patch('app.database')
    @patch('app.brain')
    def test_meeting_scheduled_intent_flow(self, mock_brain, mock_database, mock_ghl):
        """
        Caso B: O lead aceita e agenda a reunião.
        Garante que o lead é movido no pipeline comercial e a reunião é agendada no calendário.
        """
        print("\n🧪 Testando Caso B: Intenção 'meeting_scheduled' (Reunião Marcada)...")
        
        contact_id = "contact_meeting_123"
        lead_data = {
            "nome_dono": "Carlos",
            "nome_imobiliaria": "A Imóveis",
            "site": "aimoveis.com"
        }
        
        mock_database.get_last_buffer_timestamp.return_value = "2026-05-22T18:00:00"
        mock_database.get_and_clear_buffer.return_value = "Pode ser hoje às 17h30 sim."
        mock_ghl.get_conversation_history.return_value = []
        
        # Simula o cérebro detectando agendamento para 17:30
        mock_brain.generate_message.return_value = {
            "reply_message": "Show de bola Carlos! Já deixei reservado aqui hoje às 17h30. Te ligo na hora 👍",
            "detected_intent": "meeting_scheduled",
            "agreed_time": "17:30"
        }
        
        mock_ghl.send_ghl_message.return_value = True
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        with patch('datetime.datetime') as mock_date:
            mock_date.now.return_value = MagicMock()
            mock_date.fromisoformat.return_value = MagicMock()
            (mock_date.now.return_value - mock_date.fromisoformat.return_value).total_seconds.return_value = 10.0
            
            loop.run_until_complete(app.process_buffered_messages_task(contact_id, lead_data))
            
        loop.close()
        
        # Asserções
        mock_database.update_followup_stage.assert_called_once_with(contact_id, 1, status="meeting_scheduled")
        
        # Garante que moveu o lead no GHL para Reunião Marcada
        mock_ghl.create_or_update_opportunity.assert_called_once_with(
            contact_id, config.GHL_STAGE_REUNIAO_MARCADA_ID, "Carlos"
        )
        # Garante que marcou no Calendário GHL
        mock_ghl.book_ghl_calendar_event.assert_called_once_with(contact_id, "17:30")
        
        print("✅ Sucesso! O lead foi movido para 'Reunião Marcada' e a agenda foi reservada.")

    @patch('app.ghl_client')
    @patch('app.database')
    @patch('app.brain')
    def test_nurture_intent_flow(self, mock_brain, mock_database, mock_ghl):
        """
        Caso C: O lead pede material ou adia (Nutrição).
        Garante que o lead é movido para o estágio de Nutrição no pipeline comercial.
        """
        print("\n🧪 Testando Caso C: Intenção 'nurture' (Direcionado para Nutrição)...")
        
        contact_id = "contact_nurture_123"
        lead_data = {
            "nome_dono": "Carlos",
            "nome_imobiliaria": "A Imóveis",
            "site": "aimoveis.com"
        }
        
        mock_database.get_last_buffer_timestamp.return_value = "2026-05-22T18:00:00"
        mock_database.get_and_clear_buffer.return_value = "Agora não posso, me manda um material por email."
        mock_ghl.get_conversation_history.return_value = []
        
        # Simula o cérebro detectando nutrição
        mock_brain.generate_message.return_value = {
            "reply_message": "Sem problemas! Te mandei o material no seu e-mail. Se quiser trocar uma ideia depois, só chamar",
            "detected_intent": "nurture",
            "agreed_time": None
        }
        
        mock_ghl.send_ghl_message.return_value = True
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        with patch('datetime.datetime') as mock_date:
            mock_date.now.return_value = MagicMock()
            mock_date.fromisoformat.return_value = MagicMock()
            (mock_date.now.return_value - mock_date.fromisoformat.return_value).total_seconds.return_value = 10.0
            
            loop.run_until_complete(app.process_buffered_messages_task(contact_id, lead_data))
            
        loop.close()
        
        # Asserções
        mock_database.update_followup_stage.assert_called_once_with(contact_id, 1, status="nurture")
        
        # Garante que moveu o lead no GHL para Nutrição
        mock_ghl.create_or_update_opportunity.assert_called_once_with(
            contact_id, config.GHL_STAGE_NUTRICAO_ID, "Carlos"
        )
        mock_ghl.book_ghl_calendar_event.assert_not_called()
        
        print("✅ Sucesso! O lead foi movido para 'Nutrição' no GHL.")

if __name__ == '__main__':
    unittest.main()
