from flask import Flask, request, abort
from dotenv import load_dotenv
import os

# Importar função de validação do webhook
from validation import validate_typeform_signature

# Carregar variáveis de ambiente
load_dotenv()

app = Flask(__name__)

# Obter SECRET_TOKEN do webhook
SECRET_TOKEN = os.getenv('SECRET_TOKEN')

@app.route('/webhook', methods=['POST'])
def typeform_webhook():
    # Obter assinatura do cabeçalho
    typeform_signature = request.headers.get('Typeform-Signature', '')
    request_body = request.get_data()
    
    # Validar assinatura
    if not validate_typeform_signature(request_body, typeform_signature, SECRET_TOKEN):
        abort(401, 'Assinatura inválida')
        
    # Processar payload do webhook
    data = request.json
    print('Webhook recebido com sucesso', data)
    
    return '', 200

if __name__ == '__main__':
    app.run(port=3000)