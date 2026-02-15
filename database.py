import sqlite3
from datetime import datetime
import pandas as pd

class Database:
    def __init__(self):
        self.conn = sqlite3.connect('clients.db', check_same_thread=False)
        self.c = self.conn.cursor()
        self.init_db()
    
    def init_db(self):
        # Table clients
        self.c.execute('''CREATE TABLE IF NOT EXISTS clients
                         (id INTEGER PRIMARY KEY AUTOINCREMENT,
                          prenom TEXT,
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
                          FOREIGN KEY (client_id) REFERENCES clients (id))''')
        
        # Table historique
        self.c.execute('''CREATE TABLE IF NOT EXISTS historique
                         (id INTEGER PRIMARY KEY AUTOINCREMENT,
                          client_id INTEGER,
                          action TEXT,
                          details TEXT,
                          date_action TIMESTAMP,
                          FOREIGN KEY (client_id) REFERENCES clients (id))''')
        
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
                          FOREIGN KEY (client_id) REFERENCES clients (id),
                          FOREIGN KEY (voyage_id) REFERENCES voyages (id),
                          PRIMARY KEY (client_id, voyage_id))''')
        
        self.conn.commit()
    
    # ---------- CLIENTS ----------
    def ajouter_client(self, prenom, nom, telephone="", email="", description="", montant_du=0, date_limite=""):
        self.c.execute('''INSERT INTO clients 
                         (prenom, nom, telephone, email, description, montant_du, date_limite, date_creation, statut)
                         VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'actif')''',
                      (prenom, nom, telephone, email, description, montant_du, date_limite, datetime.now()))
        self.conn.commit()
        self.ajouter_historique(self.c.lastrowid, "création", f"Client créé avec montant dû: {montant_du}")
        return self.c.lastrowid
    
    def rechercher_client(self, recherche):
        self.c.execute('''SELECT * FROM clients 
                         WHERE (prenom || ' ' || nom) LIKE ? AND statut = 'actif'
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
        self.c.execute('UPDATE clients SET statut = "termine" WHERE id = ?', (client_id,))
        self.conn.commit()
        self.ajouter_historique(client_id, "archivage", "Client archivé (soldé)")
    
    def reactiver_client(self, client_id):
        self.c.execute('UPDATE clients SET statut = "actif" WHERE id = ?', (client_id,))
        self.conn.commit()
        self.ajouter_historique(client_id, "réactivation", "Client réactivé")
    
    def modifier_client(self, client_id, champ, valeur):
        champs_autorises = ['prenom', 'nom', 'telephone', 'email', 'description', 'montant_du', 'date_limite']
        if champ in champs_autorises:
            self.c.execute(f'UPDATE clients SET {champ} = ? WHERE id = ?', (valeur, client_id))
            self.conn.commit()
            self.ajouter_historique(client_id, "modification", f"{champ} modifié: {valeur}")
    
    # ---------- PAIEMENTS ----------
    def ajouter_paiement(self, client_id, montant, methode, notes=""):
        self.c.execute('''INSERT INTO paiements 
                         (client_id, montant, methode, date_paiement, notes)
                         VALUES (?, ?, ?, ?, ?)''',
                      (client_id, montant, methode, datetime.now(), notes))
        self.conn.commit()
        
        client = self.get_client(client_id)
        total_paye = self.total_paye_client(client_id)
        reste = client[6] - total_paye
        
        self.ajouter_historique(client_id, "paiement", 
                               f"Paiement de {montant} par {methode}. Reste: {reste}")
        
        if reste <= 0:
            self.ajouter_historique(client_id, "soldé", "Client complètement payé !")
    
    def get_paiements_client(self, client_id):
        self.c.execute('''SELECT * FROM paiements 
                         WHERE client_id = ? 
                         ORDER BY date_paiement DESC''', (client_id,))
        return self.c.fetchall()
    
    def total_paye_client(self, client_id):
        self.c.execute('SELECT SUM(montant) FROM paiements WHERE client_id = ?', (client_id,))
        total = self.c.fetchone()[0]
        return total if total else 0
    
    # ---------- STATISTIQUES ----------
    def get_statistiques(self):
        stats = {}
        
        self.c.execute('SELECT SUM(montant) FROM paiements')
        stats['total_global'] = self.c.fetchone()[0] or 0
        
        methodes = ["💶 Compte perso", "💶 Liquide euros", "₽ Liquide ou virement roubles", "₿ Crypto", "🇬🇪 Géorgie"]
        stats['par_methode'] = {}
        for methode in methodes:
            self.c.execute('SELECT SUM(montant) FROM paiements WHERE methode = ?', (methode,))
            stats['par_methode'][methode] = self.c.fetchone()[0] or 0
        
        self.c.execute('''SELECT SUM(montant) FROM paiements 
                         WHERE strftime('%Y-%m', date_paiement) = strftime('%Y-%m', 'now')''')
        stats['ce_mois'] = self.c.fetchone()[0] or 0
        
        self.c.execute('SELECT COUNT(*) FROM clients WHERE statut = "actif"')
        stats['clients_actifs'] = self.c.fetchone()[0]
        
        self.c.execute('SELECT COUNT(*) FROM clients WHERE statut = "termine"')
        stats['clients_termines'] = self.c.fetchone()[0]
        
        return stats
    
    # ---------- RAPPELS ----------
    def get_paiements_imminents(self, jours=30):
        from datetime import datetime, timedelta
        
        clients_imminents = []
        tous_clients = self.get_tous_clients_actifs()
        
        for client in tous_clients:
            client_id, prenom, nom, _, _, _, montant_du, date_limite, _, _ = client
            
            if not date_limite or date_limite == '':
                continue
            
            try:
                date_obj = datetime.strptime(date_limite, '%d/%m/%Y')
                jours_restants = (date_obj - datetime.now()).days
                
                if jours_restants <= jours:
                    clients_imminents.append(client)
            except:
                continue
        
        clients_imminents.sort(key=lambda x: x[7] if x[7] else '9999-12-31')
        return clients_imminents
    
    # ---------- HISTORIQUE ----------
    def ajouter_historique(self, client_id, action, details):
        self.c.execute('''INSERT INTO historique (client_id, action, details, date_action)
                         VALUES (?, ?, ?, ?)''',
                      (client_id, action, details, datetime.now()))
        self.conn.commit()
    
    def get_historique(self, client_id, limite=20):
        self.c.execute('''SELECT * FROM historique 
                         WHERE client_id = ? 
                         ORDER BY date_action DESC 
                         LIMIT ?''', (client_id, limite))
        return self.c.fetchall()
    
    # ---------- EXPORT ----------
    def export_donnees(self):
        self.c.execute('SELECT * FROM clients')
        clients = self.c.fetchall()
        df_clients = pd.DataFrame(clients, columns=['id', 'prenom', 'nom', 'telephone', 'email', 'description', 
                                                   'montant_du', 'date_limite', 'statut', 'date_creation'])
        
        self.c.execute('SELECT * FROM paiements')
        paiements = self.c.fetchall()
        df_paiements = pd.DataFrame(paiements, columns=['id', 'client_id', 'montant', 'methode', 
                                                       'date_paiement', 'notes'])
        
        self.c.execute('SELECT * FROM historique')
        historique = self.c.fetchall()
        df_historique = pd.DataFrame(historique, columns=['id', 'client_id', 'action', 'details', 'date_action'])
        
        self.c.execute('SELECT * FROM voyages')
        voyages = self.c.fetchall()
        df_voyages = pd.DataFrame(voyages, columns=['id', 'nom', 'date_voyage', 'couleur', 'ordre', 'date_creation'])
        
        return df_clients, df_paiements, df_historique, df_voyages
    
    # ---------- GESTION DES VOYAGES ----------
    def ajouter_voyage(self, nom, date_voyage="", couleur="🔵"):
        try:
            if date_voyage and len(date_voyage) == 7:
                mois, annee = date_voyage.split('/')
                ordre = int(annee) * 12 + int(mois)
            else:
                ordre = 0
        except:
            ordre = 0
            
        self.c.execute('''INSERT INTO voyages 
                         (nom, date_voyage, couleur, ordre, date_creation)
                         VALUES (?, ?, ?, ?, ?)''',
                      (nom, date_voyage, couleur, ordre, datetime.now()))
        self.conn.commit()
        return self.c.lastrowid
    
    def get_tous_voyages(self):
        self.c.execute('''SELECT * FROM voyages 
                         ORDER BY ordre DESC, date_creation DESC''')
        return self.c.fetchall()
    
    def get_voyage(self, voyage_id):
        self.c.execute('SELECT * FROM voyages WHERE id = ?', (voyage_id,))
        return self.c.fetchone()
    
    def modifier_voyage(self, voyage_id, champ, valeur):
        champs_autorises = ['nom', 'date_voyage', 'couleur']
        if champ in champs_autorises:
            if champ == 'date_voyage':
                try:
                    if valeur and len(valeur) == 7:
                        mois, annee = valeur.split('/')
                        ordre = int(annee) * 12 + int(mois)
                        self.c.execute('UPDATE voyages SET ordre = ? WHERE id = ?', (ordre, voyage_id))
                except:
                    pass
            self.c.execute(f'UPDATE voyages SET {champ} = ? WHERE id = ?', (valeur, voyage_id))
            self.conn.commit()
    
    def supprimer_voyage(self, voyage_id):
        self.c.execute('DELETE FROM client_voyage WHERE voyage_id = ?', (voyage_id,))
        self.c.execute('DELETE FROM voyages WHERE id = ?', (voyage_id,))
        self.conn.commit()
    
    # ---------- LIAISON CLIENTS-VOYAGES ----------
    def attribuer_voyage_client(self, client_id, voyage_id):
        self.c.execute('''SELECT * FROM client_voyage 
                         WHERE client_id = ? AND voyage_id = ?''', 
                      (client_id, voyage_id))
        if self.c.fetchone():
            return False
        
        self.c.execute('''INSERT INTO client_voyage (client_id, voyage_id, date_attribution)
                         VALUES (?, ?, ?)''',
                      (client_id, voyage_id, datetime.now()))
        self.conn.commit()
        return True
    
    def retirer_voyage_client(self, client_id, voyage_id):
        self.c.execute('''DELETE FROM client_voyage 
                         WHERE client_id = ? AND voyage_id = ?''',
                      (client_id, voyage_id))
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
    
    # ---------- SUPPRESSION CLIENT ----------
    def supprimer_client_complet(self, client_id):
        """Supprime un client et tous ses paiements et liaisons"""
        self.c.execute('DELETE FROM paiements WHERE client_id = ?', (client_id,))
        self.c.execute('DELETE FROM client_voyage WHERE client_id = ?', (client_id,))
        self.c.execute('DELETE FROM historique WHERE client_id = ?', (client_id,))
        self.c.execute('DELETE FROM clients WHERE id = ?', (client_id,))
        self.conn.commit()
    
    # ---------- FERMETURE ----------
    def fermer(self):
        self.conn.close()
