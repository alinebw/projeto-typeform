import os
import pymysql
from pymysql.cursors import DictCursor
from dotenv import load_dotenv
import logging

# Configuração de logger monitoramento
logging.basicConfig(
    level=logging.INFO,
    filename='processamento.log',
    format='%(asctime)s %(levelname)s %(message)s'
)

def log_event(message, level=logging.INFO):
    """
    Registra um evento nos logs do sistema
    """
    logging.log(level, message)


load_dotenv()

# Carregar as configurações do banco de dados do arquivo .env
DB_HOST = os.getenv('DB_HOST')
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_NAME = os.getenv('DB_NAME')
DB_PORT = int(os.getenv('DB_PORT', 3306))

def get_db_connection():
    """

    Estabelece conexão com banco de dados
    """
    try:
        connection = pymysql.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            port=DB_PORT,
            charset='utf8mb4',
            cursorclass=DictCursor,
            autocommit=False
    )
        log_event("Conexão com o banco de dados estabelecida com sucesso.")
        return connection
    except Exception as e:
        log_event(f"Erro ao conectar ao banco de dados: {e}", logging.ERROR)
        raise
    
def validate_data(field_name, value, expected_type, max_length=None):
    """
    Valida dados antes da inserção no banco
    """
    if not isinstance(value, expected_type):
        raise ValueError(f"{field_name} deve ser do tipo {expected_type.__name__}.")
    if max_length and isinstance(value, str) and len(value) > max_length:
        raise ValueError(f"{field_name} excede o tamanho máximo de {max_length} caracteres.")

def insert_checklist(connection, id_checklist, nome_checklist, id_projeto):
    """
    Insere um checklist no banco de dados.
    """
    try:
        with connection.cursor() as cursor:
            sql = """
                INSERT INTO checklists (id_checklist, nome_checklist, id_projeto)
                VALUES (%s, %s, %s)
            """
            # Validação de dados
            validate_data("id_checklist", id_checklist, int)
            validate_data("nome_checklist", nome_checklist, str, 100)
            validate_data("id_projeto", id_projeto, int)

            cursor.execute(sql, (id_checklist, nome_checklist, id_projeto))
            log_event(f"Checklist {id_checklist} inserido com sucesso.")
            
        # Confirma a transação
        connection.commit()
        
    except Exception as e:
        connection.rollback()  # Reverte a transação em caso de erro
        log_event(f"Erro ao inserir checklist {id_checklist}: {e}", logging.ERROR)
        raise

def insert_avaliacao(connection, id_avaliacao, id_checklist, tipo_avaliacao, status):
    """
    Insere uma avaliação no banco de dados.
    """
    try:
        with connection.cursor() as cursor:
            sql = """
                INSERT INTO avaliacoes (id_avaliacao, id_checklist, tipo_avaliacao, status)
                VALUES (%s, %s, %s, %s)
            """
            # Validação de dados
            validate_data("id_avaliacao", id_avaliacao, int)
            validate_data("id_checklist", id_checklist, int)
            validate_data("tipo_avaliacao", tipo_avaliacao, str, 50)
            validate_data("status", status, str, 20)

            cursor.execute(sql, (id_avaliacao, id_checklist, tipo_avaliacao, status))
            log_event(f"Avaliação {id_avaliacao} inserida com sucesso.")
            
        # Confirma a transação
        connection.commit()
        
    except Exception as e:
        connection.rollback()  # Reverte a transação em caso de erro
        log_event(f"Erro ao inserir avaliação {id_avaliacao}: {e}", logging.ERROR)
        raise

def insert_entregavel(connection, token, id_avaliacao, submitted_at, form_id, respondent_name, media_csat, status, data_processamento, comentario_obrigatorio, comentario_opcional):
    """
    Insere um entregável no banco de dados.
    """
    try:
        with connection.cursor() as cursor:
            sql = """
                INSERT INTO entregaveis (
                    id_entregavel, id_avaliacao, data_recebimento, id_typeform, nome_respondente, media_csat, status, data_processamento, comentario_obrigatorio, comentario_opcional
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            # Validação de dados
            validate_data("id_entregavel", token, str, 255)
            validate_data("id_avaliacao", id_avaliacao, int)
            validate_data("form_id", form_id, str, 50)

            cursor.execute(sql, (token, id_avaliacao, submitted_at, form_id, respondent_name, media_csat, status, data_processamento, comentario_obrigatorio, comentario_opcional))
            log_event(f"Entregável {token} inserido com sucesso.")
            
         # Confirma a transação
        connection.commit()
           
    except Exception as e:
        connection.rollback()  # Reverte a transação em caso de erro
        log_event(f"Erro ao inserir entregável {token}: {e}", logging.ERROR)
        raise

def ensure_pergunta_exists(connection, id_pergunta, id_avaliacao, id_entregavel, field):
    """
    Garante que uma pergunta exista no banco de dados.
    """
    try:
        with connection.cursor() as cursor:
            sql_check = "SELECT 1 FROM perguntas WHERE id_pergunta = %s AND id_avaliacao = %s"
            cursor.execute(sql_check, (id_pergunta, id_avaliacao))
            exists = cursor.fetchone()

            if not exists:
                sql_insert = """
                    INSERT INTO perguntas (id_pergunta, id_avaliacao, id_entregavel, texto_pergunta, tipo_pergunta, ordem, opcional)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """
                texto_pergunta = field.get('title')
                tipo_pergunta = field.get('type')
                ordem = field.get('ref')  # Ajustar conforme necessário
                opcional = field.get('allow_not_answer', False)

                # Validação de dados
                validate_data("id_pergunta", id_pergunta, str, 50)
                validate_data("id_entregavel", id_entregavel, str, 255)

                cursor.execute(sql_insert, (id_pergunta, id_avaliacao, id_entregavel, texto_pergunta, tipo_pergunta, ordem, opcional))
                log_event(f"Pergunta {id_pergunta} inserida com sucesso.")
                
            # Confirma a transação
        connection.commit()
        
    except Exception as e:
        connection.rollback()  # Reverte a transação em caso de erro
        log_event(f"Erro ao verificar/inserir pergunta {id_pergunta}: {e}", logging.ERROR)
        raise

def log_processamento(connection, id_entregavel, status, mensagem):
    """
    Registra um log de processamento no banco de dados.
    """
    try:
        with connection.cursor() as cursor:
            sql = """
                INSERT INTO logs_processamento (id_entregavel, data_processamento, status, mensagem)
                VALUES (%s, NOW(), %s, %s)
            """
            cursor.execute(sql, (id_entregavel, status, mensagem))
            log_event(f"Log registrado para entregável {id_entregavel}: {status} - {mensagem}")
            
         # Confirma a transação
        connection.commit()
        
    except Exception as e:
        connection.rollback()  # Reverte a transação em caso de erro
        log_event(f"Erro ao registrar log para entregável {id_entregavel}: {e}", logging.ERROR)
        raise