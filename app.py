from flask import Flask, request, abort
from dotenv import load_dotenv
import os

# Importar função de validação do webhook
from validation import validate_typeform_signature

# Importar funções do database.py
from database import (
    get_db_connection,
    insert_checklist,
    insert_avaliacao,
    insert_entregavel,
    ensure_pergunta_exists,
    insert_resposta,
    log_processamento
)

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
    if not data:
        abort(400, 'Payload vazio ou inválido')
    
    # Exibir payload recebido para depuração
        print('Webhook recebido com sucesso:', data)
    
    try:
        # Conectar ao banco de dados
        connection = get_db_connection()
        
        with connection: #Gerenciar transação de forma explícita
            with connection.cursor() as cursor:
                # Extrair dados principais do payload
                form_response = data.get('form_response', {})
                event_id= form_response.get('event_id') # ID do evento (id_entregavel)
                response_token = form_response.get('token') # ID da resposta
                submitted_at = form_response.get('submitted_at') # Data de envio
                form_id = form_response.get('form_id')  # ID do formulário (id_typeform)
                hidden_fields = form_response.get('hidden', {})
                id_checklist = hidden_fields.get('checklist') # ID da turma no hidden field
                id_avaliacao = hidden_fields.get('avaliacao') # ID da avaliação do hidden field
                comentario_obrigatorio = form_response.get('comentario_obrigatorio', None)
                comentario_opcional = form_response.get('comentario_opcional', None)
                respondent_name = None  # Nome do respondente opcional
                
                

                # Inserir na tabela 'checklists' se necessário
                if id_checklist:
                    nome_checklist = f"Checklist {id_checklist}"  # Ajuste conforme necessário
                    insert_checklist(connection, id_checklist, nome_checklist)

                # Inserir na tabela 'avaliacoes' se necessário
                if id_avaliacao:
                    tipo_avaliacao = "CSAT"  # Ajuste conforme necessário
                    insert_avaliacao(connection, id_avaliacao, id_checklist, tipo_avaliacao)

                # Inserir dados na tabela 'entregaveis'
                insert_entregavel(connection, event_id, id_avaliacao, submitted_at, form_id, respondent_name)

                # Processar as perguntas do payload
                fields = form_response.get('definition', {}).get('fields', [])
                for index, field in enumerate(fields):
                    id_pergunta = field.get('id')
                    texto_pergunta = field.get('title')
                    tipo_pergunta = field.get('type')
                    
                    # Garantir que a pergunta exista com os 4 argumentos necessários
                    ensure_pergunta_exists(connection, id_pergunta, texto_pergunta, tipo_pergunta)

                # Processar as respostas do payload
                answers = form_response.get('answers', [])
                for answer in answers:
                    field = answer.get('field', {})
                    id_pergunta = field.get('id')
                    
                    # Preparar os dados da resposta
                    valor_resposta = None
                    texto_resposta = None
                    tipo_resposta = answer.get('type')

                    if 'number' in answer:
                        valor_resposta = answer['number']
                    elif 'boolean' in answer:
                        valor_resposta = int(answer['boolean'])
                    elif 'text' in answer:
                        texto_resposta = answer['text']
                    elif 'choice' in answer:
                        texto_resposta = answer['choice'].get('label')
                    elif 'choices' in answer:
                        texto_resposta = ', '.join(answer['choices'].get('labels', []))

                    # Inserir dados na tabela 'respostas'
                    insert_resposta(connection, response_token, id_pergunta, id_avaliacao, valor_resposta, texto_resposta, tipo_resposta)

        print('Dados inseridos com sucesso no banco de dados')
        return '', 200
    
    except Exception as e:
        print('Erro ao processar o webhook:', e)
        return '', 500

if __name__ == '__main__':
    app.run(port=3000)
