import os
import psycopg2
from datetime import datetime

class Database:
    def __init__(self):
        self.conn = psycopg2.connect(os.environ.get('DATABASE_URL'))
        self.c = self.conn.cursor()
        self._init_db()

    def _init_db(self):
        # ... (le reste du code est inchangé)
      
      print("DATABASE_URL:", os.environ.get('DATABASE_URL')[:50])  # affiche les 50 premiers caractères
