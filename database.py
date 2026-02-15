import sqlite3
from datetime import datetime
import os

class Database:
    def __init__(self):
        # Crée le dossier data s'il n'existe pas (important pour Railway)
        os.makedirs('/app/data', exist_ok=True)
        self.conn = sqlite3.connect('/app/data/clients.db', check_same_thread=False)
        self.c = self.conn.cursor()
        self.init_db()

    def init_db(self):
        # Table clients
        self.c.execute('''CREATE TABLE IF NOT EXISTS clients
                         (id INTEGER PRIMARY KEY AUTOINCREMENT,
                          nom TEXT NOT NULL,
                          telephone TEXT,
                          email TEXT,
                          description TEXT,
                          montant_du REAL DEFAULT 0,
                          date_limite TEXT,
                          statut TEXT DEFAULT 'actif',
                          date_creation TIMESTAMP)''')
        # Table paiements
        self.c.execute('''CREATE TABLE IF NOT EXISTS paiements
                         (id INTEGER PRIMARY KEY AUTOINCREMENT,
                          client_id INTEGER,
                          montant REAL,
                          methode TEXT,
                          date_paiement TIMESTAMP,
                          notes TEXT,
                          FOREIGN KEY (client_id) REFERENCES clients(id))''')
        # Table voyages
        self.c.execute('''CREATE TABLE IF NOT EXISTS voyages
                         (id INTEGER PRIMARY KEY AUTOINCREMENT,
                          nom TEXT NOT NULL,
                          date_voyage TEXT,
                          couleur TEXT,
                          ordre INTEGER DEFAULT 0,
                          date_creation TIMESTAMP)''')
        # Table liaison clients-voyages
        self.c.execute('''CREATE TABLE IF NOT EXISTS client_voyage
                         (client_id INTEGER,
                          voyage_id INTEGER,
                          date_attribution TIMESTAMP,
                          FOREIGN KEY (client_id) REFERENCES clients(id),
                          FOREIGN KEY (voyage_id) REFERENCES voyages(id),
                          PRIMARY KEY (client_id, voyage_id))''')
        self.conn.commit()

    # ----- Clients -----
    def ajouter_client(self, nom, telephone='', email='', description='', montant_du=0, date_limite=''):
        self.c.execute('''INSERT INTO clients
                         (nom, telephone, email, description, montant_du, date_limite, date_creation, statut)
                         VALUES (?, ?, ?, ?, ?, ?, ?, 'actif')''',
                      (nom, telephone, email, description, montant_du, date_limite, datetime.now()))
        self.conn.commit()
        return self.c.lastrowid

    def rechercher_client(self, recherche):
        self.c.execute('''SELECT * FROM clients
                         WHERE nom LIKE ? AND statut = 'actif'
                         ORDER BY 
                           CASE WHEN date_limite IS NOT NULL AND date_limite != '' 
                           THEN date_limite ELSE '9999-12-31' END ASC''',
                      (f'%{recherche}%',))
        return self.c.fetchall()

    def get_client(self, client_id):
        self.c.execute('SELECT * FROM clients WHERE id = ?', (client_id,))
        return self.c.fetchone()

    def get_tous_clients_actifs(self):
        self.c.execute('''SELECT * FROM clients
                         WHERE statut = 'actif'
                         ORDER BY 
                           CASE WHEN date_limite IS NOT NULL AND date_limite != '' 
                           THEN date_limite ELSE '9999-12-31' END ASC''')
        return self.c.fetchall()

    def get_clients_termines(self):
        self.c.execute('''SELECT * FROM clients
                         WHERE statut = 'termine'
                         ORDER BY date_creation DESC''')
        return self.c.fetchall()

    def archiver_client(self, client_id):
        self.c.execute('UPDATE clients SET statut = ? WHERE id = ?', ('termine', client_id))
        self.conn.commit()

    def reactiver_client(self, client_id):
        self.c.execute('UPDATE clients SET statut = ? WHERE id = ?', ('actif', client_id))
        self.conn.commit()

    def modifier_client(self, client_id, champ, valeur):
        champs = ['nom', 'telephone', 'email', 'description', 'montant_du', 'date_limite']
        if champ in champs:
            self.c.execute(f'UPDATE clients SET {champ} = ? WHERE id = ?', (valeur, client_id))
            self.conn.commit()

    # ----- Paiements -----
    def ajouter_paiement(self, client_id, montant, methode, notes=''):
        self.c.execute('''INSERT INTO paiements (client_id, montant, methode, date_paiement, notes)
                         VALUES (?, ?, ?, ?, ?)''',
                      (client_id, montant, methode, datetime.now(), notes))
        self.conn.commit()

    def get_paiements_client(self, client_id):
        self.c.execute('SELECT * FROM paiements WHERE client_id = ? ORDER BY date_paiement DESC', (client_id,))
        return self.c.fetchall()

    def total_paye_client(self, client_id):
        self.c.execute('SELECT COALESCE(SUM(montant), 0) FROM paiements WHERE client_id = ?', (client_id,))
        return self.c.fetchone()[0]

    # ----- Voyages -----
    def ajouter_voyage(self, nom, date_voyage='', couleur='🔵'):
        try:
            if date_voyage and len(date_voyage) == 7:
                mois, annee = date_voyage.split('/')
                ordre = int(annee)*12 + int(mois)
            else:
                ordre = 0
        except:
            ordre = 0
        self.c.execute('''INSERT INTO voyages (nom, date_voyage, couleur, ordre, date_creation)
                         VALUES (?, ?, ?, ?, ?)''',
                      (nom, date_voyage, couleur, ordre, datetime.now()))
        self.conn.commit()
        return self.c.lastrowid

    def get_tous_voyages(self):
        self.c.execute('SELECT * FROM voyages ORDER BY ordre DESC, date_creation DESC')
        return self.c.fetchall()

    def get_voyage(self, voyage_id):
        self.c.execute('SELECT * FROM voyages WHERE id = ?', (voyage_id,))
        return self.c.fetchone()

    def attribuer_voyage_client(self, client_id, voyage_id):
        self.c.execute('''INSERT OR IGNORE INTO client_voyage (client_id, voyage_id, date_attribution)
                         VALUES (?, ?, ?)''',
                      (client_id, voyage_id, datetime.now()))
        self.conn.commit()

    def get_voyages_client(self, client_id):
        self.c.execute('''SELECT v.* FROM voyages v
                         JOIN client_voyage cv ON v.id = cv.voyage_id
                         WHERE cv.client_id = ?
                         ORDER BY v.ordre DESC''', (client_id,))
        return self.c.fetchall()

    def get_clients_voyage(self, voyage_id):
        self.c.execute('''SELECT c.* FROM clients c
                         JOIN client_voyage cv ON c.id = cv.client_id
                         WHERE cv.voyage_id = ? AND c.statut = 'actif'
                         ORDER BY c.nom ASC''', (voyage_id,))
        return self.c.fetchall()

    def get_couleur_client(self, client_id):
        voyages = self.get_voyages_client(client_id)
        if voyages:
            return voyages[0][3]
        return ""

    # ----- Rappels -----
    def get_paiements_imminents(self, jours=7):
        from datetime import datetime, timedelta
        clients = self.get_tous_clients_actifs()
        result = []
        now = datetime.now()
        for c in clients:
            date_limite = c[6]  # index de date_limite
            if date_limite:
                try:
                    d = datetime.strptime(date_limite, '%d/%m/%Y')
                    if 0 <= (d - now).days <= jours:
                        result.append(c)
                except:
                    continue
        return result

    def fermer(self):
        self.conn.close()
