# Armazena chaves da Anthropic, GHL e Webhooks
import os

ANTHROPIC_API_KEY = "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"
GHL_API_KEY = "pit-b5558a5a-c91f-4385-bc89-4da28c518986"
GHL_LOCATION_ID = os.getenv("GHL_LOCATION_ID", "")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "")

# Configurações de Funil e Agendamento do GHL
GHL_PIPELINE_ID = os.getenv("GHL_PIPELINE_ID", "default_pipeline_id")
GHL_STAGE_REUNIAO_MARCADA_ID = os.getenv("GHL_STAGE_REUNIAO_MARCADA_ID", "reuniao_marcada_stage_id")
GHL_STAGE_NUTRICAO_ID = os.getenv("GHL_STAGE_NUTRICAO_ID", "nutricao_stage_id")
GHL_CALENDAR_ID = os.getenv("GHL_CALENDAR_ID", "default_calendar_id")

