from flask import Flask, request, abort
from dotenv import load_dotenv
import os
import logging

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
    associate_pergunta_entregavel,
    log_processamento
)

# Carregar variáveis de ambiente
load_dotenv()

# Configurar o logger
logging.basicConfig(level=logging.INFO)

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
    data = request.get_json()
    if not data:
        abort(400, 'Payload vazio ou inválido')

    # Exibir payload recebido para depuração (não exibir dados sensíveis)
    logging.info('Webhook recebido com sucesso.')

    # Obter o event_id (id_entregavel)
    event_id = data.get('event_id')  # ID do evento (id_entregavel)
    if not event_id:
        abort(400, 'event_id não encontrado no payload')

    # Obter o form_response
    form_response = data.get('form_response', {})
    if not form_response:
        abort(400, 'form_response não encontrado no payload')

    submitted_at = form_response.get('submitted_at')  # Data de envio
    form_id = form_response.get('form_id')  # ID do formulário (id_typeform)
    hidden_fields = form_response.get('hidden', {})

    # Extrair IDs como strings
    id_checklist_str = hidden_fields.get('checklist')
    id_avaliacao_str = hidden_fields.get('avaliacao')

    # Validar que os IDs não estão vazios
    if not id_checklist_str:
        abort(400, 'id_checklist não encontrado nos hidden fields')
    if not id_avaliacao_str:
        abort(400, 'id_avaliacao não encontrado nos hidden fields')

    # Converter para inteiros
    try:
        id_checklist = int(id_checklist_str)
    except ValueError:
        abort(400, 'id_checklist deve ser um número inteiro')

    try:
        id_avaliacao = int(id_avaliacao_str)
    except ValueError:
        abort(400, 'id_avaliacao deve ser um número inteiro')

    # Inicializar variáveis opcionais como None
    respondent_name = None
    comentario_obrigatorio = None
    comentario_opcional = None

    connection = None  # Inicializar conexão

    try:
        # Conectar ao banco de dados
        connection = get_db_connection()

        with connection:  # Gerenciar transação de forma explícita
            # Inserir na tabela 'checklists' se necessário
            insert_checklist(connection, id_checklist, None)

            # Inserir na tabela 'avaliacoes' se necessário
            insert_avaliacao(connection, id_avaliacao, id_checklist, None)

            # Inserir dados na tabela 'entregaveis'
            insert_entregavel(
                connection, event_id, id_avaliacao, submitted_at, form_id, respondent_name,
                comentario_obrigatorio, comentario_opcional, id_checklist
            )

            # Processar as perguntas do payload
            fields = form_response.get('definition', {}).get('fields', [])
            field_id_to_title = {}
            for idx, field in enumerate(fields, start=1):
                id_pergunta = field.get('id')
                if not id_pergunta:
                    continue  # Ignorar se não houver id da pergunta

                title = field.get('title', '').lower()
                field_id_to_title[id_pergunta] = title

                texto_pergunta = field.get('title')
                tipo_pergunta = field.get('type')
                ref = field.get('ref')
                ordem = idx  # Usar o índice do loop como ordem

                # TODO: Verificar a ordem do 'ref' após o recebimento do teste com o formulário criado automaticamente.
                # Avaliar se precisa criar um dict para ref

                # Garantir que a pergunta exista
                ensure_pergunta_exists(
                    connection, id_pergunta, id_avaliacao, {
                        'title': texto_pergunta,
                        'type': tipo_pergunta,
                        'ref': ref,
                        'ordem': ordem
                    }
                )

                # Associar a pergunta ao entregável
                associate_pergunta_entregavel(connection, id_pergunta, event_id)

            # Processar as respostas do payload
            answers = form_response.get('answers', [])
            for answer in answers:
                field = answer.get('field', {})
                id_pergunta = field.get('id')
                ref = field.get('ref')  # Capturar o 'ref' da resposta
                if not id_pergunta:
                    continue  # Ignorar se não houver id da pergunta

                title = field_id_to_title.get(id_pergunta, '').lower()

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
                    choice_label = answer['choice'].get('label')
                    texto_resposta = choice_label
                elif 'choices' in answer:
                    texto_resposta = ', '.join(answer['choices'].get('labels', []))
                else:
                    texto_resposta = str(answer.get('value', ''))

                # Inserir dados na tabela 'respostas' para todas as perguntas
                insert_resposta(
                    connection,
                    id_entregavel=event_id,
                    id_pergunta=id_pergunta,
                    id_avaliacao=id_avaliacao,
                    valor_resposta=valor_resposta,
                    texto_resposta=texto_resposta,
                    tipo_resposta=tipo_resposta,
                    ref=ref  # Passar o 'ref' para a função
                )

                # Se houver necessidade de processar campos especiais com base no 'ref', descomentar e ajustar o código abaixo:
                '''
                # Processar campos especiais usando 'ref'
                if ref == 'comentario_obrigatorio_ref':
                    comentario_obrigatorio = texto_resposta
                elif ref == 'comentario_opcional_ref':
                    comentario_opcional = texto_resposta
                elif ref == 'nome_respondente_ref':
                    respondent_name = texto_resposta
                '''

            # Atualizar o entregável com os valores opcionais se necessário
            
            # Registrar log de sucesso
            log_processamento(connection, event_id, 'PROCESSADO', 'Webhook processado com sucesso.')

        logging.info('Dados inseridos com sucesso no banco de dados')
        return '', 200

    except Exception as e:
        # Registrar log de erro somente se a conexão estiver aberta
        if connection and connection.open:
            try:
                log_processamento(connection, event_id or 'N/A', 'ERRO', str(e))
            except Exception as log_error:
                logging.error(f'Erro ao registrar log de processamento: {log_error}')
        else:
            logging.error('Conexão com o banco de dados não está disponível para registrar o log de erro.')

        logging.error('Erro ao processar o webhook: %s', e)
        return '', 500


if __name__ == '__main__':
    app.run(port=3000, debug=True)