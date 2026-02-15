import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from database import Database
from datetime import datetime, time
import os

# Configuration
TOKEN = os.environ.get('TOKEN')
ADMIN_ID = 1099086639  # Remplace par ton ID
BOT_USERNAME = "@gestionpaiementav_bot"

logging.basicConfig(level=logging.INFO)
db = Database()

METHODES_PAIEMENT = [
    "💶 Compte perso",
    "💶 Liquide euros",
    "₽ Liquide ou virement roubles",
    "₿ Crypto",
    "🇬🇪 Géorgie"
]

# ---------- Menu principal ----------
async def menu_principal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("➕ AJOUTER CLIENT", callback_data='ajouter_client')],
        [InlineKeyboardButton("💰 PAIEMENT REÇU", callback_data='paiement_recu')],
        [InlineKeyboardButton("✈️ VOYAGES", callback_data='voyages')],
        [InlineKeyboardButton("🔍 RECHERCHER CLIENT", callback_data='rechercher_client')],
        [InlineKeyboardButton("📋 LISTE CLIENTS ACTIFS", callback_data='liste_clients')],
        [InlineKeyboardButton("💰 PROCHAINS PAIEMENTS", callback_data='prochains_paiements')],
        [InlineKeyboardButton("📁 CLIENTS TERMINÉS", callback_data='clients_termines')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    texte = "🚀 MENU PRINCIPAL - GESTION PAIEMENTS\n\nSélectionnez une option :"
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(texte, reply_markup=reply_markup)
    else:
        await update.message.reply_text(texte, reply_markup=reply_markup)

# ---------- Ajout client ----------
async def ajouter_client(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    context.user_data.clear()
    context.user_data['etape'] = 'attente_nom'
    context.user_data['client'] = {
        'nom': '', 'telephone': '', 'email': '', 'description': '',
        'montant_du': 0, 'date_limite': '', 'methode': '', 'voyages': []
    }
    keyboard = [[InlineKeyboardButton("🔙 RETOUR MENU", callback_data='menu_principal')]]
    await update.callback_query.edit_message_text(
        "👤 *AJOUT CLIENT*\n\nEnvoyez le *nom* du client :",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def recevoir_nom(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('etape') != 'attente_nom':
        return
    nom = update.message.text
    context.user_data['client']['nom'] = nom
    context.user_data['etape'] = None
    await update.message.reply_text(f"✅ Nom enregistré : {nom}")
    await afficher_formulaire_client(update, context)

async def afficher_formulaire_client(update: Update, context: ContextTypes.DEFAULT_TYPE):
    client = context.user_data.get('client', {})
    voyages = db.get_tous_voyages()
    nom = client.get('nom', '?')
    keyboard = [
        [InlineKeyboardButton(f"👤 Nom: {nom}", callback_data='modif_nom')],
        [InlineKeyboardButton(f"📞 Téléphone: {client.get('telephone','?')}", callback_data='modif_telephone')],
        [InlineKeyboardButton(f"📧 Email: {client.get('email','?')}", callback_data='modif_email')],
        [InlineKeyboardButton(f"📝 Description: {client.get('description','?')[:15]}", callback_data='modif_description')],
        [InlineKeyboardButton(f"💰 Montant dû: {client.get('montant_du',0)}", callback_data='modif_montant')],
        [InlineKeyboardButton(f"📅 Date limite: {client.get('date_limite','?')}", callback_data='modif_date')],
        [InlineKeyboardButton(f"💳 Méthode: {client.get('methode','?')}", callback_data='modif_methode')],
    ]
    if voyages:
        txt = "✈️ Voyages: "
        if client.get('voyages'):
            noms = []
            for vid in client['voyages']:
                v = db.get_voyage(vid)
                if v:
                    noms.append(f"{v[3]}{v[1]}")
            txt += ', '.join(noms) if noms else '?'
        else:
            txt += '?'
        keyboard.append([InlineKeyboardButton(txt, callback_data='modif_voyages')])
    keyboard.append([InlineKeyboardButton("✅ VALIDER", callback_data='valider_client')])
    keyboard.append([InlineKeyboardButton("🔙 RETOUR MENU", callback_data='menu_principal')])
    await update.message.reply_text(
        f"📋 Fiche client - {nom}\nCliquez pour modifier :",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ---------- Modifications des champs ----------
async def modif_champ(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    champ = query.data.replace('modif_', '')
    context.user_data['champ_en_cours'] = champ
    if champ == 'methode':
        keyboard = [[InlineKeyboardButton(m, callback_data=f'set_methode_{m}')] for m in METHODES_PAIEMENT]
        keyboard.append([InlineKeyboardButton("🔙 RETOUR", callback_data='retour_formulaire')])
        await query.edit_message_text("Choisissez la méthode :", reply_markup=InlineKeyboardMarkup(keyboard))
    elif champ == 'voyages':
        voyages = db.get_tous_voyages()
        keyboard = []
        for v in voyages:
            vid, nom, datev, couleur, _, _ = v
            selected = vid in context.user_data['client'].get('voyages', [])
            prefix = "✅ " if selected else ""
            keyboard.append([InlineKeyboardButton(f"{prefix}{couleur} {nom} ({datev or '?'})", callback_data=f'toggle_voyage_{vid}')])
        keyboard.append([InlineKeyboardButton("✅ TERMINÉ", callback_data='retour_formulaire')])
        await query.edit_message_text("Sélectionnez les voyages :", reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        keyboard = [[InlineKeyboardButton("🔙 RETOUR", callback_data='retour_formulaire')]]
        await query.edit_message_text(f"Envoyez la nouvelle valeur pour {champ} :", reply_markup=InlineKeyboardMarkup(keyboard))
        context.user_data['etape'] = f'attente_{champ}'

async def toggle_voyage(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    vid = int(query.data.replace('toggle_voyage_', ''))
    if 'voyages' not in context.user_data['client']:
        context.user_data['client']['voyages'] = []
    if vid in context.user_data['client']['voyages']:
        context.user_data['client']['voyages'].remove(vid)
    else:
        context.user_data['client']['voyages'].append(vid)
    await modif_champ(update, context)  # retour à la liste des voyages

async def set_methode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    methode = query.data.replace('set_methode_', '')
    context.user_data['client']['methode'] = methode
    await retour_formulaire(update, context)

async def recevoir_modification(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get('etape', '').startswith('attente_'):
        return
    champ = context.user_data['etape'].replace('attente_', '')
    valeur = update.message.text
    if champ == 'montant':
        try:
            valeur = float(valeur)
        except:
            await update.message.reply_text("❌ Montant invalide")
            return
    context.user_data['client'][champ] = valeur
    context.user_data['etape'] = None
    await update.message.reply_text("✅ Mis à jour")
    await retour_formulaire(update, context)

async def retour_formulaire(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    # On simule un message pour réafficher le formulaire
    fake_update = type('obj', (), {'message': query.message})
    await afficher_formulaire_client(fake_update, context)

async def valider_client(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    client = context.user_data.get('client', {})
    if not client.get('nom'):
        await query.edit_message_text("❌ Le nom est obligatoire")
        return
    cid = db.ajouter_client(
        nom=client['nom'],
        telephone=client.get('telephone', ''),
        email=client.get('email', ''),
        description=client.get('description', ''),
        montant_du=client.get('montant_du', 0),
        date_limite=client.get('date_limite', '')
    )
    if client.get('methode'):
        db.ajouter_paiement(cid, 0, client['methode'], "Méthode prévue")
    for vid in client.get('voyages', []):
        db.attribuer_voyage_client(cid, vid)
    await query.edit_message_text(f"✅ Client ajouté avec ID {cid}")
    keyboard = [[InlineKeyboardButton("🔙 MENU", callback_data='menu_principal')]]
    await query.message.reply_text("Retour au menu ?", reply_markup=InlineKeyboardMarkup(keyboard))
    context.user_data.clear()

# ---------- Paiement reçu ----------
async def paiement_recu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    clients = db.get_tous_clients_actifs()
    if not clients:
        await update.callback_query.edit_message_text("❌ Aucun client actif")
        return
    keyboard = []
    for c in clients:
        cid, nom, _, _, _, montant, _, _, _ = c
        reste = montant - db.total_paye_client(cid)
        voyages = db.get_voyages_client(cid)
        couleur = voyages[0][3] if voyages else ''
        keyboard.append([InlineKeyboardButton(f"{couleur}{nom} (reste {reste})", callback_data=f'paiement_client_{cid}')])
    keyboard.append([InlineKeyboardButton("🔙 RETOUR", callback_data='menu_principal')])
    await update.callback_query.edit_message_text("Choisissez le client :", reply_markup=InlineKeyboardMarkup(keyboard))

async def paiement_client_selectionne(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    cid = int(query.data.replace('paiement_client_', ''))
    context.user_data['paiement_cid'] = cid
    client = db.get_client(cid)
    reste = client[5] - db.total_paye_client(cid)
    context.user_data['paiement_reste'] = reste
    keyboard = [[InlineKeyboardButton("🔙 RETOUR", callback_data='paiement_recu')]]
    await query.edit_message_text(
        f"Client {client[1]}, reste {reste}\nEnvoyez le montant reçu :",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    context.user_data['etape'] = 'attente_montant_paiement'

async def recevoir_montant_paiement(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('etape') != 'attente_montant_paiement':
        return
    try:
        montant = float(update.message.text)
    except:
        await update.message.reply_text("❌ Montant invalide")
        return
    cid = context.user_data['paiement_cid']
    reste = context.user_data['paiement_reste']
    if montant > reste:
        keyboard = [
            [InlineKeyboardButton("✅ Oui", callback_data=f'force_montant_{montant}')],
            [InlineKeyboardButton("❌ Non", callback_data='paiement_recu')]
        ]
        await update.message.reply_text(
            f"⚠️ Le montant dépasse le reste ({reste}). Enregistrer quand même ?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        context.user_data['montant_force'] = montant
        return
    context.user_data['paiement_montant'] = montant
    await afficher_methodes_paiement(update, context)

async def force_montant(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    montant = float(query.data.replace('force_montant_', ''))
    context.user_data['paiement_montant'] = montant
    await afficher_methodes_paiement(update, context)

async def afficher_methodes_paiement(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton(m, callback_data=f'paiement_methode_{m}')] for m in METHODES_PAIEMENT]
    keyboard.append([InlineKeyboardButton("🔙 RETOUR", callback_data='paiement_recu')])
    await update.message.reply_text("Choisissez la méthode :", reply_markup=InlineKeyboardMarkup(keyboard))
    context.user_data['etape'] = 'attente_methode_paiement'

async def choisir_methode_paiement(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    methode = query.data.replace('paiement_methode_', '')
    cid = context.user_data['paiement_cid']
    montant = context.user_data['paiement_montant']
    db.ajouter_paiement(cid, montant, methode)
    client = db.get_client(cid)
    total = db.total_paye_client(cid)
    reste = client[5] - total
    await query.edit_message_text(f"✅ Paiement enregistré. Nouveau reste : {reste}")
    keyboard = [[InlineKeyboardButton("🔙 MENU", callback_data='menu_principal')]]
    await query.message.reply_text("Retour au menu ?", reply_markup=InlineKeyboardMarkup(keyboard))
    context.user_data.clear()

# ---------- Voyages ----------
async def voyages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    voyages = db.get_tous_voyages()
    texte = "✈️ VOYAGES\n\n"
    keyboard = []
    for v in voyages:
        vid, nom, datev, couleur, _, _ = v
        clients = db.get_clients_voyage(vid)
        nb = len(clients)
        texte += f"{couleur}{nom} ({datev or '?'}) - {nb} client(s)\n"
        keyboard.append([InlineKeyboardButton(f"{couleur}{nom}", callback_data=f'voyage_detail_{vid}')])
    keyboard.append([InlineKeyboardButton("➕ CRÉER", callback_data='voyage_creer')])
    keyboard.append([InlineKeyboardButton("🔙 RETOUR", callback_data='menu_principal')])
    await update.callback_query.edit_message_text(texte, reply_markup=InlineKeyboardMarkup(keyboard))

async def voyage_creer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    context.user_data['nouveau_voyage'] = {}
    context.user_data['etape'] = 'voyage_attente_nom'
    keyboard = [[InlineKeyboardButton("🔙 RETOUR", callback_data='voyages')]]
    await update.callback_query.edit_message_text(
        "✈️ CRÉER VOYAGE - Étape 1/3\nEnvoyez le nom :",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def voyage_recevoir_nom(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('etape') != 'voyage_attente_nom':
        return
    nom = update.message.text
    context.user_data['nouveau_voyage']['nom'] = nom
    context.user_data['etape'] = 'voyage_attente_date'
    keyboard = [[InlineKeyboardButton("🔙 RETOUR", callback_data='voyages')]]
    await update.message.reply_text(
        f"Nom: {nom}\nÉtape 2/3 - Envoyez la date (MM/AAAA) ou 'skip' :",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def voyage_recevoir_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('etape') != 'voyage_attente_date':
        return
    texte = update.message.text
    if texte.lower() == 'skip':
        context.user_data['nouveau_voyage']['date'] = ''
    else:
        if len(texte) == 7 and texte[2] == '/':
            context.user_data['nouveau_voyage']['date'] = texte
        else:
            await update.message.reply_text("Format incorrect. Utilisez MM/AAAA ou 'skip'")
            return
    couleurs = ["🔴","🟠","🟡","🟢","🔵","🟣","🟤","⚫","⚪"]
    keyboard = [
        [InlineKeyboardButton(c, callback_data=f'voyage_couleur_{c}') for c in couleurs[:3]],
        [InlineKeyboardButton(c, callback_data=f'voyage_couleur_{c}') for c in couleurs[3:6]],
        [InlineKeyboardButton(c, callback_data=f'voyage_couleur_{c}') for c in couleurs[6:9]],
        [InlineKeyboardButton("🔙 RETOUR", callback_data='voyages')]
    ]
    await update.message.reply_text(
        f"Nom: {context.user_data['nouveau_voyage']['nom']}\nDate: {context.user_data['nouveau_voyage'].get('date','?')}\nÉtape 3/3 - Choisissez une couleur :",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    context.user_data['etape'] = 'voyage_attente_couleur'

async def voyage_choisir_couleur(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if context.user_data.get('etape') != 'voyage_attente_couleur':
        return
    couleur = query.data.replace('voyage_couleur_', '')
    data = context.user_data['nouveau_voyage']
    vid = db.ajouter_voyage(data['nom'], data.get('date',''), couleur)
    await query.edit_message_text(f"✅ Voyage créé ! ID {vid}")
    keyboard = [[InlineKeyboardButton("✈️ VOIR VOYAGES", callback_data='voyages')]]
    await query.message.reply_text("Retour aux voyages ?", reply_markup=InlineKeyboardMarkup(keyboard))
    context.user_data.clear()

async def voyage_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    vid = int(query.data.replace('voyage_detail_', ''))
    v = db.get_voyage(vid)
    if not v:
        await query.edit_message_text("Voyage introuvable")
        return
    clients = db.get_clients_voyage(vid)
    texte = f"{v[3]}{v[1]} ({v[2] or '?'})\nClients :\n"
    for c in clients:
        cid, nom, _, _, _, montant, _, _, _ = c
        reste = montant - db.total_paye_client(cid)
        texte += f"  • {nom} (reste {reste})\n"
    keyboard = [[InlineKeyboardButton("🔙 RETOUR", callback_data='voyages')]]
    await query.edit_message_text(texte, reply_markup=InlineKeyboardMarkup(keyboard))

# ---------- Recherche ----------
async def rechercher_client(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    keyboard = [[InlineKeyboardButton("🔙 RETOUR", callback_data='menu_principal')]]
    await update.callback_query.edit_message_text(
        "🔍 Envoyez le nom ou une partie :",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    context.user_data['etape'] = 'recherche'

async def recevoir_recherche(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('etape') != 'recherche':
        return
    recherche = update.message.text
    clients = db.rechercher_client(recherche)
    if not clients:
        await update.message.reply_text("❌ Aucun client trouvé")
        return
    for c in clients:
        cid, nom, tel, email, desc, montant, datelim, statut, _ = c
        total = db.total_paye_client(cid)
        reste = montant - total
        voyages = db.get_voyages_client(cid)
        couleur = voyages[0][3] if voyages else ''
        texte = f"{couleur}{nom}\n💰 Reste {reste}/{montant}"
        if datelim:
            texte += f"\n📅 {datelim}"
        keyboard = [[InlineKeyboardButton("💰 PAIEMENT", callback_data=f'payer_{cid}')]]
        await update.message.reply_text(texte, reply_markup=InlineKeyboardMarkup(keyboard))
    context.user_data['etape'] = None

# ---------- Liste clients actifs ----------
async def liste_clients(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    clients = db.get_tous_clients_actifs()
    if not clients:
        await update.callback_query.edit_message_text("📭 Aucun client actif")
        return
    keyboard = []
    for c in clients:
        cid, nom, _, _, _, montant, datelim, _, _ = c
        reste = montant - db.total_paye_client(cid)
        voyages = db.get_voyages_client(cid)
        couleur = voyages[0][3] if voyages else ''
        keyboard.append([InlineKeyboardButton(f"{couleur}{nom} (reste {reste})", callback_data=f'client_detail_{cid}')])
    keyboard.append([InlineKeyboardButton("🔙 RETOUR", callback_data='menu_principal')])
    await update.callback_query.edit_message_text("Liste des clients :", reply_markup=InlineKeyboardMarkup(keyboard))

async def client_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    cid = int(query.data.replace('client_detail_', ''))
    c = db.get_client(cid)
    if not c:
        await query.edit_message_text("Client introuvable")
        return
    cid, nom, tel, email, desc, montant, datelim, statut, _ = c
    total = db.total_paye_client(cid)
    reste = montant - total
    voyages = db.get_voyages_client(cid)
    couleur = voyages[0][3] if voyages else ''
    paiements = db.get_paiements_client(cid)
    texte = f"{couleur}{nom}\n📞 {tel}\n📧 {email}\n📝 {desc}\n💰 Dû {montant} Payé {total} Reste {reste}\n📅 {datelim}\n"
    if paiements:
        texte += "Paiements :\n"
        for p in paiements[:3]:
            _, _, pm, pmeth, pdate, _ = p
            texte += f"  • {pdate[:10]} {pm} {pmeth}\n"
    keyboard = [
        [InlineKeyboardButton("💰 PAIEMENT", callback_data=f'payer_{cid}')],
        [InlineKeyboardButton("✈️ VOYAGES", callback_data=f'modif_voyages_{cid}')],
        [InlineKeyboardButton("✏️ MODIFIER", callback_data=f'modifier_client_{cid}')],
    ]
    if statut == 'actif':
        keyboard.append([InlineKeyboardButton("✅ ARCHIVER", callback_data=f'archiver_{cid}')])
    else:
        keyboard.append([InlineKeyboardButton("🔄 RÉACTIVER", callback_data=f'reactiver_{cid}')])
    keyboard.append([InlineKeyboardButton("🔙 RETOUR", callback_data='liste_clients')])
    await query.edit_message_text(texte, reply_markup=InlineKeyboardMarkup(keyboard))

async def modifier_client(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    cid = int(query.data.replace('modifier_client_', ''))
    c = db.get_client(cid)
    if not c:
        await query.edit_message_text("Client introuvable")
        return
    # Charger les données dans user_data pour modification
    context.user_data['client'] = {
        'id': c[0],
        'nom': c[1],
        'telephone': c[2] or '',
        'email': c[3] or '',
        'description': c[4] or '',
        'montant_du': c[5],
        'date_limite': c[6] or '',
        'methode': '',  # On ne peut pas récupérer la méthode prévue facilement, on laisse vide
        'voyages': [v[0] for v in db.get_voyages_client(cid)]
    }
    await afficher_formulaire_client(update, context)

# ---------- Paiement direct depuis détail ----------
async def payer_depuis_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    cid = int(query.data.split('_')[1])
    context.user_data['paiement_cid'] = cid
    client = db.get_client(cid)
    reste = client[5] - db.total_paye_client(cid)
    keyboard = [[InlineKeyboardButton(m, callback_data=f'methode_direct_{m}')] for m in METHODES_PAIEMENT]
    keyboard.append([InlineKeyboardButton("🔙 RETOUR", callback_data=f'client_detail_{cid}')])
    await query.edit_message_text(
        f"Client {client[1]}, reste {reste}\nChoisissez la méthode :",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    context.user_data['etape'] = 'attente_methode_direct'

async def methode_direct(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    methode = query.data.replace('methode_direct_', '')
    context.user_data['paiement_methode'] = methode
    keyboard = [[InlineKeyboardButton("🔙 RETOUR", callback_data=f'client_detail_{context.user_data["paiement_cid"]}')]]
    await query.edit_message_text("Envoyez le montant :", reply_markup=InlineKeyboardMarkup(keyboard))
    context.user_data['etape'] = 'attente_montant_direct'

async def recevoir_montant_direct(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('etape') != 'attente_montant_direct':
        return
    try:
        montant = float(update.message.text)
    except:
        await update.message.reply_text("❌ Montant invalide")
        return
    cid = context.user_data['paiement_cid']
    methode = context.user_data['paiement_methode']
    db.ajouter_paiement(cid, montant, methode)
    client = db.get_client(cid)
    total = db.total_paye_client(cid)
    reste = client[5] - total
    await update.message.reply_text(f"✅ Paiement enregistré. Nouveau reste : {reste}")
    keyboard = [[InlineKeyboardButton("🔙 RETOUR CLIENT", callback_data=f'client_detail_{cid}')]]
    await update.message.reply_text("Retour à la fiche client ?", reply_markup=InlineKeyboardMarkup(keyboard))
    context.user_data.clear()

# ---------- Prochains paiements ----------
async def prochains_paiements(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    clients = db.get_paiements_imminents(30)
    if not clients:
        await update.callback_query.edit_message_text("✅ Aucun paiement imminent")
        return
    texte = "💰 PROCHAINS PAIEMENTS\n"
    for c in clients:
        cid, nom, _, _, _, montant, datelim, _, _ = c
        total = db.total_paye_client(cid)
        reste = montant - total
        voyages = db.get_voyages_client(cid)
        couleur = voyages[0][3] if voyages else ''
        try:
            jours = (datetime.strptime(datelim, '%d/%m/%Y') - datetime.now()).days
            if jours < 0:
                urgence = "🔴 RETARD"
            elif jours == 0:
                urgence = "⚠️ AUJOURD'HUI"
            else:
                urgence = f"📅 {jours}j"
        except:
            urgence = "?"
        texte += f"\n{couleur}{nom} - {urgence}\n   Reste {reste}/{montant} - {datelim}"
    keyboard = [[InlineKeyboardButton("🔙 RETOUR", callback_data='menu_principal')]]
    await update.callback_query.edit_message_text(texte, reply_markup=InlineKeyboardMarkup(keyboard))

# ---------- Clients terminés ----------
async def clients_termines(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    clients = db.get_clients_termines()
    if not clients:
        await update.callback_query.edit_message_text("📭 Aucun client terminé")
        return
    texte = "📁 CLIENTS TERMINÉS\n"
    for c in clients[:15]:
        cid, nom, _, _, _, montant, _, _, _ = c
        total = db.total_paye_client(cid)
        voyages = db.get_voyages_client(cid)
        couleur = voyages[0][3] if voyages else ''
        texte += f"\n{couleur}{nom} - payé {total}/{montant}"
    keyboard = [[InlineKeyboardButton("🔙 RETOUR", callback_data='menu_principal')]]
    await update.callback_query.edit_message_text(texte, reply_markup=InlineKeyboardMarkup(keyboard))

# ---------- Archiver / Réactiver ----------
async def archiver_client_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    cid = int(query.data.split('_')[1])
    db.archiver_client(cid)
    await query.edit_message_text("✅ Client archivé")
    keyboard = [[InlineKeyboardButton("🔙 RETOUR", callback_data='liste_clients')]]
    await query.message.reply_text("Retour à la liste ?", reply_markup=InlineKeyboardMarkup(keyboard))

async def reactiver_client_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    cid = int(query.data.split('_')[1])
    db.reactiver_client(cid)
    await query.edit_message_text("✅ Client réactivé")
    keyboard = [[InlineKeyboardButton("🔙 RETOUR", callback_data='liste_clients')]]
    await query.message.reply_text("Retour à la liste ?", reply_markup=InlineKeyboardMarkup(keyboard))

# ---------- Notifications automatiques ----------
async def check_paiements_imminents(context: ContextTypes.DEFAULT_TYPE):
    maintenant = datetime.now()
    clients = db.get_paiements_imminents(7)
    for c in clients:
        cid, nom, _, _, _, montant, datelim, _, _ = c
        total = db.total_paye_client(cid)
        reste = montant - total
        voyages = db.get_voyages_client(cid)
        couleur = voyages[0][3] if voyages else ''
        try:
            jours = (datetime.strptime(datelim, '%d/%m/%Y') - maintenant).days
            if 0 <= jours <= 7:
                message = (f"⏰ RAPPEL {jours}j\n{couleur}{nom}\nReste {reste}/{montant}\n📅 {datelim}")
                await context.bot.send_message(chat_id=ADMIN_ID, text=message)
        except:
            continue

# ---------- Main ----------
def main():
    print("🚀 Démarrage du bot...")
    app = Application.builder().token(TOKEN).build()

    # Commandes
    app.add_handler(CommandHandler("start", menu_principal))

    # Callbacks généraux
    app.add_handler(CallbackQueryHandler(menu_principal, pattern='^menu_principal$'))
    app.add_handler(CallbackQueryHandler(ajouter_client, pattern='^ajouter_client$'))
    app.add_handler(CallbackQueryHandler(paiement_recu, pattern='^paiement_recu$'))
    app.add_handler(CallbackQueryHandler(voyages, pattern='^voyages$'))
    app.add_handler(CallbackQueryHandler(rechercher_client, pattern='^rechercher_client$'))
    app.add_handler(CallbackQueryHandler(liste_clients, pattern='^liste_clients$'))
    app.add_handler(CallbackQueryHandler(prochains_paiements, pattern='^prochains_paiements$'))
    app.add_handler(CallbackQueryHandler(clients_termines, pattern='^clients_termines$'))

    # Modifications client
    app.add_handler(CallbackQueryHandler(modif_champ, pattern='^modif_'))
    app.add_handler(CallbackQueryHandler(toggle_voyage, pattern='^toggle_voyage_'))
    app.add_handler(CallbackQueryHandler(set_methode, pattern='^set_methode_'))
    app.add_handler(CallbackQueryHandler(retour_formulaire, pattern='^retour_formulaire$'))
    app.add_handler(CallbackQueryHandler(valider_client, pattern='^valider_client$'))

    # Détails client
    app.add_handler(CallbackQueryHandler(client_detail, pattern='^client_detail_'))
    app.add_handler(CallbackQueryHandler(payer_depuis_detail, pattern='^payer_'))
    app.add_handler(CallbackQueryHandler(methode_direct, pattern='^methode_direct_'))
    app.add_handler(CallbackQueryHandler(modifier_client, pattern='^modifier_client_'))
    app.add_handler(CallbackQueryHandler(archiver_client_callback, pattern='^archiver_'))
    app.add_handler(CallbackQueryHandler(reactiver_client_callback, pattern='^reactiver_'))

    # Paiement reçu
    app.add_handler(CallbackQueryHandler(paiement_client_selectionne, pattern='^paiement_client_'))
    app.add_handler(CallbackQueryHandler(force_montant, pattern='^force_montant_'))
    app.add_handler(CallbackQueryHandler(choisir_methode_paiement, pattern='^paiement_methode_'))

    # Voyages
    app.add_handler(CallbackQueryHandler(voyage_creer, pattern='^voyage_creer$'))
    app.add_handler(CallbackQueryHandler(voyage_choisir_couleur, pattern='^voyage_couleur_'))
    app.add_handler(CallbackQueryHandler(voyage_detail, pattern='^voyage_detail_'))

    # Messages texte (ordre important : les plus spécifiques d'abord)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, recevoir_nom))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, voyage_recevoir_nom))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, voyage_recevoir_date))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, recevoir_modification))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, recevoir_montant_paiement))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, recevoir_recherche))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, recevoir_montant_direct))

    # Notifications
    job_queue = app.job_queue
    if job_queue:
        job_queue.run_daily(check_paiements_imminents, time=time(hour=9, minute=30), chat_id=ADMIN_ID)

    print("✅ Bot démarré !")
    app.run_polling()

if __name__ == '__main__':
    main()
