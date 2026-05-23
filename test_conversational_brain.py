import sys
from sdr_brain import SDRBrain

def test_chat():
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

    print("=" * 60)
    print("INICIANDO TESTE DO CÉREBRO CONVERSACIONAL B2B")
    print("=" * 60)

    brain = SDRBrain()

    lead_data = {
        "nome_dono": "Carlos",
        "nome_imobiliaria": "A Imóveis",
        "site": "aimoveis.com"
    }

    # 1. Abordagem Inicial (Estágio 1)
    msg1 = brain.generate_message(lead_data, 1)
    print(f"SDR (Stage 1):\n{msg1}\n")

    # 2. Resposta do Lead: "fale mais"
    history = [
        {"role": "assistant", "content": msg1},
        {"role": "user", "content": "fale mais"}
    ]
    print(f"User: fale mais")
    print("SDR está pensando...")
    reply1 = brain.generate_message(lead_data, history=history)
    print(f"SDR:\n{reply1}\n")

    # 3. Resposta do Lead: "sim, a gente demora bastante à noite pq os corretores estão dormindo"
    history.append({"role": "assistant", "content": reply1})
    history.append({"role": "user", "content": "sim, a gente demora bastante à noite pq os corretores estão dormindo"})
    print(f"User: sim, a gente demora bastante à noite pq os corretores estão dormindo")
    print("SDR está pensando...")
    reply2 = brain.generate_message(lead_data, history=history)
    print(f"SDR:\n{reply2}\n")

    # 4. Resposta do Lead: "legal, me manda o link do diagnóstico então"
    history.append({"role": "assistant", "content": reply2})
    history.append({"role": "user", "content": "legal, me manda o link do diagnóstico então"})
    print(f"User: legal, me manda o link do diagnóstico então")
    print("SDR está pensando...")
    reply3 = brain.generate_message(lead_data, history=history)
    print(f"SDR:\n{reply3}\n")

if __name__ == "__main__":
    test_chat()
