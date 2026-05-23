# Armazena chaves da Anthropic, GHL e Webhooks
import os

# Puxa as chaves das Variáveis de Ambiente do Sistema (Segurança Máxima)
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
GHL_API_KEY = os.getenv("GHL_API_KEY", "")
GHL_LOCATION_ID = os.getenv("GHL_LOCATION_ID", "")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "")

# Configurações de Funil e Agendamento do GHL
GHL_PIPELINE_ID = os.getenv("GHL_PIPELINE_ID", "")
GHL_STAGE_REUNIAO_MARCADA_ID = os.getenv("GHL_STAGE_REUNIAO_MARCADA_ID", "")
GHL_STAGE_NUTRICAO_ID = os.getenv("GHL_STAGE_NUTRICAO_ID", "")
GHL_CALENDAR_ID = os.getenv("GHL_CALENDAR_ID", "")
