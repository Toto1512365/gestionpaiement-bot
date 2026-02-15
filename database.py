import sqlite3
import os
from datetime import datetime, timedelta

class Database:
    def __init__(self):
        db_path = '/app/data/clients.db'
        if not os.path.exists('/app/data'):
            db_path = 'clients.db'
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.c = self.conn.cursor()
        self._init_db()

    def _init_db(self):
        # Table clients
        self.c.execute('''
            CREATE TABLE IF NOT EXISTS clients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nom TEXT NOT NULL,
                telephone TEXT,
                email TEXT,
                description TEXT,
                montant_du REAL DEFAULT 0,
                date_limite TEXT,
                statut TEXT DEFAULT 'actif',
                snooze_until TEXT,  -- date jusqu'à laquelle on ne notifie pas (JJ/MM/AAAA)
                date_creation TIMESTAMP
            )
        ''')
        # Table paiements
        self.c.execute('''
            CREATE TABLE IF NOT EXISTS paiements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id INTEGER,
                montant REAL,
                methode TEXT,
                date_paiement TIMESTAMP,
                notes TEXT,
                FOREIGN KEY(client_id) REFERENCES clients(id) ON DELETE CASCADE
            )
        ''')
        # Table voyages
        self.c.execute('''
            CREATE TABLE IF NOT EXISTS voyages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nom TEXT NOT NULL,
                date_voyage TEXT,
                couleur TEXT,
                ordre INTEGER DEFAULT 0,
                date_creation TIMESTAMP
            )
        ''')
        # Table liaison clients-voyages
        self.c.execute('''
            CREATE TABLE IF NOT EXISTS client_voyage (
                client_id INTEGER,
                voyage_id INTEGER,
                date_attribution TIMESTAMP,
                FOREIGN KEY(client_id) REFERENCES clients(id) ON DELETE CASCADE,
                FOREIGN KEY(voyage_id) REFERENCES voyages(id) ON DELETE CASCADE,
                PRIMARY KEY (client_id, voyage_id)
            )
        ''')
        self.conn.commit()

    # ----- Clients -----
    def ajouter_client(self, nom, telephone='', email='', description='', montant_du=0, date_limite=''):
        self.c.execute('''
            INSERT INTO clients (nom, telephone, email, description, montant_du, date_limite, date_creation, statut)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'actif')
        ''', (nom, telephone, email, description, montant_du, date_limite, datetime.now()))
        self.conn.commit()
        return self.c.lastrowid

    def update_client(self, client_id, nom, telephone, email, description, montant_du, date_limite):
        self.c.execute('''
            UPDATE clients
            SET nom = ?, telephone = ?, email = ?, description = ?, montant_du = ?, date_limite = ?
            WHERE id = ?
        ''', (nom, telephone, email, description, montant_du, date_limite, client_id))
        self.conn.commit()

    def modifier_date_limite(self, client_id, nouvelle_date):
        self.c.execute('UPDATE clients SET date_limite = ? WHERE id = ?', (nouvelle_date, client_id))
        self.conn.commit()

    def set_snooze(self, client_id, jours):
        """Ajoute un snooze de 'jours' à partir de maintenant, mais le jour J sera toujours notifié."""
        snooze_until = (datetime.now() + timedelta(days=jours)).strftime('%d/%m/%Y')
        self.c.execute('UPDATE clients SET snooze_until = ? WHERE id = ?', (snooze_until, client_id))
        self.conn.commit()

    def get_client(self, client_id):
        self.c.execute('SELECT * FROM clients WHERE id = ?', (client_id,))
        return self.c.fetchone()

    def get_tous_clients_actifs(self):
        self.c.execute('''
            SELECT * FROM clients
            WHERE statut = 'actif'
            ORDER BY date_limite
        ''')
        return self.c.fetchall()

    def get_clients_termines(self):
        self.c.execute('''
            SELECT * FROM clients
            WHERE statut = 'termine'
            ORDER BY date_creation DESC
        ''')
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
        self.c.execute('''
            INSERT INTO paiements (client_id, montant, methode, date_paiement, notes)
            VALUES (?, ?, ?, ?, ?)
        ''', (client_id, montant, methode, datetime.now(), notes))
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
                ordre = int(annee) * 12 + int(mois)
            else:
                ordre = 0
        except:
            ordre = 0
        self.c.execute('''
            INSERT INTO voyages (nom, date_voyage, couleur, ordre, date_creation)
            VALUES (?, ?, ?, ?, ?)
        ''', (nom, date_voyage, couleur, ordre, datetime.now()))
        self.conn.commit()
        return self.c.lastrowid

    def get_tous_voyages(self):
        # Tri par ordre croissant = les plus proches en premier
        self.c.execute('SELECT * FROM voyages ORDER BY ordre ASC, date_creation ASC')
        return self.c.fetchall()

    def get_voyage(self, voyage_id):
        self.c.execute('SELECT * FROM voyages WHERE id = ?', (voyage_id,))
        return self.c.fetchone()

    def supprimer_voyage(self, voyage_id):
        self.c.execute('DELETE FROM voyages WHERE id = ?', (voyage_id,))
        self.conn.commit()

    def attribuer_voyage_client(self, client_id, voyage_id):
        self.c.execute('''
            INSERT OR IGNORE INTO client_voyage (client_id, voyage_id, date_attribution)
            VALUES (?, ?, ?)
        ''', (client_id, voyage_id, datetime.now()))
        self.conn.commit()

    def retirer_tous_voyages_client(self, client_id):
        self.c.execute('DELETE FROM client_voyage WHERE client_id = ?', (client_id,))
        self.conn.commit()

    def get_voyages_client(self, client_id):
        self.c.execute('''
            SELECT v.* FROM voyages v
            JOIN client_voyage cv ON v.id = cv.voyage_id
            WHERE cv.client_id = ?
            ORDER BY v.ordre ASC
        ''', (client_id,))
        return self.c.fetchall()

    def get_clients_voyage(self, voyage_id):
        self.c.execute('''
            SELECT c.* FROM clients c
            JOIN client_voyage cv ON c.id = cv.client_id
            WHERE cv.voyage_id = ? AND c.statut = 'actif'
            ORDER BY c.nom
        ''', (voyage_id,))
        return self.c.fetchall()

    # ----- Notifications -----
    def get_clients_a_notifier(self):
        """
        Retourne les clients pour lesquels une notification doit être envoyée aujourd'hui.
        Règles :
        - On notifie à partir de 4 jours avant la date limite (J-4, J-3, J-2, J-1, J0)
        - On notifie chaque jour de retard (J+1, J+2, ...)
        - Le snooze suspend les notifications pendant X jours, SAUF le jour J (date limite) qui est toujours notifié.
        """
        from datetime import datetime, timedelta
        aujourd_hui = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        clients_actifs = self.get_tous_clients_actifs()
        result = []
        for c in clients_actifs:
            client_id, nom, _, _, _, montant_du, date_limite, _, snooze_until, _ = c
            if not date_limite:
                continue
            try:
                d_limite = datetime.strptime(date_limite, '%d/%m/%Y').replace(hour=0, minute=0, second=0)
            except:
                continue

            # Calcul du nombre de jours avant/après la date limite
            delta = (d_limite - aujourd_hui).days  # négatif si dépassé

            # Vérifier snooze : on notifie seulement si on est en dehors de la période de snooze, sauf le jour J
            notifier = False
            if delta <= 0:
                # En retard ou jour J : on notifie toujours (snooze ignoré)
                notifier = True
            elif delta <= 4:
                # Dans les 4 jours avant : on notifie sauf si snooze actif
                if snooze_until:
                    try:
                        snooze_date = datetime.strptime(snooze_until, '%d/%m/%Y').replace(hour=0, minute=0, second=0)
                        if aujourd_hui <= snooze_date:
                            # Snooze encore actif, on ne notifie pas
                            notifier = False
                        else:
                            notifier = True
                    except:
                        notifier = True
                else:
                    notifier = True
            else:
                notifier = False

            if notifier:
                # On ajoute le client avec le nombre de jours pour le message
                result.append((c, delta))

        return result

    def get_clients_avec_retard(self):
        """Retourne les clients actifs avec date limite dépassée"""
        from datetime import datetime
        aujourd_hui = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        tous = self.get_tous_clients_actifs()
        result = []
        for c in tous:
            date_lim = c[6]
            if date_lim:
                try:
                    d = datetime.strptime(date_lim, '%d/%m/%Y').replace(hour=0, minute=0, second=0)
                    if d < aujourd_hui:
                        result.append(c)
                except:
                    continue
        return result

    def get_paiements_imminents(self, jours=30):
        """Retourne tous les clients actifs avec date limite dans les 'jours' à venir, triés par date croissante"""
        from datetime import datetime, timedelta
        now = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        limite = now + timedelta(days=jours)
        tous = self.get_tous_clients_actifs()
        result = []
        for c in tous:
            date_lim = c[6]
            if date_lim:
                try:
                    d = datetime.strptime(date_lim, '%d/%m/%Y').replace(hour=0, minute=0, second=0)
                    if d <= limite:
                        result.append(c)
                except:
                    continue
        result.sort(key=lambda x: x[6] if x[6] else '9999-12-31')
        return result

    def fermer(self):
        self.conn.close()
