import sqlite3
import datetime

DB_NAME = "sdr_database.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS leads (
            ghl_contact_id TEXT PRIMARY KEY,
            nome_dono TEXT,
            nome_imobiliaria TEXT,
            site TEXT,
            followup_stage INTEGER DEFAULT 1,
            last_contact_date DATETIME,
            status TEXT DEFAULT 'active'
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS message_buffer (
            ghl_contact_id TEXT,
            message_content TEXT,
            received_at DATETIME
        )
    ''')
    conn.commit()
    conn.close()

def insert_or_update_lead(ghl_contact_id, nome_dono, nome_imobiliaria, site, status='active'):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    now = datetime.datetime.now().isoformat()
    cursor.execute('''
        INSERT INTO leads (ghl_contact_id, nome_dono, nome_imobiliaria, site, followup_stage, last_contact_date, status)
        VALUES (?, ?, ?, ?, 1, ?, ?)
        ON CONFLICT(ghl_contact_id) DO UPDATE SET
            nome_dono=excluded.nome_dono,
            nome_imobiliaria=excluded.nome_imobiliaria,
            site=excluded.site,
            status=excluded.status
    ''', (ghl_contact_id, nome_dono, nome_imobiliaria, site, now, status))
    conn.commit()
    conn.close()

def get_active_leads():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM leads WHERE status = 'active'")
    rows = cursor.fetchall()
    conn.close()
    
    leads = []
    for row in rows:
        leads.append({
            'ghl_contact_id': row[0],
            'nome_dono': row[1],
            'nome_imobiliaria': row[2],
            'site': row[3],
            'followup_stage': row[4],
            'last_contact_date': row[5],
            'status': row[6]
        })
    return leads

def update_followup_stage(ghl_contact_id, stage, status='active'):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    now = datetime.datetime.now().isoformat()
    cursor.execute('''
        UPDATE leads 
        SET followup_stage = ?, last_contact_date = ?, status = ?
        WHERE ghl_contact_id = ?
    ''', (stage, now, status, ghl_contact_id))
    conn.commit()
    conn.close()

def add_to_buffer(ghl_contact_id, message_content):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    now = datetime.datetime.now().isoformat()
    cursor.execute('''
        INSERT INTO message_buffer (ghl_contact_id, message_content, received_at)
        VALUES (?, ?, ?)
    ''', (ghl_contact_id, message_content, now))
    conn.commit()
    conn.close()

def get_and_clear_buffer(ghl_contact_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Busca todas as mensagens no buffer ordenadas pelo tempo
    cursor.execute('''
        SELECT message_content FROM message_buffer 
        WHERE ghl_contact_id = ? 
        ORDER BY received_at ASC
    ''', (ghl_contact_id,))
    rows = cursor.fetchall()
    
    # Junta as mensagens com espaço
    full_message = " ".join([row[0] for row in rows])
    
    # Deleta as mensagens do buffer
    cursor.execute('DELETE FROM message_buffer WHERE ghl_contact_id = ?', (ghl_contact_id,))
    conn.commit()
    conn.close()
    
    return full_message

def get_last_buffer_timestamp(ghl_contact_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT received_at FROM message_buffer 
        WHERE ghl_contact_id = ? 
        ORDER BY received_at DESC LIMIT 1
    ''', (ghl_contact_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return row[0]
    return None

# Initialize the database when the module is imported
init_db()
