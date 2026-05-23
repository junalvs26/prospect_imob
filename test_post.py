import requests

payload = {
    "contact_id": "test_jr_001",
    "first_name": "Ricardo",
    "last_name": "Silva",
    "email": "teste@imobiliaria.com",
    "phone": "+5599999999999",
    "custom_fields": {
        "nome_imobiliaria": "Imobiliária Horizonte",
        "site": "https://www.horizonteimoveis.com.br"
    }
}

try:
    response = requests.post("http://127.0.0.1:8000/webhook/ghl-lead", json=payload)
    print("Status Code:", response.status_code)
    print("Response JSON:", response.json())
except Exception as e:
    print("Erro ao conectar no servidor:", e)
