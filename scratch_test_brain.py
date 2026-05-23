import logging
import sys
from sdr_brain import SDRBrain

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def test_all_stages():
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    print("=" * 60)
    print("INICIANDO TESTE DO SDR PERSUASIVO (CIALDINI TRIGGERS)")
    print("=" * 60)

    brain = SDRBrain()

    lead_data = {
        "nome_dono": "Eduardo",
        "nome_imobiliaria": "Pilar Imóveis",
        "site": "https://www.pilarimoveis.com.br"
    }

    for stage in range(1, 10):
        print(f"\n--- ESTÁGIO {stage} ---")
        try:
            message = brain.generate_message(lead_data, stage)
            print(f"\n{message}\n")
        except Exception as e:
            print(f"Erro ao gerar estágio {stage}: {e}")
        print("-" * 60)

if __name__ == "__main__":
    test_all_stages()
