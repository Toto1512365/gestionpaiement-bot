import os
import psycopg2
from datetime import datetime

class Database:
    def __init__(self):
        self.conn = psycopg2.connect(os.environ.get('DATABASE_URL'))
        self.c = self.conn.cursor()
        self.init_db()
    
    def init_db(self):
        self.c.execute('''CREATE TABLE IF NOT EXISTS clients
                         (id SERIAL PRIMARY KEY,
                          prenom TEXT,
                          nom TEXT NOT NULL,
                          telephone TEXT,
                          email TEXT,
                          description TEXT,
                          montant_du REAL DEFAULT 0,
                          date_limite TEXT,
                          statut TEXT DEFAULT 'actif',
                          date_creation TIMESTAMP)''')
        self.conn.commit()
    
    def ajouter_client(self, prenom, nom):
        self.c.execute('''INSERT INTO clients (prenom, nom, date_creation, statut)
                          VALUES (%s, %s, %s, 'actif') RETURNING id''',
                      (prenom, nom, datetime.now()))
        self.conn.commit()
        return self.c.fetchone()[0]
    
    def get_client(self, client_id):
        self.c.execute('SELECT * FROM clients WHERE id = %s', (client_id,))
        return self.c.fetchone()
    
    def fermer(self):
        self.conn.close()
