import anthropic
import config
import logging

class SDRBrain:
    def __init__(self):
        # A chave de API é puxada automaticamente do arquivo de configuração
        self.client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
        self.model = "claude-3-5-sonnet-20241022"

    def generate_message(self, lead_data: dict, stage: int = 0, history: list = None) -> dict:
        system_prompt = """Você é um empresário e copywriter altamente persuasivo, falando de igual para igual, de dono para dono, com proprietários de imobiliárias. Você é um verdadeiro mago de vendas e agendamento comercial no WhatsApp.
Sua missão é engajar o dono em uma conversa informal e muito amigável para conhecer a operação dele, construir uma conexão real (rapport) e depois levá-lo a agendar uma reunião de diagnóstico de 10 minutos (onde mostraremos como nossa infraestrutura de IA para atendimento automático resolve o vazamento de leads).

ESTRATÉGIA DO MAGO DE FECHAMENTO (REUNIÃO HOJE APÓS AS 17H):
- Seu principal objetivo comercial é marcar uma chamada rápida de 10 min.
- Você DEVE sempre propor que essa reunião aconteça HOJE MESMO, no final do expediente, em horários após as 17:00 (por exemplo: 17h15, 17h30, 18h00, 18h30).
- Nunca pergunte "quando fica bom pra você?". Em vez disso, use a técnica das opções limitadas de forma super casual: 
  * "Consigo te mostrar isso rapidinho hoje no final do dia? Tenho uma brecha livre às 17h30 ou 18h. O que fica melhor pra ti?"
  * "Bora bater um papo de 10 min hoje depois do expediente? Tenho livre às 17h15 ou às 17h45. Qual prefere?"
- Se o lead disser que hoje não pode mas sugerir outro dia, aceite, mas sempre busque sugerir horários após as 17h daquele dia.

Para ser irresistível, você domina os gatilhos do livro "As Armas da Persuasão" (Robert Cialdini) e os aplica com naturalidade, empatia e sem parecer um vendedor:
1. CONEXÃO E CURIOSIDADE REAL (Afeição/Sintonia): No início da conversa, seja extremamente "solto", leve, descontraído e informal. Fale como um colega de negócios parceiro e curioso, usando termos casuais do nicho de forma sutil e natural (como "cara", "total", "massa", "tranquilo", "show"). Evite formalidades e quebre o gelo com perguntas sobre a região ou portfólio dele.
2. FOCO EM ENTENDER E FAZER PERGUNTAS: Não tente vender nada no começo. Seu primeiro objetivo é fazer ele falar sobre a operação, entender como lidam com leads e só depois explorar a velocidade de resposta e o sentimento de perda de leads.
3. O Princípio do Contraste: Contraste o prejuízo silencioso (perder dezenas de milhares de reais em comissão por leads abandonados) com o esforço irrisório de bater um papo rápido de 10 min hoje no fim do expediente.
4. Reciprocidade: Valide as dores dele e ofereça insights ou checklists rápidos de blindagem sem forçar a barra.
5. Compromisso e Coerência: Apele para o orgulho profissional dele como dono de uma imobiliária de ponta que preza por atendimento de alto nível.
6. Autoridade: Cite dados de mercado com naturalidade se o assunto surgir (ex: tempo de resposta rápida é o maior preditor de vendas no imobiliário).

Regras INEGOCIÁVEIS de Humanização e Estilo:
- PROIBIDO jargões corporativos ("otimizar", "sinergia", "solução inovadora/robusta", "espero que esteja bem", "revolucionar", "inteligência artificial"). Fale como um humano de verdade.
- CONCISÃO EXTREMA: Suas mensagens devem ter no máximo 1 ou 2 linhas (geralmente menos de 20 palavras). NUNCA mande textões ou parágrafos no WhatsApp.
- EMOJIS QUASE INEXISTENTES: Use emojis de forma extremamente rara (no máximo um a cada 4 ou 5 mensagens e apenas se fizer muito sentido no contexto, como um polegar 👍). Nunca polua a mensagem com emojis.
- NÃO peça desculpas por incomodar (nada de "desculpe insistir" ou "sei que está ocupado").
- SEM ponto final no término da mensagem (deixe a última frase aberta, estilo WhatsApp real).
- CTAs super curtos e naturais. Termine quase sempre com uma pergunta curta e provocativa para mantê-lo respondendo.

REQUISITO TÉCNICO DE SAÍDA:
Você DEVE obrigatoriamente responder APENAS com um objeto JSON válido, sem qualquer introdução ou conclusão. Não use blocos de código markdown (como ```json) ou qualquer outro caractere. Retorne apenas o JSON puro contendo exatamente estas chaves:
{
  "reply_message": "sua mensagem em texto para enviar no whatsapp (curta, humana, sem ponto final)",
  "detected_intent": "active" | "meeting_scheduled" | "nurture" | "stopped",
  "agreed_time": "HH:MM"
}

Significado dos intents:
- "active": a conversa está fluindo e você está engajando ou qualificando o lead.
- "meeting_scheduled": o lead expressou acordo claro em agendar a reunião hoje ou em outro dia num horário específico (ex: "pode ser às 17h30", "fechado às 18h", "vamos sim, me liga no fim do dia").
- "nurture": o lead não quer a reunião agora mas demonstrou interesse morno, pediu material, pediu contato no mês que vem, ou sugeriu manter contato de outra forma (ex: "me manda um material", "agora não posso, me procura depois").
- "stopped": o lead recusou explicitamente, pediu para não entrar em contato ou demonstrou irritação.

Regra da chave 'agreed_time':
- Se o 'detected_intent' for 'meeting_scheduled', tente extrair o horário que foi acordado no formato "HH:MM" (ex: "17:30", "18:00"). Se o horário acordado não ficou perfeitamente claro ou foi genérico (ex: "no fim do dia"), defina como "17:30" (seu horário padrão ideal pós 17h). Se o intent não for 'meeting_scheduled', defina esta chave como null."""

        nome_dono = lead_data.get('nome_dono', 'dono(a)')
        nome_imobiliaria = lead_data.get('nome_imobiliaria', 'imobiliária')
        site = lead_data.get('site', 'seu site')

        # Se houver histórico de conversa, engajamos em diálogo dinâmico
        if history and len(history) > 0:
            user_prompt = f"""Histórico da conversa no WhatsApp até agora:
{chr(10).join([f"- {msg['role']}: {msg['content']}" for msg in history])}

Lead: {nome_dono}
Imobiliária: {nome_imobiliaria}
Site: {site}

Tarefa: Responda ao lead de forma ultra-curta, descontraída, muito natural e solta (máximo 2 linhas, sem ponto final).
Objetivos principais:
1. Demonstre empatia real e comente de forma humana e informal a resposta dele.
2. Seja o Mago de Fechamento: Se o lead mostrou abertura ou concordou, sugira e feche o papo de 10 min para HOJE MESMO após as 17:00 (ex: 17h30 ou 18h).
3. Classifique corretamente na chave 'detected_intent' do JSON se o lead aceitou a reunião ('meeting_scheduled'), se pediu material/nutrição ('nurture'), se pediu para parar ('stopped') ou se a conversa ainda está em andamento ('active')."""
            
        else:
            # Cadências iniciais/follow-up super casuais e curtas (1 a 9)
            if stage == 1:
                user_prompt = f"""Crie a mensagem de primeiro contato (estágio 1).
Lead: {nome_dono}
Imobiliária: {nome_imobiliaria}
Site: {site}

Tarefa: Gere uma abordagem inicial ultra-curta (máximo 2 linhas), bem solta, casual e simpática para gerar conexão imediata.
Elogie de forma sincera o site ({site}) ou a marca e faça uma pergunta descontraída sobre a operação deles. Não mencione perda de leads nem IA ainda.
CTA exemplo: "Oi {nome_dono}, tudo bem? Cara, tava olhando o site da {nome_imobiliaria} ({site}) e curti muito a curadoria de vcs. Vcs focam mais em alto padrão ou atendem de tudo aí?" """
                
            elif stage == 2:
                user_prompt = f"""Crie a mensagem de follow-up (estágio 2).
Lead: {nome_dono}
Imobiliária: {nome_imobiliaria}
 
Tarefa: Se o lead não respondeu ao primeiro contato, mande um follow-up casual para puxar assunto sobre a operação deles de forma leve e descompromissada.
CTA exemplo: "Oi {nome_dono}, tranquilo? Pergunto porque achei o site de vcs muito massa. Como vcs dividem a operação de vcs hoje entre vendas e captação?" """

            elif stage == 3:
                user_prompt = f"""Crie a mensagem de follow-up (estágio 3).
Lead: {nome_dono}
Imobiliária: {nome_imobiliaria}
 
Tarefa: Se o lead continua sem responder, faça uma transição leve e curiosa sobre o atendimento ao cliente e a resposta rápida.
CTA exemplo: "Oi {nome_dono}, cara, vcs têm muita demanda pelo site ou a maior parte vem de indicações/portais?" """

            elif stage == 4:
                user_prompt = f"""Crie a mensagem de follow-up (estágio 4).
Lead: {nome_dono}
Imobiliária: {nome_imobiliaria}
 
Tarefa: Segue para o problema da perda de leads (furo de atendimento fora de hora) usando o contraste de comissões perdidas vs tempo, mas com tom amigável de dono para dono.
CTA exemplo: "Perguntei pq vejo muita imobiliária investindo pesado em tráfego e site, mas deixando escapar lead de noite e fim de semana por falta de resposta rápida. Vcs já têm automação pra isso ou dependem do corretor responder na hora?" """

            elif stage == 5:
                user_prompt = f"""Crie a mensagem de follow-up (estágio 5).
Lead: {nome_dono}
Imobiliária: {nome_imobiliaria}
 
Tarefa: Ofereça valor com reciprocidade. Um checklist rápido de blindagem de leads 24/7.
CTA exemplo: "Eduardo, montei um checklist de 1 página mostrando como blindar a recepção de leads 24/7. Posso te mandar por aqui sem compromisso?" """

            elif stage == 6:
                user_prompt = f"""Crie a mensagem de follow-up (estágio 6).
Lead: {nome_dono}
Imobiliária: {nome_imobiliaria}
 
Tarefa: Use autoridade científica rápida (HBR: responder após 5 minutos cai conversão em 80%). Tente puxar a reunião para HOJE no final do expediente.
CTA exemplo: "Responder lead após 5 min reduz conversão em 80% segundo a HBR. Nossa IA atende em 10 segundos. Vamos marcar um papo rápido de 10 min hoje no fim do expediente? Tenho livre às 17h30 ou 18h" """

            elif stage == 7:
                user_prompt = f"""Crie a mensagem de follow-up (estágio 7).
Lead: {nome_dono}
Imobiliária: {nome_imobiliaria}
 
Tarefa: Pergunta desarmadora.
CTA exemplo: "Ei {nome_dono}, vcs ainda tão buscando escalar vendas ou a equipe já bateu o limite de atendimento?" """

            elif stage == 8:
                user_prompt = f"""Crie a mensagem de follow-up (estágio 8).
Lead: {nome_dono}
Imobiliária: {nome_imobiliaria}
 
Tarefa: Contraste provocativo e elegante. Proponha marcar hoje mesmo após as 17h.
CTA exemplo: "{nome_dono}, prefere deixar o vazamento financeiro aberto no site ou tirar 10 min hoje no fim do dia pra resolver? Consigo hoje às 17h30 ou 18h" """

            elif stage == 9:
                user_prompt = f"""Crie a mensagem de despedida final (estágio 9).
Lead: {nome_dono}
Imobiliária: {nome_imobiliaria}
 
Tarefa: Break-up simpático. Deixe as portas abertas.
CTA exemplo: "Tô limpando minha lista pra não encher seu saco, {nome_dono}. Se um dia quiser automatizar e blindar seus leads, só me chamar. Sucesso na {nome_imobiliaria}!" """
            else:
                return {
                    "reply_message": "Erro: Estágio de follow-up inválido.",
                    "detected_intent": "stopped",
                    "agreed_time": None
                }

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=150,
                temperature=0.7,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_prompt}
                ]
            )
            raw_text = response.content[0].text.strip()
            
            # Limpeza de markdown caso o modelo retorne com ```json ... ```
            if raw_text.startswith("```json"):
                raw_text = raw_text.replace("```json", "", 1)
            elif raw_text.startswith("```"):
                raw_text = raw_text.replace("```", "", 1)
            if raw_text.endswith("```"):
                raw_text = raw_text[:-3].strip()
            raw_text = raw_text.strip()
            
            import json
            try:
                parsed_json = json.loads(raw_text)
                # Validação de campos obrigatórios
                if "reply_message" not in parsed_json:
                    parsed_json["reply_message"] = raw_text
                if "detected_intent" not in parsed_json:
                    parsed_json["detected_intent"] = "active"
                if "agreed_time" not in parsed_json:
                    parsed_json["agreed_time"] = None
                return parsed_json
            except Exception as json_err:
                logging.warning(f"Erro ao parsear JSON retornado da IA: {json_err}. Raw text: {raw_text}")
                return {
                    "reply_message": raw_text,
                    "detected_intent": "active",
                    "agreed_time": None
                }
            
        except anthropic.APIConnectionError as e:
            logging.error(f"O servidor da Anthropic não pôde ser alcançado: {e}")
            return {"reply_message": "Erro ao conectar à IA.", "detected_intent": "active", "agreed_time": None}
        except anthropic.RateLimitError as e:
            logging.error(f"Limite de taxa da API atingido: {e}")
            return {"reply_message": "Limite de IA atingido.", "detected_intent": "active", "agreed_time": None}
        except anthropic.APIStatusError as e:
            logging.error(f"Erro retornado pela API: {e.status_code}")
            return {"reply_message": "Erro na API de IA.", "detected_intent": "active", "agreed_time": None}
        except Exception as e:
            logging.error(f"Erro inesperado: {str(e)}")
            return {"reply_message": "Erro desconhecido na geração.", "detected_intent": "active", "agreed_time": None}

