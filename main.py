import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from database import Database
from datetime import datetime, time
import pandas as pd
from io import BytesIO
import os

# ---------- CONFIGURATION ----------
TOKEN = os.environ.get('TOKEN')
ADMIN_ID = 1099086639  # ton ID Telegram
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

# ---------- MENU PRINCIPAL ----------
async def menu_principal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("➕ AJOUTER CLIENT", callback_data='menu_ajouter')],
        [InlineKeyboardButton("💰 PAIEMENT REÇU", callback_data='menu_paiement_recu')],
        [InlineKeyboardButton("✈️ VOYAGES", callback_data='menu_voyages')],
        [InlineKeyboardButton("🔍 RECHERCHER CLIENT", callback_data='menu_rechercher')],
        [InlineKeyboardButton("📋 LISTE CLIENTS ACTIFS", callback_data='menu_liste')],
        [InlineKeyboardButton("💰 PROCHAINS PAIEMENTS", callback_data='menu_rappels')],
        [InlineKeyboardButton("📊 STATISTIQUES", callback_data='menu_stats')],
        [InlineKeyboardButton("📁 CLIENTS TERMINÉS", callback_data='menu_termines')],
        [InlineKeyboardButton("📤 EXPORTER DONNÉES", callback_data='menu_export')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    texte = ("🚀 MENU PRINCIPAL - GESTION PAIEMENTS\n\n"
             f"Bot: {BOT_USERNAME}\n"
             "Sélectionnez une option :")

    if update.callback_query:
        query = update.callback_query
        await query.answer()
        await query.edit_message_text(texte, reply_markup=reply_markup)
    else:
        await update.message.reply_text(texte, reply_markup=reply_markup)

# ---------- AJOUT CLIENT ----------
async def ajouter_client(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data.clear()
    context.user_data['nouveau_client'] = {
        'prenom': '',
        'nom': '',
        'telephone': '',
        'email': '',
        'description': '',
        'montant_du': 0,
        'date_limite': '',
        'methode_paiement': '',
        'voyages': []
    }
    keyboard = [[InlineKeyboardButton("🔙 RETOUR MENU", callback_data='retour_menu')]]
    await query.edit_message_text(
        "👤 *AJOUT D'UN NOUVEAU CLIENT*\n\n"
        "✏️ ÉTAPE 1/2 - Envoyez le *prénom* du client :",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )
    context.user_data['etape'] = 'attente_prenom'

async def recevoir_prenom(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('etape') != 'attente_prenom':
        return
    prenom = update.message.text
    context.user_data['nouveau_client']['prenom'] = prenom
    keyboard = [[InlineKeyboardButton("🔙 RETOUR MENU", callback_data='retour_menu')]]
    await update.message.reply_text(
        f"✅ Prénom enregistré : *{prenom}*\n\n"
        "👤 ÉTAPE 2/2 - Envoyez le *nom* du client :",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )
    context.user_data['etape'] = 'attente_nom'

async def recevoir_nom(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('etape') != 'attente_nom':
        return
    nom = update.message.text
    context.user_data['nouveau_client']['nom'] = nom
    await update.message.reply_text(
        f"✅ Nom enregistré : *{nom}*\n\n"
        "📋 Chargement du formulaire...",
        parse_mode='Markdown'
    )
    context.user_data['etape'] = None
    await afficher_formulaire_client(update, context)

async def afficher_formulaire_client(update: Update, context: ContextTypes.DEFAULT_TYPE):
    client = context.user_data.get('nouveau_client', {})
    voyages = db.get_tous_voyages()

    prenom = client.get('prenom', '')
    nom = client.get('nom', '')
    nom_complet = f"{prenom} {nom}".strip()

    keyboard = []

    # Prénom et Nom
    keyboard.append([
        InlineKeyboardButton(f"👤 Prénom: {prenom or '?'}", callback_data='modif_prenom'),
        InlineKeyboardButton(f"👤 Nom: {nom or '?'}", callback_data='modif_nom')
    ])
    # Téléphone et Email
    keyboard.append([
        InlineKeyboardButton(f"📞 Tél: {client.get('telephone') or '?'}", callback_data='modif_telephone'),
        InlineKeyboardButton(f"📧 Email: {client.get('email') or '?'}", callback_data='modif_email')
    ])
    # Description
    keyboard.append([InlineKeyboardButton(f"📝 Description: {client.get('description')[:15] or '?'}", callback_data='modif_description')])
    # Montant dû
    keyboard.append([InlineKeyboardButton(f"💰 Montant dû: {client.get('montant_du', 0)}", callback_data='modif_montant')])
    # Date limite
    keyboard.append([InlineKeyboardButton(f"📅 Date limite: {client.get('date_limite') or '?'}", callback_data='modif_date')])
    # Méthode de paiement
    keyboard.append([InlineKeyboardButton(f"💳 Méthode: {client.get('methode_paiement') or '?'}", callback_data='modif_methode')])

    # Voyages
    if voyages:
        voyage_text = "✈️ Voyages: "
        if client.get('voyages'):
            noms = []
            for vid in client['voyages']:
                v = db.get_voyage(vid)
                if v:
                    noms.append(f"{v[3]}{v[1]}")
            voyage_text += ", ".join(noms) if noms else "?"
        else:
            voyage_text += "?"
        keyboard.append([InlineKeyboardButton(voyage_text, callback_data='modif_voyages')])

    # Boutons de validation et retour
    keyboard.append([InlineKeyboardButton("✅ VALIDER LE CLIENT", callback_data='valider_client')])
    keyboard.append([InlineKeyboardButton("🔙 RETOUR MENU", callback_data='retour_menu')])

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        f"📋 *FICHE CLIENT - {nom_complet}*\n\n"
        "Cliquez sur les boutons pour modifier :",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

# ---------- MODIFICATION DES CHAMPS ----------
async def modif_champ(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    champ = query.data.replace('modif_', '')
    context.user_data['champ_en_cours'] = champ

    messages = {
        'prenom': "✏️ Envoyez le nouveau *prénom* :",
        'nom': "✏️ Envoyez le nouveau *nom* :",
        'telephone': "✏️ Envoyez le nouveau *téléphone* :",
        'email': "✏️ Envoyez le nouvel *email* :",
        'description': "✏️ Envoyez la nouvelle *description* :",
        'montant': "💰 Envoyez le nouveau *montant dû* (chiffre uniquement) :",
        'date': "📅 Envoyez la nouvelle *date limite* (JJ/MM/AAAA) :",
        'methode': "💳 Choisissez la nouvelle *méthode de paiement* :",
        'voyages': "✈️ Choisissez les *voyages* :",
    }

    if champ == 'methode':
        keyboard = [[InlineKeyboardButton(m, callback_data=f'set_methode_{m}')] for m in METHODES_PAIEMENT]
        keyboard.append([InlineKeyboardButton("🔙 RETOUR FORMULAIRE", callback_data='retour_formulaire')])
        await query.edit_message_text(
            messages[champ],
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    elif champ == 'voyages':
        voyages = db.get_tous_voyages()
        keyboard = []
        for v in voyages:
            vid, vnom, vdate, vcoul, _, _ = v
            selected = vid in context.user_data['nouveau_client'].get('voyages', [])
            prefix = "✅ " if selected else ""
            keyboard.append([InlineKeyboardButton(
                f"{prefix}{vcoul} {vnom} ({vdate or '?'})",
                callback_data=f'toggle_voyage_{vid}'
            )])
        keyboard.append([InlineKeyboardButton("✅ TERMINÉ", callback_data='retour_formulaire')])
        keyboard.append([InlineKeyboardButton("🔙 RETOUR FORMULAIRE", callback_data='retour_formulaire')])
        await query.edit_message_text(
            messages[champ],
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    else:
        keyboard = [[InlineKeyboardButton("🔙 RETOUR FORMULAIRE", callback_data='retour_formulaire')]]
        await query.edit_message_text(
            messages[champ],
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        context.user_data['etape'] = f'attente_{champ}'

async def toggle_voyage(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    vid = int(query.data.replace('toggle_voyage_', ''))
    if 'voyages' not in context.user_data['nouveau_client']:
        context.user_data['nouveau_client']['voyages'] = []
    if vid in context.user_data['nouveau_client']['voyages']:
        context.user_data['nouveau_client']['voyages'].remove(vid)
    else:
        context.user_data['nouveau_client']['voyages'].append(vid)
    await modif_champ(update, context)

async def set_methode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    methode = query.data.replace('set_methode_', '')
    context.user_data['nouveau_client']['methode_paiement'] = methode
    await retour_formulaire(update, context)

async def recevoir_modification(update: Update, context: ContextTypes.DEFAULT_TYPE):
    etape = context.user_data.get('etape', '')
    if not etape.startswith('attente_'):
        return
    champ = etape.replace('attente_', '')
    valeur = update.message.text
    if champ == 'montant':
        try:
            valeur = float(valeur)
        except ValueError:
            await update.message.reply_text("❌ Montant invalide. Veuillez entrer un nombre.")
            return
    context.user_data['nouveau_client'][champ] = valeur
    context.user_data['etape'] = None
    await update.message.reply_text("✅ Information mise à jour !")
    await retour_formulaire(update, context)

async def retour_formulaire(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    # On simule un update avec un message pour réafficher le formulaire
    fake_update = type('obj', (), {'message': query.message})
    await afficher_formulaire_client(fake_update, context)

async def valider_client(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    client = context.user_data.get('nouveau_client', {})
    if not client.get('prenom') and not client.get('nom'):
        await query.edit_message_text("❌ Le client doit avoir un prénom ou un nom !")
        return
    prenom = client.get('prenom', '')
    nom = client.get('nom', '')
    nom_complet = f"{prenom} {nom}".strip()

    client_id = db.ajouter_client(
        prenom=prenom,
        nom=nom,
        telephone=client.get('telephone', ''),
        email=client.get('email', ''),
        description=client.get('description', ''),
        montant_du=client.get('montant_du', 0),
        date_limite=client.get('date_limite', '')
    )

    if client.get('methode_paiement'):
        db.ajouter_paiement(client_id, 0, client['methode_paiement'], "Méthode de paiement prévue")

    if client.get('voyages'):
        for vid in client['voyages']:
            db.attribuer_voyage_client(client_id, vid)

    voyages = db.get_voyages_client(client_id)
    couleur = voyages[0][3] if voyages else ""

    await query.edit_message_text(
        f"✅ Client ajouté avec succès ! ID: `{client_id}`\n\n"
        f"{couleur}👤 {nom_complet}\n"
        f"💰 Montant dû: {client.get('montant_du', 0)}\n"
        f"💳 Méthode: {client.get('methode_paiement', 'Non définie')}",
        parse_mode='Markdown'
    )
    keyboard = [[InlineKeyboardButton("🔙 RETOUR MENU", callback_data='retour_menu')]]
    await query.message.reply_text(
        "Retour au menu principal ?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    context.user_data.clear()

# ---------- VOYAGES ----------
async def menu_voyages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    voyages = db.get_tous_voyages()
    texte = "✈️ *GESTION DES VOYAGES*\n\n"
    keyboard = []

    if voyages:
        texte += "Vos voyages (du plus récent au plus ancien) :\n\n"
        for v in voyages:
            vid, nom, datev, couleur, ordre, _ = v
            clients = db.get_clients_voyage(vid)
            nb = len(clients)
            texte += f"{couleur} *{nom}*"
            if datev:
                texte += f" - {datev}"
            texte += f" ({nb} client{'s' if nb>1 else ''})\n"
            keyboard.append([InlineKeyboardButton(f"{couleur} {nom} ({datev or '?'})", callback_data=f'voyage_detail_{vid}')])
        keyboard.append([InlineKeyboardButton("➕ CRÉER UN VOYAGE", callback_data='voyage_creer')])
    else:
        texte += "Aucun voyage créé pour le moment.\n\n"
        keyboard.append([InlineKeyboardButton("➕ CRÉER UN VOYAGE", callback_data='voyage_creer')])

    keyboard.append([InlineKeyboardButton("🔙 RETOUR MENU", callback_data='retour_menu')])
    await query.edit_message_text(texte, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def voyage_creer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['nouveau_voyage'] = {}
    keyboard = [[InlineKeyboardButton("🔙 RETOUR VOYAGES", callback_data='menu_voyages')]]
    await query.edit_message_text(
        "✈️ *CRÉER UN VOYAGE*\n\n"
        "📝 ÉTAPE 1/3 - Envoyez le *nom* du voyage :",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )
    context.user_data['etape'] = 'voyage_attente_nom'

async def voyage_recevoir_nom(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('etape') != 'voyage_attente_nom':
        return
    nom = update.message.text
    context.user_data['nouveau_voyage']['nom'] = nom
    keyboard = [[InlineKeyboardButton("🔙 RETOUR VOYAGES", callback_data='menu_voyages')]]
    await update.message.reply_text(
        f"✅ Nom enregistré : *{nom}*\n\n"
        "📅 ÉTAPE 2/3 - Envoyez la *date* du voyage (format MM/AAAA)\n"
        "Exemple: `06/2024` pour Juin 2024\n"
        "Ou envoyez 'skip' pour passer",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )
    context.user_data['etape'] = 'voyage_attente_date'

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
            await update.message.reply_text("❌ Format incorrect. Utilisez MM/AAAA (ex: 06/2024) ou 'skip'")
            return

    couleurs = ["🔴", "🟠", "🟡", "🟢", "🔵", "🟣", "🟤", "⚫", "⚪"]
    keyboard = [
        [InlineKeyboardButton(c, callback_data=f'voyage_couleur_{c}') for c in couleurs[:3]],
        [InlineKeyboardButton(c, callback_data=f'voyage_couleur_{c}') for c in couleurs[3:6]],
        [InlineKeyboardButton(c, callback_data=f'voyage_couleur_{c}') for c in couleurs[6:9]],
        [InlineKeyboardButton("🔙 RETOUR", callback_data='menu_voyages')]
    ]
    await update.message.reply_text(
        f"✈️ *CRÉER UN VOYAGE*\n\n"
        f"Nom: *{context.user_data['nouveau_voyage']['nom']}*\n"
        f"Date: *{context.user_data['nouveau_voyage'].get('date', 'Non définie')}*\n\n"
        "🎨 ÉTAPE 3/3 - Choisissez une couleur :",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )
    context.user_data['etape'] = 'voyage_attente_couleur'

async def voyage_choisir_couleur(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if context.user_data.get('etape') != 'voyage_attente_couleur':
        return
    couleur = query.data.replace('voyage_couleur_', '')
    voyage_data = context.user_data.get('nouveau_voyage', {})
    vid = db.ajouter_voyage(voyage_data['nom'], voyage_data.get('date', ''), couleur)
    await query.edit_message_text(
        f"✅ *VOYAGE CRÉÉ !*\n\n"
        f"{couleur} *{voyage_data['nom']}*\n"
        f"📅 Date: {voyage_data.get('date', 'Non définie')}\n"
        f"🆔 ID: `{vid}`",
        parse_mode='Markdown'
    )
    keyboard = [
        [InlineKeyboardButton("✈️ VOIR LES VOYAGES", callback_data='menu_voyages')],
        [InlineKeyboardButton("🔙 RETOUR MENU", callback_data='retour_menu')]
    ]
    await query.message.reply_text(
        "Que voulez-vous faire ?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    context.user_data.clear()

async def voyage_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    vid = int(query.data.replace('voyage_detail_', ''))
    voyage = db.get_voyage(vid)
    if not voyage:
        await query.edit_message_text("❌ Voyage introuvable")
        return
    vid, nom, datev, couleur, _, _ = voyage
    clients = db.get_clients_voyage(vid)

    texte = f"{couleur} *{nom}*\n"
    if datev:
        texte += f"📅 Date: {datev}\n"
    texte += f"👥 *Clients participants:* {len(clients)}\n\n"

    keyboard = []
    if clients:
        texte += "Liste des clients :\n"
        for c in clients[:10]:
            cid, prenom, cnom, _, _, _, montant, datelim, _, _ = c
            total = db.total_paye_client(cid)
            reste = montant - total
            texte += f"  • {prenom} {cnom} - Reste: {reste}/{montant}\n"
            keyboard.append([InlineKeyboardButton(f"👤 {prenom} {cnom}", callback_data=f'detail_{cid}')])
    else:
        texte += "Aucun client dans ce voyage pour le moment."

    keyboard.append([InlineKeyboardButton("🔙 RETOUR VOYAGES", callback_data='menu_voyages')])
    await query.edit_message_text(texte, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

# ---------- PAIEMENT REÇU ----------
async def paiement_recu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    clients = db.get_tous_clients_actifs()
    if not clients:
        await query.edit_message_text("❌ Aucun client actif.")
        return
    texte = "💰 *ENREGISTRER UN PAIEMENT REÇU*\n\nSélectionnez le client :\n\n"
    keyboard = []
    for c in clients:
        cid, prenom, nom, _, _, _, montant, _, _, _ = c
        total = db.total_paye_client(cid)
        reste = montant - total
        voyages = db.get_voyages_client(cid)
        couleur = voyages[0][3] if voyages else ""
        nom_complet = f"{prenom} {nom}".strip()
        keyboard.append([InlineKeyboardButton(
            f"{couleur} {nom_complet} (Reste: {reste})",
            callback_data=f'paiement_client_{cid}'
        )])
    keyboard.append([InlineKeyboardButton("🔙 RETOUR MENU", callback_data='retour_menu')])
    await query.edit_message_text(texte, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    context.user_data['etape'] = 'attente_client_paiement'

async def paiement_client_selectionne(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    cid = int(query.data.replace('paiement_client_', ''))
    context.user_data['paiement_client_id'] = cid
    client = db.get_client(cid)
    total = db.total_paye_client(cid)
    reste = client[6] - total
    context.user_data['paiement_reste'] = reste
    keyboard = [[InlineKeyboardButton("🔙 RETOUR MENU", callback_data='retour_menu')]]
    await query.edit_message_text(
        f"💰 *MONTANT DU PAIEMENT*\n\n"
        f"Client: *{client[1]} {client[2]}*\n"
        f"💰 Restant dû: *{reste}*\n\n"
        "✏️ Envoyez le montant reçu :",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )
    context.user_data['etape'] = 'attente_montant_paiement'

async def recevoir_montant_paiement(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('etape') != 'attente_montant_paiement':
        return
    try:
        montant = float(update.message.text)
    except ValueError:
        await update.message.reply_text("❌ Montant invalide.")
        return
    cid = context.user_data['paiement_client_id']
    reste = context.user_data['paiement_reste']
    if montant > reste:
        keyboard = [
            [InlineKeyboardButton("✅ Oui, enregistrer quand même", callback_data=f'force_montant_{montant}')],
            [InlineKeyboardButton("❌ Non, annuler", callback_data='retour_menu')]
        ]
        await update.message.reply_text(
            f"⚠️ Le montant ({montant}) dépasse le reste dû ({reste}).\n"
            "Voulez-vous quand même enregistrer ?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        context.user_data['montant_force'] = montant
        return
    context.user_data['paiement_montant'] = montant
    await afficher_methodes_paiement(update, context)

async def afficher_methodes_paiement(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton(m, callback_data=f'paiement_methode_{m}')] for m in METHODES_PAIEMENT]
    keyboard.append([InlineKeyboardButton("🔙 RETOUR MENU", callback_data='retour_menu')])
    await update.message.reply_text(
        "💰 Choisissez la méthode de paiement :",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    context.user_data['etape'] = 'attente_methode_paiement'

async def force_montant(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    montant = float(query.data.replace('force_montant_', ''))
    context.user_data['paiement_montant'] = montant
    await afficher_methodes_paiement(update, context)

async def choisir_methode_paiement(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    methode = query.data.replace('paiement_methode_', '')
    cid = context.user_data['paiement_client_id']
    montant = context.user_data['paiement_montant']
    db.ajouter_paiement(cid, montant, methode)
    client = db.get_client(cid)
    total = db.total_paye_client(cid)
    reste = client[6] - total
    await query.edit_message_text(
        f"✅ *PAIEMENT ENREGISTRÉ !*\n\n"
        f"Client: {client[1]} {client[2]}\n"
        f"Montant: {montant}\n"
        f"Méthode: {methode}\n"
        f"Total payé: {total}\n"
        f"Reste: {reste}",
        parse_mode='Markdown'
    )
    keyboard = [[InlineKeyboardButton("🔙 RETOUR MENU", callback_data='retour_menu')]]
    await query.message.reply_text(
        "Retour au menu ?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    context.user_data.clear()

# ---------- AUTRES FONCTIONS SIMPLIFIÉES ----------
async def rechercher_client(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.callback_query.edit_message_text("🔍 Recherche (à implémenter)")

async def liste_clients(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    clients = db.get_tous_clients_actifs()
    if not clients:
        await update.callback_query.edit_message_text("📭 Aucun client actif.")
        return
    texte = "📋 *CLIENTS ACTIFS*\n\n"
    for c in clients:
        cid, prenom, nom, _, _, _, montant, date_lim, statut, _ = c
        total = db.total_paye_client(cid)
        reste = montant - total
        voyages = db.get_voyages_client(cid)
        couleur = voyages[0][3] if voyages else ""
        texte += f"{couleur} {prenom} {nom} - Reste: {reste}/{montant}\n"
        if date_lim:
            texte += f"   📅 {date_lim}\n"
    await update.callback_query.edit_message_text(texte, parse_mode='Markdown')

async def prochains_paiements(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    clients = db.get_paiements_imminents(30)
    if not clients:
        await update.callback_query.edit_message_text("✅ Aucun paiement imminent.")
        return
    texte = "💰 *PROCHAINS PAIEMENTS*\n\n"
    for c in clients:
        cid, prenom, nom, _, _, _, montant, date_lim, _, _ = c
        total = db.total_paye_client(cid)
        reste = montant - total
        paiements = db.get_paiements_client(cid)
        methode = paiements[0][3] if paiements else "Non définie"
        voyages = db.get_voyages_client(cid)
        couleur = voyages[0][3] if voyages else ""
        try:
            jours = (datetime.strptime(date_lim, '%d/%m/%Y') - datetime.now()).days
            if jours < 0:
                urgence = "🔴 EN RETARD"
            elif jours == 0:
                urgence = "⚠️ AUJOURD'HUI"
            else:
                urgence = f"📅 Dans {jours}j"
        except:
            urgence = "Date invalide"
        texte += f"{couleur}*{prenom} {nom}*\n{urgence}\n💰 Reste: {reste}/{montant}\n💳 {methode}\n📅 {date_lim}\n━━━━━━━━━━\n"
    await update.callback_query.edit_message_text(texte, parse_mode='Markdown')

async def statistiques(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    stats = db.get_statistiques()
    texte = "📊 *STATISTIQUES*\n\n"
    texte += f"💰 Total encaissé : {stats['total_global']}\n"
    texte += f"📅 Ce mois-ci : {stats['ce_mois']}\n"
    texte += f"👥 Clients actifs : {stats['clients_actifs']}\n"
    texte += f"📁 Clients terminés : {stats['clients_termines']}\n\n"
    texte += "Par méthode :\n"
    for m, montant in stats['par_methode'].items():
        if montant > 0:
            texte += f"  {m} : {montant}\n"
    await update.callback_query.edit_message_text(texte, parse_mode='Markdown')

async def clients_termines(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    clients = db.get_clients_termines()
    if not clients:
        await update.callback_query.edit_message_text("📭 Aucun client terminé.")
        return
    texte = "📁 *CLIENTS TERMINÉS*\n\n"
    for c in clients[:15]:
        cid, prenom, nom, _, _, _, montant, _, _, _ = c
        total = db.total_paye_client(cid)
        texte += f"• {prenom} {nom} - Payé: {total}/{montant}\n"
    await update.callback_query.edit_message_text(texte, parse_mode='Markdown')

async def export(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.callback_query.edit_message_text("📤 Génération de l'export...")
    df_c, df_p, df_h, df_v = db.export_donnees()
    with BytesIO() as output:
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_c.to_excel(writer, sheet_name='Clients', index=False)
            df_p.to_excel(writer, sheet_name='Paiements', index=False)
            df_h.to_excel(writer, sheet_name='Historique', index=False)
            df_v.to_excel(writer, sheet_name='Voyages', index=False)
        output.seek(0)
        await update.effective_chat.send_document(
            document=output,
            filename=f'export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        )
    await update.effective_chat.send_message(
        "✅ Export terminé !",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 RETOUR MENU", callback_data='retour_menu')]])
    )

# ---------- NOTIFICATIONS ----------
async def check_paiements_imminents(context: ContextTypes.DEFAULT_TYPE):
    maintenant = datetime.now()
    clients = db.get_paiements_imminents(7)
    for c in clients:
        cid, prenom, nom, _, _, _, montant, date_lim, _, _ = c
        total = db.total_paye_client(cid)
        reste = montant - total
        paiements = db.get_paiements_client(cid)
        methode = paiements[0][3] if paiements else "Non définie"
        voyages = db.get_voyages_client(cid)
        couleur = voyages[0][3] if voyages else ""
        try:
            jours = (datetime.strptime(date_lim, '%d/%m/%Y') - maintenant).days
            if 0 <= jours <= 7:
                message = (f"⏰ *RAPPEL - {jours} JOURS*\n\n"
                           f"{couleur}👤 {prenom} {nom}\n"
                           f"💰 Reste: {reste}/{montant}\n"
                           f"💳 Méthode: {methode}\n"
                           f"📅 Limite: {date_lim}")
                await context.bot.send_message(chat_id=ADMIN_ID, text=message, parse_mode='Markdown')
        except:
            continue

# ---------- MAIN ----------
def main():
    print("🚀 Démarrage du bot...")
    print(f"🤖 Bot: {BOT_USERNAME}")
    print(f"👤 Admin ID: {ADMIN_ID}")

    app = Application.builder().token(TOKEN).build()

    # Commandes
    app.add_handler(CommandHandler("start", menu_principal))

    # Menu principal
    app.add_handler(CallbackQueryHandler(menu_principal, pattern='^retour_menu$'))

    # Ajout client
    app.add_handler(CallbackQueryHandler(ajouter_client, pattern='^menu_ajouter$'))

    # Modifications client
    app.add_handler(CallbackQueryHandler(modif_champ, pattern='^modif_'))
    app.add_handler(CallbackQueryHandler(toggle_voyage, pattern='^toggle_voyage_'))
    app.add_handler(CallbackQueryHandler(set_methode, pattern='^set_methode_'))
    app.add_handler(CallbackQueryHandler(valider_client, pattern='^valider_client$'))
    app.add_handler(CallbackQueryHandler(retour_formulaire, pattern='^retour_formulaire$'))

    # Voyages
    app.add_handler(CallbackQueryHandler(menu_voyages, pattern='^menu_voyages$'))
    app.add_handler(CallbackQueryHandler(voyage_creer, pattern='^voyage_creer$'))
    app.add_handler(CallbackQueryHandler(voyage_choisir_couleur, pattern='^voyage_couleur_'))
    app.add_handler(CallbackQueryHandler(voyage_detail, pattern='^voyage_detail_'))

    # Paiement reçu
    app.add_handler(CallbackQueryHandler(paiement_recu, pattern='^menu_paiement_recu$'))
    app.add_handler(CallbackQueryHandler(paiement_client_selectionne, pattern='^paiement_client_'))
    app.add_handler(CallbackQueryHandler(force_montant, pattern='^force_montant_'))
    app.add_handler(CallbackQueryHandler(choisir_methode_paiement, pattern='^paiement_methode_'))

    # Autres menus
    app.add_handler(CallbackQueryHandler(rechercher_client, pattern='^menu_rechercher$'))
    app.add_handler(CallbackQueryHandler(liste_clients, pattern='^menu_liste$'))
    app.add_handler(CallbackQueryHandler(prochains_paiements, pattern='^menu_rappels$'))
    app.add_handler(CallbackQueryHandler(statistiques, pattern='^menu_stats$'))
    app.add_handler(CallbackQueryHandler(clients_termines, pattern='^menu_termines$'))
    app.add_handler(CallbackQueryHandler(export, pattern='^menu_export$'))

    # Messages texte
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, recevoir_prenom))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, recevoir_nom))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, voyage_recevoir_nom))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, voyage_recevoir_date))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, recevoir_modification))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, recevoir_montant_paiement))

    # Notifications
    job_queue = app.job_queue
    if job_queue:
        job_queue.run_daily(check_paiements_imminents, time=time(hour=9, minute=30), chat_id=ADMIN_ID)

    print("✅ Bot démarré !")
    print(f"📱 Allez sur Telegram et tapez /start")
    app.run_polling()

if __name__ == '__main__':
    main()
