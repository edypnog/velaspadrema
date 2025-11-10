import sqlite3
import datetime

# DB_NAME = "vela_virtual.db"
DB_NAME = "/data/vela_virtual.db"


def init_db():
    """Cria a tabela no banco de dados se ela não existir."""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS velas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                user_name TEXT NOT NULL,
                purpose TEXT NOT NULL,
                timestamp DATETIME NOT NULL,
                gif_url TEXT NOT NULL
            )
        """
        )
        conn.commit()
        conn.close()
        print("Banco de dados inicializado com sucesso.")
    except Exception as e:
        print(f"Erro ao inicializar o banco de dados: {e}")


def add_candle(user_id, user_name, purpose, gif_url):
    """Adiciona uma nova vela ao banco de dados."""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        timestamp = datetime.datetime.now()
        cursor.execute(
            "INSERT INTO velas (user_id, user_name, purpose, timestamp, gif_url) VALUES (?, ?, ?, ?, ?)",
            (user_id, user_name, purpose, timestamp, gif_url),
        )
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Erro ao adicionar vela: {e}")
        return False


def get_all_candles(limit=20):
    """Busca as últimas velas acesas, com um limite."""
    try:
        conn = sqlite3.connect(DB_NAME)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM velas ORDER BY timestamp DESC LIMIT ?", (limit,))
        velas = cursor.fetchall()
        conn.close()
        return velas
    except Exception as e:
        print(f"Erro ao buscar todas as velas: {e}")
        return None


def get_candle_by_id(candle_id):
    """Busca uma vela específica pelo seu ID."""
    try:
        conn = sqlite3.connect(DB_NAME)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM velas WHERE id = ?", (candle_id,))
        vela = cursor.fetchone()
        conn.close()
        return vela
    except Exception as e:
        print(f"Erro ao buscar vela por ID: {e}")
        return None


# --- NOVA FUNÇÃO ---
def update_candle_purpose(candle_id, user_id, new_purpose):
    """Atualiza o propósito de uma vela, se o user_id corresponder."""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE velas SET purpose = ? WHERE id = ? AND user_id = ?",
            (new_purpose, candle_id, user_id),
        )
        # Verifica se alguma linha foi realmente alterada (para confirmar permissão)
        updated_rows = cursor.rowcount
        conn.commit()
        conn.close()
        return updated_rows > 0
    except Exception as e:
        print(f"Erro ao editar vela: {e}")
        return False


# --- NOVA FUNÇÃO ---
def delete_candle(candle_id, user_id):
    """Exclui uma vela do banco de dados, se o user_id corresponder."""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM velas WHERE id = ? AND user_id = ?", (candle_id, user_id)
        )
        # Verifica se alguma linha foi realmente deletada
        deleted_rows = cursor.rowcount
        conn.commit()
        conn.close()
        return deleted_rows > 0
    except Exception as e:
        print(f"Erro ao excluir vela: {e}")
        return False


def get_candles_by_user(user_id):
    """Busca todas as velas de um usuário específico."""
    try:
        conn = sqlite3.connect(DB_NAME)
        conn.row_factory = sqlite3.Row  # Adicionado para consistência
        cursor = conn.cursor()

        # AQUI ESTÁ A CORREÇÃO: "velas" em vez de "candles"
        cursor.execute(
            "SELECT id, purpose, timestamp, gif_url FROM velas WHERE user_id = ? ORDER BY timestamp DESC",
            (user_id,),
        )
        velas = cursor.fetchall()
        conn.close()

        # Isso agora funciona corretamente por causa do row_factory
        return [dict(vela) for vela in velas]

    except Exception as e:
        print(f"Erro ao buscar velas por usuário: {e}")
        return None
