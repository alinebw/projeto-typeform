import os
import pymysql
from pymysql.cursors import DictCursor
from dotenv import load_dotenv

load_dotenv()

# Carregar as configurações do banco de dados do arquivo .env
DB_HOST = os.getenv('DB_HOST')
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_NAME = os.getenv('DB_NAME')
DB_PORT = int(os.getenv('DB_PORT', 3306))

def get_db_connection():
    return pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        port=DB_PORT,
        charset='utf8mb4',
        cursorclass=DictCursor,
        autocommit=False
    )

def insert_checklist(connection, id_checklist, nome_checklist):
    with connection.cursor() as cursor:
        cursor.execute("""
            INSERT INTO checklists (id_checklist, nome_checklist)
            VALUES (%s, %s)
            ON DUPLICATE KEY UPDATE nome_checklist = VALUES(nome_checklist)
        """, (id_checklist, nome_checklist))
    connection.commit()

def insert_avaliacao(connection, id_avaliacao, id_checklist, tipo_avaliacao):
    with connection.cursor() as cursor:
        cursor.execute("""
            INSERT INTO avaliacoes (id_avaliacao, id_checklist, tipo_avaliacao)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE tipo_avaliacao = VALUES(tipo_avaliacao)
        """, (id_avaliacao, id_checklist, tipo_avaliacao))
    connection.commit()

def insert_entregavel(connection, token, id_avaliacao, submitted_at, form_id, respondent_name):
    with connection.cursor() as cursor:
        sql = """
            INSERT INTO entregaveis (id_entregavel, id_avaliacao, data_recebimento, id_typeform, nome_respondente)
            VALUES (%s, %s, %s, %s, %s)
        """
        cursor.execute(sql, (token, id_avaliacao, submitted_at, form_id, respondent_name))

def ensure_pergunta_exists(connection, id_pergunta, texto_pergunta, tipo_pergunta):
    """Verifica se a pergunta existe, caso contrário insere na tabela"""
    try:
        with connection.cursor() as cursor:
            # Verificar se a pergunta já existe
            cursor.execute("""
                SELECT 1 FROM perguntas WHERE id_pergunta = %s
            """, (id_pergunta,))
            result = cursor.fetchone()

            # Se a pergunta não existe, insira na tabela
            if not result:
                cursor.execute("""
                    INSERT INTO perguntas (id_pergunta, texto_pergunta, tipo_pergunta)
                    VALUES (%s, %s, %s)
                """, (id_pergunta, texto_pergunta, tipo_pergunta))
                connection.commit()
    except Exception as e:
        print(f"Erro ao garantir que a pergunta existe: {e}")

def insert_entregavel(connection, id_entregavel, id_avaliacao, data_recebimento, id_typeform, nome_respondente):
    """Insere um novo entregável na tabela"""
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                INSERT INTO entregaveis (id_entregavel, id_avaliacao, data_recebimento, id_typeform, nome_respondente)
                VALUES (%s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE data_recebimento = VALUES(data_recebimento),
                                        nome_respondente = VALUES(nome_respondente)
            """, (id_entregavel, id_avaliacao, data_recebimento, id_typeform, nome_respondente))
            connection.commit()
    except Exception as e:
        print(f"Erro ao inserir entregável: {e}")

def insert_resposta(connection, id_entregavel, id_pergunta, id_avaliacao, valor_resposta, texto_resposta, tipo_resposta):
    """Insere uma nova resposta na tabela"""
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                INSERT INTO respostas (id_entregavel, id_pergunta, id_avaliacao, valor_resposta, texto_resposta, tipo_resposta)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (id_entregavel, id_pergunta, id_avaliacao, valor_resposta, texto_resposta, tipo_resposta))
            connection.commit()
    except Exception as e:
        print(f"Erro ao inserir resposta: {e}")

def insert_checklist(connection, id_checklist, nome_checklist):
    """Insere um novo checklist na tabela"""
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                INSERT INTO checklists (id_checklist, nome_checklist)
                VALUES (%s, %s)
                ON DUPLICATE KEY UPDATE nome_checklist = VALUES(nome_checklist)
            """, (id_checklist, nome_checklist))
            connection.commit()
    except Exception as e:
        print(f"Erro ao inserir checklist: {e}")

def insert_avaliacao(connection, id_avaliacao, id_checklist, tipo_avaliacao):
    """Insere uma nova avaliação na tabela"""
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                INSERT INTO avaliacoes (id_avaliacao, id_checklist, tipo_avaliacao)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE tipo_avaliacao = VALUES(tipo_avaliacao)
            """, (id_avaliacao, id_checklist, tipo_avaliacao))
            connection.commit()
    except Exception as e:
        print(f"Erro ao inserir avaliação: {e}")