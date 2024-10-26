from flask import Flask, request, abort
import os
import hmac
import hashlib
import base64
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

SECRET_TOKEN = os.getenv('SECRET_TOKEN')

def validate_typeform_signature(request_body, typeform_signature, secret):
    computed_signature = hmac.new(
        secret.encode('utf-8'),
        msg=request_body,
        digestmod=hashlib.sha256
    ).digest()
    encoded_signature = base64.b64encode(computed_signature).decode('utf-8')

    return hmac.compare_digest(f"sha256={encoded_signature}", typeform_signature)

@app.route('/webhook', methods=['POST'])
def typeform_webhook():
    typeform_signature = request.headers.get('Typeform-Signature', '')
    request_body = request.get_data()

    if not validate_typeform_signature(request_body, typeform_signature, SECRET_TOKEN):
        abort(401, 'Invalid signature')

    # Processar o payload aqui
    data = request.json
    print('Webhook recebido com sucesso:', data)

    return '', 200

if __name__ == '__main__':
    app.run(port=3000)
