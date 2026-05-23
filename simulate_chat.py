import sys
from sdr_brain import SDRBrain

def run_simulation():
    # Configura UTF-8 para o console do Windows para exibir emojis perfeitamente
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

    print("=" * 60)
    print("🤖 SIMULADOR CONVERSACIONAL INTERATIVO - SDR B2B (CIALDINI) 🤖")
    print("=" * 60)
    print("Esse script simula o robô prospectando e conversando no WhatsApp.")
    print("Você assumirá o papel do Dono da Imobiliária (Lead) conversando com o SDR.\n")

    nome = input("👉 Seu Nome (ex: Carlos): ").strip() or "Carlos"
    imobiliaria = input("👉 Nome da sua Imobiliária (ex: A Imóveis): ").strip() or "A Imóveis"
    site = input("👉 URL do seu Site (ex: aimoveis.com): ").strip() or "aimoveis.com"

    lead_data = {
        "nome_dono": nome,
        "nome_imobiliaria": imobiliaria,
        "site": site
    }

    brain = SDRBrain()
    history = []

    print("\n🚀 [Estágio 1 - Primeiro Contato] Simulando webhook de novo lead no GHL...")
    print("Gerando abordagem comercial personalizada e casual com base no seu site...")
    
    try:
        msg = brain.generate_message(lead_data, 1)
        print(f"\n💬 [SDR] diz:\n{msg}\n")
        history.append({"role": "assistant", "content": msg})
    except Exception as e:
        print(f"Erro ao gerar estágio 1: {e}")
        return

    stage = 1
    while True:
        print("=" * 60)
        print("Opções de Simulação:")
        print("1. Responder à mensagem (Entra no CHAT INTERATIVO DE DUAS VIAS em tempo real com a IA)")
        print("2. Ignorar mensagem (Simula passar 24h em silêncio e dispara o próximo Follow-up)")
        print("3. Sair da simulação")
        print("=" * 60)
        
        opcao = input("👉 Escolha uma opção (1, 2 ou 3): ").strip()
        
        if opcao == "1":
            print("\n💬 [CHAT ATIVADO] Você entrou na conversa ao vivo no WhatsApp com o SDR.")
            print("Digite suas respostas e tente debater sobre sua operação. Digite 'sair' para voltar ao menu principal.")
            print(f"SDR: \"{history[-1]['content']}\"\n")
            
            while True:
                user_msg = input("✍️ Você (Lead): ").strip()
                if not user_msg:
                    continue
                if user_msg.lower() == "sair":
                    print("\n🚪 Saindo do chat ao vivo...")
                    break
                
                # Registra a mensagem do usuário no histórico
                history.append({"role": "user", "content": user_msg})
                
                print("⏳ SDR está digitando...")
                try:
                    # Gera resposta dinâmica de duas vias
                    sdr_reply = brain.generate_message(lead_data, history=history)
                    print(f"\n💬 [SDR] diz:\n{sdr_reply}\n")
                    history.append({"role": "assistant", "content": sdr_reply})
                except Exception as e:
                    print(f"Erro ao gerar resposta da IA: {e}")
                    break
            
        elif opcao == "2":
            if stage >= 9:
                print("\n🛑 Todos os 9 estágios de follow-up foram esgotados sem resposta!")
                print("Lead movido para a esteira de nutrição de longo prazo no GHL.")
                break
                
            stage += 1
            print(f"\n⏳ Passaram-se 24 horas sem resposta... Disparando Follow-up (Estágio {stage}/9)...")
            print("Gerando nova mensagem casual baseada em persuasão e gatilhos...")
            try:
                msg = brain.generate_message(lead_data, stage)
                print(f"\n💬 [SDR] diz:\n{msg}\n")
                # Reseta o histórico com o novo follow-up
                history = [{"role": "assistant", "content": msg}]
            except Exception as e:
                print(f"Erro ao gerar estágio {stage}: {e}")
                break
                
        elif opcao == "3" or opcao.lower() == "sair":
            print("\n👋 Encerrando simulador. Sucesso nas vendas!")
            break
        else:
            print("\n⚠️ Opção inválida. Digite 1, 2 ou 3.")

if __name__ == "__main__":
    run_simulation()
