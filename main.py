import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from database import Database
from datetime import datetime, time
import pandas as pd
from io import BytesIO

# 🔐 VOTRE TOKEN
TOKEN = "8489899130:AAFAFe3tkKUrixHokYQO_d0Pt3wkicGZX80"

# Nom d'utilisateur du bot
BOT_USERNAME = "@gestionpaiementav_bot"

logging.basicConfig(level=logging.INFO)
db = Database()

# Méthodes de paiement
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
    
    message_texte = (
        "🚀 MENU PRINCIPAL - GESTION PAIEMENTS\n\n"
        f"Bot: {BOT_USERNAME}\n"
        "Sélectionnez une option :"
    )
    
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        await query.edit_message_text(
            text=message_texte,
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(
            text=message_texte,
            reply_markup=reply_markup
        )

# ---------- AJOUT CLIENT (ÉTAPE 1: PRÉNOM) ----------
async def ajouter_client(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    # Initialiser un nouveau client
    context.user_data['nouveau_client'] = {
        'prenom': '',
        'nom': '',
        'telephone': '',
        'email': '',
        'description': '',
        'montant_du': 0,
        'date_limite': '',
        'methode_paiement': '',
        'voyages': []  # Liste des IDs de voyages
    }
    
    # Première question : le prénom
    keyboard = [[InlineKeyboardButton("🔙 RETOUR MENU", callback_data='retour_menu')]]
    
    await query.edit_message_text(
        "👤 *AJOUT D'UN NOUVEAU CLIENT - ÉTAPE 1/2*\n\n"
        "✏️ Envoyez le *prénom* du client :",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )
    context.user_data['etape'] = 'ajout_prenom'

async def recevoir_prenom(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('etape') != 'ajout_prenom':
        return
    
    prenom = update.message.text
    context.user_data['nouveau_client']['prenom'] = prenom
    
    # Deuxième question : le nom
    keyboard = [[InlineKeyboardButton("🔙 RETOUR MENU", callback_data='retour_menu')]]
    
    await update.message.reply_text(
        f"✅ Prénom enregistré : *{prenom}*\n\n"
        "👤 *AJOUT D'UN NOUVEAU CLIENT - ÉTAPE 2/2*\n\n"
        "✏️ Envoyez le *nom* du client :",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )
    context.user_data['etape'] = 'ajout_nom'

async def recevoir_nom(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('etape') != 'ajout_nom':
        return
    
    nom = update.message.text
    context.user_data['nouveau_client']['nom'] = nom
    
    # Afficher le formulaire complet avec tous les boutons
    await update.message.reply_text(
        f"✅ Nom enregistré : *{nom}*\n\n"
        "📋 Vous pouvez maintenant compléter les autres informations :",
        parse_mode='Markdown'
    )
    
    await afficher_formulaire_client(update, context)

# ---------- FORMULAIRE CLIENT COMPLET ----------
async def afficher_formulaire_client(update: Update, context: ContextTypes.DEFAULT_TYPE):
    client = context.user_data.get('nouveau_client', {})
    
    voyages = db.get_tous_voyages()
    
    # Texte récapitulatif
    prenom = client.get('prenom', '')
    nom = client.get('nom', '')
    nom_complet = f"{prenom} {nom}".strip()
    
    keyboard = [
        [InlineKeyboardButton(
            f"{'✅' if client.get('prenom') else '❌'} Prénom: {client.get('prenom', 'Non défini')[:20]}",
            callback_data='edit_prenom'
        )],
        [InlineKeyboardButton(
            f"{'✅' if client.get('nom') else '❌'} Nom: {client.get('nom', 'Non défini')[:20]}",
            callback_data='edit_nom'
        )],
        [InlineKeyboardButton(
            f"{'✅' if client.get('telephone') else '❌'} Téléphone: {client.get('telephone', 'Non défini')[:20]}",
            callback_data='edit_telephone'
        )],
        [InlineKeyboardButton(
            f"{'✅' if client.get('email') else '❌'} Email: {client.get('email', 'Non défini')[:20]}",
            callback_data='edit_email'
        )],
        [InlineKeyboardButton(
            f"{'✅' if client.get('description') else '❌'} Description: {client.get('description', 'Non défini')[:20]}",
            callback_data='edit_description'
        )],
        [InlineKeyboardButton(
            f"{'✅' if client.get('montant_du', 0) > 0 else '❌'} Montant dû: {client.get('montant_du', 0)}",
            callback_data='edit_montant'
        )],
        [InlineKeyboardButton(
            f"{'✅' if client.get('date_limite') else '❌'} Date limite: {client.get('date_limite', 'Non défini')}",
            callback_data='edit_date'
        )],
        [InlineKeyboardButton(
            f"{'✅' if client.get('methode_paiement') else '❌'} Méthode: {client.get('methode_paiement', 'Non défini')[:20]}",
            callback_data='edit_methode'
        )],
    ]
    
    # Ajouter les voyages
    if voyages:
        voyage_text = "✈️ Voyages: "
        if client.get('voyages'):
            noms_voyages = []
            for vid in client['voyages']:
                v = db.get_voyage(vid)
                if v:
                    noms_voyages.append(f"{v[3]}{v[1]}")
            if noms_voyages:
                voyage_text += ", ".join(noms_voyages)
            else:
                voyage_text += "Non défini"
        else:
            voyage_text += "Non défini"
        
        keyboard.append([InlineKeyboardButton(voyage_text, callback_data='edit_voyages')])
    
    keyboard.append([InlineKeyboardButton("✅ VALIDER LE CLIENT", callback_data='valider_client')])
    keyboard.append([InlineKeyboardButton("🔙 RETOUR MENU", callback_data='retour_menu')])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if hasattr(update, 'callback_query') and update.callback_query:
        query = update.callback_query
        await query.edit_message_text(
            f"👤 *FICHE CLIENT - {nom_complet}*\n\n"
            "Cliquez sur chaque champ pour le modifier :",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            f"👤 *FICHE CLIENT - {nom_complet}*\n\n"
            "Cliquez sur chaque champ pour le modifier :",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

# ---------- MODIFICATION DES CHAMPS ----------
async def edit_champ(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    champ = query.data.replace('edit_', '')
    context.user_data['champ_en_cours'] = champ
    
    messages = {
        'prenom': "✏️ Entrez le *prénom* du client :",
        'nom': "✏️ Entrez le *nom* du client :",
        'telephone': "✏️ Entrez le *téléphone* du client :",
        'email': "✏️ Entrez l'*email* du client :",
        'description': "✏️ Entrez la *description* :",
        'montant': "💰 Entrez le *montant dû* (chiffre uniquement) :",
        'date': "📅 Entrez la *date limite* (format JJ/MM/AAAA) :",
        'methode': "💳 Choisissez la *méthode de paiement* :",
        'voyages': "✈️ Choisissez les *voyages* pour ce client :",
    }
    
    if champ == 'methode':
        keyboard = []
        for methode in METHODES_PAIEMENT:
            keyboard.append([InlineKeyboardButton(methode, callback_data=f'set_methode_{methode}')])
        keyboard.append([InlineKeyboardButton("🔙 RETOUR FORMULAIRE", callback_data='retour_formulaire')])
        
        await query.edit_message_text(
            messages[champ],
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    elif champ == 'voyages':
        voyages = db.get_tous_voyages()
        keyboard = []
        for voyage in voyages:
            voyage_id, nom, date_voyage, couleur, ordre, date_creation = voyage
            # Vérifier si déjà sélectionné
            selected = voyage_id in context.user_data['nouveau_client'].get('voyages', [])
            prefix = "✅ " if selected else ""
            keyboard.append([InlineKeyboardButton(
                f"{prefix}{couleur} {nom} ({date_voyage or 'Date?'})", 
                callback_data=f'toggle_voyage_{voyage_id}'
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
        context.user_data['etape'] = f'edit_{champ}'

async def toggle_voyage(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    voyage_id = int(query.data.replace('toggle_voyage_', ''))
    
    if 'voyages' not in context.user_data['nouveau_client']:
        context.user_data['nouveau_client']['voyages'] = []
    
    if voyage_id in context.user_data['nouveau_client']['voyages']:
        context.user_data['nouveau_client']['voyages'].remove(voyage_id)
    else:
        context.user_data['nouveau_client']['voyages'].append(voyage_id)
    
    # Réafficher la liste des voyages
    await edit_champ(update, context)

async def set_methode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    methode = query.data.replace('set_methode_', '')
    context.user_data['nouveau_client']['methode_paiement'] = methode
    
    await afficher_formulaire_client(update, context)

async def recevoir_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if 'etape' not in context.user_data:
        return
    
    etape = context.user_data['etape']
    texte = update.message.text
    
    if etape == 'edit_prenom':
        context.user_data['nouveau_client']['prenom'] = texte
    elif etape == 'edit_nom':
        context.user_data['nouveau_client']['nom'] = texte
    elif etape == 'edit_telephone':
        context.user_data['nouveau_client']['telephone'] = texte
    elif etape == 'edit_email':
        context.user_data['nouveau_client']['email'] = texte
    elif etape == 'edit_description':
        context.user_data['nouveau_client']['description'] = texte
    elif etape == 'edit_montant':
        try:
            context.user_data['nouveau_client']['montant_du'] = float(texte)
        except ValueError:
            await update.message.reply_text("❌ Montant invalide.")
            return
    elif etape == 'edit_date':
        context.user_data['nouveau_client']['date_limite'] = texte
    
    context.user_data['etape'] = None
    
    await update.message.reply_text("✅ Information enregistrée !")
    await afficher_formulaire_client(update, context)

async def retour_formulaire(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await afficher_formulaire_client(update, context)

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
        db.ajouter_paiement(
            client_id=client_id,
            montant=0,
            methode=client.get('methode_paiement'),
            notes="Méthode de paiement prévue"
        )
    
    # Attribuer les voyages
    if client.get('voyages'):
        for voyage_id in client['voyages']:
            db.attribuer_voyage_client(client_id, voyage_id)
    
    # Récupérer la couleur du premier voyage pour l'affichage
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
    await update.effective_chat.send_message(
        "Retour au menu principal ?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    context.user_data.pop('nouveau_client', None)

# ---------- VOYAGES ----------
async def menu_voyages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    voyages = db.get_tous_voyages()
    
    texte = "✈️ *GESTION DES VOYAGES*\n\n"
    
    if voyages:
        texte += "Vos voyages (du plus récent au plus ancien) :\n\n"
        
        keyboard = []
        for voyage in voyages:
            voyage_id, nom, date_voyage, couleur, ordre, date_creation = voyage
            clients = db.get_clients_voyage(voyage_id)
            nb_clients = len(clients)
            
            texte += f"{couleur} *{nom}*"
            if date_voyage:
                texte += f" - {date_voyage}"
            texte += f" ({nb_clients} client{'s' if nb_clients > 1 else ''})\n"
            
            keyboard.append([InlineKeyboardButton(
                f"{couleur} {nom} ({date_voyage or 'Date?'})", 
                callback_data=f'voyage_detail_{voyage_id}'
            )])
        
        keyboard.append([InlineKeyboardButton("➕ CRÉER UN VOYAGE", callback_data='voyage_creer')])
        keyboard.append([InlineKeyboardButton("🔙 RETOUR MENU", callback_data='retour_menu')])
        
        await query.edit_message_text(
            texte,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    else:
        texte += "Aucun voyage créé pour le moment.\n\n"
        keyboard = [
            [InlineKeyboardButton("➕ CRÉER UN VOYAGE", callback_data='voyage_creer')],
            [InlineKeyboardButton("🔙 RETOUR MENU", callback_data='retour_menu')]
        ]
        
        await query.edit_message_text(
            texte,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

async def voyage_creer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    context.user_data['nouveau_voyage'] = {}
    
    keyboard = [[InlineKeyboardButton("🔙 RETOUR VOYAGES", callback_data='menu_voyages')]]
    
    await query.edit_message_text(
        "✈️ *CRÉER UN VOYAGE - ÉTAPE 1/3*\n\n"
        "📝 Envoyez le *nom* du voyage :",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )
    context.user_data['etape'] = 'voyage_nom'

async def voyage_recevoir_nom(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('etape') != 'voyage_nom':
        return
    
    nom = update.message.text
    context.user_data['nouveau_voyage']['nom'] = nom
    
    keyboard = [[InlineKeyboardButton("🔙 RETOUR VOYAGES", callback_data='menu_voyages')]]
    
    await update.message.reply_text(
        "✈️ *CRÉER UN VOYAGE - ÉTAPE 2/3*\n\n"
        f"Nom: *{nom}*\n\n"
        "📅 Envoyez la *date* du voyage (format MM/AAAA)\n"
        "Exemple: `06/2024` pour Juin 2024\n\n"
        "Ou envoyez 'skip' pour passer",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )
    context.user_data['etape'] = 'voyage_date'

async def voyage_recevoir_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('etape') != 'voyage_date':
        return
    
    date_texte = update.message.text
    
    if date_texte.lower() == 'skip':
        context.user_data['nouveau_voyage']['date'] = ''
    else:
        if len(date_texte) == 7 and date_texte[2] == '/':
            context.user_data['nouveau_voyage']['date'] = date_texte
        else:
            await update.message.reply_text("❌ Format incorrect. Utilisez MM/AAAA (ex: 06/2024) ou 'skip'")
            return
    
    # AFFICHAGE DES COULEURS EXACTEMENT COMME DEMANDÉ
    couleurs = ["🔴", "🟠", "🟡", "🟢", "🔵", "🟣", "🟤", "⚫", "⚪"]
    
    keyboard = []
    
    # Première ligne : 3 couleurs
    row1 = []
    for i in range(3):
        row1.append(InlineKeyboardButton(couleurs[i], callback_data=f'voyage_couleur_{couleurs[i]}'))
    keyboard.append(row1)
    
    # Deuxième ligne : 3 couleurs
    row2 = []
    for i in range(3, 6):
        row2.append(InlineKeyboardButton(couleurs[i], callback_data=f'voyage_couleur_{couleurs[i]}'))
    keyboard.append(row2)
    
    # Troisième ligne : 3 couleurs
    row3 = []
    for i in range(6, 9):
        row3.append(InlineKeyboardButton(couleurs[i], callback_data=f'voyage_couleur_{couleurs[i]}'))
    keyboard.append(row3)
    
    # Bouton retour
    keyboard.append([InlineKeyboardButton("🔙 RETOUR", callback_data='menu_voyages')])
    
    await update.message.reply_text(
        f"✈️ *CRÉER UN VOYAGE - ÉTAPE 3/3*\n\n"
        f"Nom: *{context.user_data['nouveau_voyage']['nom']}*\n"
        f"Date: *{context.user_data['nouveau_voyage'].get('date', 'Non définie')}*\n\n"
        f"🎨 Choisissez une couleur pour ce voyage :\n",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )
    context.user_data['etape'] = 'voyage_couleur'

async def voyage_choisir_couleur(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    couleur = query.data.replace('voyage_couleur_', '')
    voyage_data = context.user_data.get('nouveau_voyage', {})
    
    voyage_id = db.ajouter_voyage(
        nom=voyage_data['nom'],
        date_voyage=voyage_data.get('date', ''),
        couleur=couleur
    )
    
    await query.edit_message_text(
        f"✅ *VOYAGE CRÉÉ AVEC SUCCÈS !*\n\n"
        f"{couleur} *{voyage_data['nom']}*\n"
        f"📅 Date: {voyage_data.get('date', 'Non définie')}\n"
        f"🎨 Couleur: {couleur}\n"
        f"🆔 ID: `{voyage_id}`",
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
    
    context.user_data.pop('nouveau_voyage', None)
    context.user_data['etape'] = None

async def voyage_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    voyage_id = int(query.data.replace('voyage_detail_', ''))
    voyage = db.get_voyage(voyage_id)
    
    if not voyage:
        await query.edit_message_text("❌ Voyage introuvable")
        return
    
    voyage_id, nom, date_voyage, couleur, ordre, date_creation = voyage
    clients = db.get_clients_voyage(voyage_id)
    
    texte = f"{couleur} *{nom}*\n"
    if date_voyage:
        texte += f"📅 Date: {date_voyage}\n"
    texte += f"👥 *Clients participants:* {len(clients)}\n\n"
    
    keyboard = []
    
    if clients:
        texte += "Liste des clients :\n"
        for client in clients[:10]:
            client_id, prenom, nom, tel, email, desc, montant_du, date_limite, statut, date_crea = client
            total_paye = db.total_paye_client(client_id)
            reste = montant_du - total_paye
            texte += f"  • {prenom} {nom} - Reste: {reste}/{montant_du}\n"
            
            keyboard.append([InlineKeyboardButton(
                f"👤 {prenom} {nom}", 
                callback_data=f'detail_{client_id}'
            )])
    else:
        texte += "Aucun client dans ce voyage pour le moment."
    
    keyboard.append([
        InlineKeyboardButton("✏️ MODIFIER", callback_data=f'voyage_modifier_{voyage_id}'),
        InlineKeyboardButton("🗑️ SUPPRIMER", callback_data=f'voyage_supprimer_{voyage_id}')
    ])
    keyboard.append([InlineKeyboardButton("🔙 RETOUR VOYAGES", callback_data='menu_voyages')])
    
    await query.edit_message_text(
        texte,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def voyage_modifier(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    voyage_id = int(query.data.replace('voyage_modifier_', ''))
    context.user_data['voyage_modif_id'] = voyage_id
    
    voyage = db.get_voyage(voyage_id)
    
    keyboard = [
        [InlineKeyboardButton("📝 Nom", callback_data=f'voyage_edit_nom_{voyage_id}')],
        [InlineKeyboardButton("📅 Date", callback_data=f'voyage_edit_date_{voyage_id}')],
        [InlineKeyboardButton("🎨 Couleur", callback_data=f'voyage_edit_couleur_{voyage_id}')],
        [InlineKeyboardButton("🔙 RETOUR", callback_data=f'voyage_detail_{voyage_id}')]
    ]
    
    await query.edit_message_text(
        f"✏️ *MODIFIER LE VOYAGE*\n\n"
        f"Voyage: {voyage[1]}\n\n"
        f"Que souhaitez-vous modifier ?",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def voyage_supprimer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    voyage_id = int(query.data.replace('voyage_supprimer_', ''))
    context.user_data['voyage_supprimer_id'] = voyage_id
    
    voyage = db.get_voyage(voyage_id)
    
    keyboard = [
        [
            InlineKeyboardButton("✅ OUI", callback_data=f'voyage_delete_confirm_{voyage_id}'),
            InlineKeyboardButton("❌ NON", callback_data=f'voyage_detail_{voyage_id}')
        ]
    ]
    
    await query.edit_message_text(
        f"⚠️ *CONFIRMATION SUPPRESSION*\n\n"
        f"Voulez-vous vraiment supprimer le voyage *{voyage[1]}* ?\n\n"
        f"Cette action est irréversible et retirera ce voyage de tous les clients.",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def voyage_delete_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    voyage_id = int(query.data.replace('voyage_delete_confirm_', ''))
    db.supprimer_voyage(voyage_id)
    
    await query.edit_message_text("✅ Voyage supprimé avec succès !")
    
    keyboard = [[InlineKeyboardButton("✈️ RETOUR VOYAGES", callback_data='menu_voyages')]]
    await query.message.reply_text(
        "Retour à la liste des voyages ?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ---------- PAIEMENT REÇU ----------
async def paiement_recu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    clients = db.get_tous_clients_actifs()
    
    if not clients:
        await query.edit_message_text("❌ Aucun client actif pour enregistrer un paiement.")
        keyboard = [[InlineKeyboardButton("🔙 RETOUR MENU", callback_data='retour_menu')]]
        await query.message.reply_text(
            "Retour au menu ?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    texte = "💰 *ENREGISTRER UN PAIEMENT REÇU*\n\n"
    texte += "Sélectionnez le client qui a effectué le paiement :\n\n"
    
    keyboard = []
    for client in clients:
        client_id, prenom, nom, _, _, _, montant_du, date_limite, _, _ = client
        total_paye = db.total_paye_client(client_id)
        reste = montant_du - total_paye
        voyages = db.get_voyages_client(client_id)
        couleur = voyages[0][3] if voyages else ""
        nom_complet = f"{prenom} {nom}".strip()
        keyboard.append([InlineKeyboardButton(
            f"{couleur} {nom_complet} (Reste: {reste})", 
            callback_data=f'paiement_client_{client_id}'
        )])
    
    keyboard.append([InlineKeyboardButton("🔙 RETOUR MENU", callback_data='retour_menu')])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        texte,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def paiement_client_selectionne(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Un client a été sélectionné pour le paiement"""
    query = update.callback_query
    await query.answer()
    
    client_id = int(query.data.replace('paiement_client_', ''))
    context.user_data['paiement_client_id'] = client_id
    
    client = db.get_client(client_id)
    total_paye = db.total_paye_client(client_id)
    reste = client[6] - total_paye  # montant_du est à l'index 6
    
    context.user_data['paiement_reste'] = reste
    
    keyboard = [[InlineKeyboardButton("🔙 RETOUR MENU", callback_data='retour_menu')]]
    
    nom_complet = f"{client[1]} {client[2]}".strip()  # prenom et nom
    
    await query.edit_message_text(
        f"💰 *MONTANT DU PAIEMENT*\n\n"
        f"Client: *{nom_complet}*\n"
        f"💰 Montant restant dû: *{reste}*\n\n"
        f"✏️ Envoyez le montant reçu :",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )
    context.user_data['etape'] = 'montant_paiement_recu'

async def recevoir_montant_paiement_recu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reçoit le montant du paiement"""
    if context.user_data.get('etape') != 'montant_paiement_recu':
        return
    
    try:
        montant = float(update.message.text)
        client_id = context.user_data.get('paiement_client_id')
        reste = context.user_data.get('paiement_reste', 0)
        
        if montant > reste:
            keyboard = [
                [InlineKeyboardButton("✅ Oui, enregistrer quand même", callback_data=f'force_montant_{montant}')],
                [InlineKeyboardButton("❌ Non, annuler", callback_data='retour_menu')]
            ]
            await update.message.reply_text(
                f"⚠️ Attention ! Le montant saisi ({montant}) est supérieur au reste dû ({reste}).\n\n"
                f"Voulez-vous quand même enregistrer ce paiement ?",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            context.user_data['montant_force'] = montant
            return
        
        context.user_data['paiement_montant'] = montant
        
        keyboard = []
        for methode in METHODES_PAIEMENT:
            keyboard.append([InlineKeyboardButton(methode, callback_data=f'paiement_methode_{methode}')])
        keyboard.append([InlineKeyboardButton("🔙 RETOUR MENU", callback_data='retour_menu')])
        
        await update.message.reply_text(
            f"💰 Montant: *{montant}*\n\n"
            f"Choisissez la méthode de paiement :",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        context.user_data['etape'] = 'methode_paiement_recu'
        
    except ValueError:
        await update.message.reply_text("❌ Montant invalide. Veuillez entrer un nombre.")
        return

async def force_montant(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Force l'enregistrement d'un montant supérieur au reste"""
    query = update.callback_query
    await query.answer()
    
    montant = float(query.data.replace('force_montant_', ''))
    context.user_data['paiement_montant'] = montant
    
    keyboard = []
    for methode in METHODES_PAIEMENT:
        keyboard.append([InlineKeyboardButton(methode, callback_data=f'paiement_methode_{methode}')])
    keyboard.append([InlineKeyboardButton("🔙 RETOUR MENU", callback_data='retour_menu')])
    
    await query.edit_message_text(
        f"💰 Montant forcé: *{montant}*\n\n"
        f"Choisissez la méthode de paiement :",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )
    context.user_data['etape'] = 'methode_paiement_recu'

async def choisir_methode_paiement(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Choisit la méthode et enregistre le paiement"""
    query = update.callback_query
    await query.answer()
    
    methode = query.data.replace('paiement_methode_', '')
    client_id = context.user_data.get('paiement_client_id')
    montant = context.user_data.get('paiement_montant')
    
    db.ajouter_paiement(client_id, montant, methode)
    
    client = db.get_client(client_id)
    total_paye = db.total_paye_client(client_id)
    reste = client[6] - total_paye
    
    nom_complet = f"{client[1]} {client[2]}".strip()
    
    await query.edit_message_text(
        f"✅ *PAIEMENT ENREGISTRÉ !*\n\n"
        f"Client: {nom_complet}\n"
        f"Montant: {montant}\n"
        f"Méthode: {methode}\n"
        f"Nouveau total payé: {total_paye}\n"
        f"Reste à payer: {reste}",
        parse_mode='Markdown'
    )
    
    keyboard = [[InlineKeyboardButton("🔙 RETOUR MENU", callback_data='retour_menu')]]
    await query.message.reply_text(
        "Retour au menu ?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    context.user_data['etape'] = None

# ---------- LISTE CLIENTS ACTIFS ----------
async def liste_clients(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    clients = db.get_tous_clients_actifs()
    
    if not clients:
        await query.edit_message_text("📭 Aucun client actif")
        keyboard = [[InlineKeyboardButton("🔙 RETOUR MENU", callback_data='retour_menu')]]
        await query.message.reply_text(
            "Retour au menu ?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    texte = "📋 *LISTE DES CLIENTS ACTIFS*\n\n"
    texte += "Cliquez sur un client pour voir ses détails :\n\n"
    
    keyboard = []
    
    for client in clients:
        client_id, prenom, nom, tel, email, desc, montant_du, date_limite, statut, date_crea = client
        voyages = db.get_voyages_client(client_id)
        couleur = voyages[0][3] if voyages else ""
        nom_complet = f"{prenom} {nom}".strip()
        keyboard.append([InlineKeyboardButton(f"{couleur}👤 {nom_complet}", callback_data=f'detail_{client_id}')])
    
    keyboard.append([InlineKeyboardButton("🔙 RETOUR MENU", callback_data='retour_menu')])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        texte,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

# ---------- DÉTAILS CLIENT COMPLET ----------
async def details_client_complet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    client_id = int(query.data.split('_')[1])
    context.user_data['client_en_cours'] = client_id
    
    client = db.get_client(client_id)
    if not client:
        await query.edit_message_text("❌ Client introuvable")
        return
    
    client_id, prenom, nom, tel, email, desc, montant_du, date_limite, statut, date_crea = client
    total_paye = db.total_paye_client(client_id)
    reste = montant_du - total_paye
    
    voyages = db.get_voyages_client(client_id)
    couleur = voyages[0][3] if voyages else ""
    
    paiements = db.get_paiements_client(client_id)
    
    nom_complet = f"{prenom} {nom}".strip()
    
    texte = f"{couleur}📋 *FICHE CLIENT COMPLÈTE*\n\n"
    texte += f"{couleur}👤 *{nom_complet}*\n"
    texte += f"🆔 ID: `{client_id}`\n"
    if tel: texte += f"📞 Téléphone: {tel}\n"
    if email: texte += f"📧 Email: {email}\n"
    if desc: texte += f"📝 Description: {desc}\n"
    
    if voyages:
        texte += "✈️ *Voyages:*\n"
        for v in voyages:
            v_id, v_nom, v_date, v_couleur, v_ordre, v_crea = v
            texte += f"  {v_couleur} {v_nom} ({v_date or 'Date?'})\n"
    
    texte += f"\n💰 *Montant dû:* {montant_du}\n"
    texte += f"💵 *Total payé:* {total_paye}\n"
    texte += f"⚠️ *Reste à payer:* {reste}\n"
    if date_limite: texte += f"📅 *Date limite:* {date_limite}\n"
    texte += f"✅ *Statut:* {statut}\n"
    
    if paiements:
        texte += f"\n📜 *Historique des paiements:*\n"
        for p in paiements:
            p_id, _, p_montant, p_methode, p_date, p_notes = p
            date_str = p_date[:10] if p_date else "Date inconnue"
            texte += f"  • {date_str} - {p_montant} - {p_methode}\n"
            if p_notes:
                texte += f"    Notes: {p_notes}\n"
    
    keyboard = [
        [InlineKeyboardButton("💰 AJOUTER PAIEMENT", callback_data=f'payer_{client_id}')],
        [InlineKeyboardButton("✏️ MODIFIER", callback_data=f'modifier_client_{client_id}')],
    ]
    
    if statut == 'actif':
        keyboard.append([InlineKeyboardButton("✅ VALIDER (Terminé)", callback_data=f'valider_manuel_{client_id}')])
        keyboard.append([InlineKeyboardButton("🗑️ SUPPRIMER", callback_data=f'supprimer_client_{client_id}')])
    else:
        keyboard.append([InlineKeyboardButton("🔄 RÉACTIVER", callback_data=f'reactiver_{client_id}')])
    
    keyboard.append([InlineKeyboardButton("🔙 RETOUR LISTE", callback_data='menu_liste')])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(texte, reply_markup=reply_markup, parse_mode='Markdown')

# ---------- MODIFICATION CLIENT (DEPUIS LA FICHE) ----------
async def modifier_client(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    client_id = int(query.data.replace('modifier_client_', ''))
    client = db.get_client(client_id)
    
    if not client:
        await query.edit_message_text("❌ Client introuvable")
        return
    
    # Charger les données du client dans user_data pour modification
    client_id, prenom, nom, tel, email, desc, montant_du, date_limite, statut, date_crea = client
    
    # Récupérer les voyages du client
    voyages_client = db.get_voyages_client(client_id)
    voyages_ids = [v[0] for v in voyages_client]
    
    context.user_data['nouveau_client'] = {
        'id': client_id,
        'prenom': prenom,
        'nom': nom,
        'telephone': tel or '',
        'email': email or '',
        'description': desc or '',
        'montant_du': montant_du,
        'date_limite': date_limite or '',
        'methode_paiement': '',
        'voyages': voyages_ids
    }
    
    await afficher_formulaire_client(update, context)

# ---------- RECHERCHE CLIENT ----------
async def rechercher_client(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    keyboard = [[InlineKeyboardButton("🔙 RETOUR MENU", callback_data='retour_menu')]]
    
    await query.edit_message_text(
        "🔍 *RECHERCHER UN CLIENT*\n\n"
        "Envoyez le nom du client :",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )
    context.user_data['etape'] = 'recherche'

async def recevoir_recherche(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('etape') != 'recherche':
        return
    
    recherche = update.message.text
    clients = db.rechercher_client(recherche)
    
    if not clients:
        await update.message.reply_text("❌ Aucun client trouvé")
        keyboard = [[InlineKeyboardButton("🔙 RETOUR MENU", callback_data='retour_menu')]]
        await update.message.reply_text(
            "Retour au menu ?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    for client in clients[:5]:
        client_id, prenom, nom, tel, email, desc, montant_du, date_limite, statut, date_crea = client
        total_paye = db.total_paye_client(client_id)
        reste = montant_du - total_paye
        
        voyages = db.get_voyages_client(client_id)
        couleur = voyages[0][3] if voyages else ""
        
        nom_complet = f"{prenom} {nom}".strip()
        
        texte = f"{couleur}👤 *{nom_complet}*\n"
        texte += f"🆔 ID: {client_id}\n"
        texte += f"💰 Dû: {montant_du} | Payé: {total_paye} | Reste: {reste}\n"
        if date_limite:
            texte += f"📅 Limite: {date_limite}\n"
        
        keyboard = [
            [InlineKeyboardButton("💰 PAIEMENT", callback_data=f'payer_{client_id}')],
            [InlineKeyboardButton("🔙 RETOUR MENU", callback_data='retour_menu')]
        ]
        
        await update.message.reply_text(
            texte,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    context.user_data['etape'] = None

# ---------- PROCHAINS PAIEMENTS ----------
async def prochains_paiements(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    clients = db.get_paiements_imminents(30)
    
    if not clients:
        await query.edit_message_text("✅ Aucun paiement à prévoir dans les 30 prochains jours.")
        keyboard = [[InlineKeyboardButton("🔙 RETOUR MENU", callback_data='retour_menu')]]
        await query.message.reply_text(
            "Retour au menu ?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    texte = "💰 *PROCHAINS PAIEMENTS*\n\n"
    
    for client in clients:
        client_id, prenom, nom, _, _, _, montant_du, date_limite, _, _ = client
        total_paye = db.total_paye_client(client_id)
        reste = montant_du - total_paye
        
        paiements = db.get_paiements_client(client_id)
        methode = "Non définie"
        if paiements:
            for p in paiements:
                if p[3]:
                    methode = p[3]
                    break
        
        voyages = db.get_voyages_client(client_id)
        couleur = voyages[0][3] if voyages else ""
        nom_complet = f"{prenom} {nom}".strip()
        
        try:
            date_obj = datetime.strptime(date_limite, '%d/%m/%Y')
            jours_restants = (date_obj - datetime.now()).days
            if jours_restants < 0:
                urgence = "🔴 EN RETARD"
            elif jours_restants == 0:
                urgence = "⚠️ AUJOURD'HUI"
            elif jours_restants <= 3:
                urgence = f"🔸 URGENT ({jours_restants}j)"
            elif jours_restants <= 7:
                urgence = f"🔹 Cette semaine ({jours_restants}j)"
            else:
                urgence = f"📅 Dans {jours_restants}j"
        except:
            urgence = "📅 Date invalide"
        
        texte += f"{couleur}*{nom_complet}*\n"
        texte += f"{urgence}\n"
        texte += f"💰 Reste: {reste}/{montant_du}\n"
        texte += f"💳 Méthode: {methode}\n"
        texte += f"📅 Limite: {date_limite}\n"
        texte += "━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    keyboard = [[InlineKeyboardButton("🔙 RETOUR MENU", callback_data='retour_menu')]]
    
    await query.edit_message_text(
        texte,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

# ---------- STATISTIQUES ----------
async def statistiques(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    stats = db.get_statistiques()
    
    texte = "📊 *STATISTIQUES*\n\n"
    texte += f"💰 *Total encaissé (global):* {stats['total_global']}\n"
    texte += f"📅 *Ce mois-ci:* {stats['ce_mois']}\n"
    texte += f"👥 *Clients actifs:* {stats['clients_actifs']}\n"
    texte += f"📁 *Clients terminés:* {stats['clients_termines']}\n\n"
    texte += "*Par méthode de paiement:*\n"
    
    for methode, montant in stats['par_methode'].items():
        if montant > 0:
            pourcentage = (montant / stats['total_global'] * 100) if stats['total_global'] > 0 else 0
            texte += f"  {methode}: {montant} ({pourcentage:.1f}%)\n"
    
    keyboard = [[InlineKeyboardButton("🔙 RETOUR MENU", callback_data='retour_menu')]]
    
    await query.edit_message_text(
        texte,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

# ---------- CLIENTS TERMINÉS ----------
async def clients_termines(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    clients = db.get_clients_termines()
    
    if not clients:
        await query.edit_message_text("📭 Aucun client terminé")
        keyboard = [[InlineKeyboardButton("🔙 RETOUR MENU", callback_data='retour_menu')]]
        await query.message.reply_text(
            "Retour au menu ?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    texte = "📁 *CLIENTS TERMINÉS (Archivés)*\n\n"
    keyboard = []
    
    for client in clients[:15]:
        client_id, prenom, nom, _, _, _, montant_du, _, _, _ = client
        total_paye = db.total_paye_client(client_id)
        voyages = db.get_voyages_client(client_id)
        couleur = voyages[0][3] if voyages else ""
        nom_complet = f"{prenom} {nom}".strip()
        texte += f"• {couleur}{nom_complet} - Payé: {total_paye}/{montant_du}\n"
        keyboard.append([InlineKeyboardButton(
            f"{couleur}🔄 RÉACTIVER {nom_complet}", 
            callback_data=f'reactiver_{client_id}'
        )])
    
    keyboard.append([InlineKeyboardButton("🔙 RETOUR MENU", callback_data='retour_menu')])
    
    await query.edit_message_text(
        texte,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

# ---------- EXPORT ----------
async def export(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text("📤 Génération de l'export...")
    
    df_clients, df_paiements, df_historique, df_voyages = db.export_donnees()
    
    with BytesIO() as output:
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_clients.to_excel(writer, sheet_name='Clients', index=False)
            df_paiements.to_excel(writer, sheet_name='Paiements', index=False)
            df_historique.to_excel(writer, sheet_name='Historique', index=False)
            df_voyages.to_excel(writer, sheet_name='Voyages', index=False)
        output.seek(0)
        
        await update.effective_chat.send_document(
            document=output,
            filename=f'export_complet_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        )
    
    keyboard = [[InlineKeyboardButton("🔙 RETOUR MENU", callback_data='retour_menu')]]
    await update.effective_chat.send_message(
        "✅ Export terminé ! Retour au menu ?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ---------- PAIEMENTS ----------
async def payer_client(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    client_id = int(query.data.split('_')[1])
    context.user_data['paiement_client_id'] = client_id
    
    client = db.get_client(client_id)
    total_paye = db.total_paye_client(client_id)
    reste = client[6] - total_paye
    
    keyboard = []
    for methode in METHODES_PAIEMENT:
        keyboard.append([InlineKeyboardButton(methode, callback_data=f'methode_{methode}')])
    
    keyboard.append([InlineKeyboardButton("🔙 RETOUR MENU", callback_data='retour_menu')])
    
    nom_complet = f"{client[1]} {client[2]}".strip()
    
    await query.edit_message_text(
        f"💰 *PAIEMENT*\n\n"
        f"Client: *{nom_complet}*\n"
        f"Reste à payer: *{reste}*\n\n"
        f"Choisissez la méthode :",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def choisir_methode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    methode = query.data.replace('methode_', '')
    context.user_data['paiement_methode'] = methode
    
    keyboard = [[InlineKeyboardButton("🔙 RETOUR MENU", callback_data='retour_menu')]]
    
    await query.edit_message_text(
        f"💰 Méthode: *{methode}*\n\n"
        f"Envoyez le montant payé :",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )
    context.user_data['etape'] = 'montant_paiement'

async def recevoir_montant(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('etape') != 'montant_paiement':
        return
    
    try:
        montant = float(update.message.text)
        client_id = context.user_data.get('paiement_client_id')
        methode = context.user_data.get('paiement_methode')
        
        db.ajouter_paiement(client_id, montant, methode)
        
        client = db.get_client(client_id)
        total_paye = db.total_paye_client(client_id)
        reste = client[6] - total_paye
        
        nom_complet = f"{client[1]} {client[2]}".strip()
        
        await update.message.reply_text(
            f"✅ *Paiement enregistré !*\n\n"
            f"Client: {nom_complet}\n"
            f"Montant: {montant}\n"
            f"Méthode: {methode}\n"
            f"Total payé: {total_paye}\n"
            f"Reste: {reste}",
            parse_mode='Markdown'
        )
        
        if reste <= 0:
            keyboard = [
                [InlineKeyboardButton("📦 ARCHIVER", callback_data=f'archiver_{client_id}')],
                [InlineKeyboardButton("🔙 RETOUR MENU", callback_data='retour_menu')]
            ]
            await update.message.reply_text(
                "💰 Client soldé ! Voulez-vous l'archiver ?",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            keyboard = [[InlineKeyboardButton("🔙 RETOUR MENU", callback_data='retour_menu')]]
            await update.message.reply_text(
                "Retour au menu ?",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        
    except ValueError:
        await update.message.reply_text("❌ Montant invalide. Veuillez entrer un nombre.")
        return
    
    context.user_data['etape'] = None

# ---------- ACTIONS SUR CLIENTS ----------
async def archiver_client(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    client_id = int(query.data.split('_')[1])
    db.archiver_client(client_id)
    
    await query.edit_message_text("✅ Client archivé avec succès !")
    
    keyboard = [[InlineKeyboardButton("🔙 RETOUR MENU", callback_data='retour_menu')]]
    await query.message.reply_text(
        "Retour au menu ?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def reactiver_client(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    client_id = int(query.data.split('_')[1])
    db.reactiver_client(client_id)
    
    await query.edit_message_text("✅ Client réactivé avec succès !")
    
    keyboard = [[InlineKeyboardButton("🔙 RETOUR MENU", callback_data='retour_menu')]]
    await query.message.reply_text(
        "Retour au menu ?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def valider_manuel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    client_id = int(query.data.replace('valider_manuel_', ''))
    db.archiver_client(client_id)
    
    client = db.get_client(client_id)
    nom_complet = f"{client[1]} {client[2]}".strip()
    
    await query.edit_message_text(
        f"✅ Client *{nom_complet}* marqué comme TERMINÉ !",
        parse_mode='Markdown'
    )
    
    keyboard = [[InlineKeyboardButton("🔙 RETOUR LISTE", callback_data='menu_liste')]]
    await query.message.reply_text(
        "Retour à la liste des clients ?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def supprimer_client(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    client_id = int(query.data.replace('supprimer_client_', ''))
    context.user_data['client_supprimer_id'] = client_id
    
    client = db.get_client(client_id)
    nom_complet = f"{client[1]} {client[2]}".strip()
    
    keyboard = [
        [
            InlineKeyboardButton("✅ OUI", callback_data=f'delete_confirm_{client_id}'),
            InlineKeyboardButton("❌ NON", callback_data=f'detail_{client_id}')
        ]
    ]
    
    await query.edit_message_text(
        f"⚠️ *CONFIRMATION SUPPRESSION*\n\n"
        f"Voulez-vous vraiment supprimer définitivement le client *{nom_complet}* ?\n\n"
        f"Cette action est irréversible et supprimera tous ses paiements !",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def delete_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    client_id = int(query.data.replace('delete_confirm_', ''))
    
    await query.edit_message_text("✅ Client supprimé définitivement !")
    
    keyboard = [[InlineKeyboardButton("🔙 RETOUR MENU", callback_data='retour_menu')]]
    await query.message.reply_text(
        "Retour au menu ?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ---------- NOTIFICATIONS AUTOMATIQUES ----------
async def check_paiements_imminents(context: ContextTypes.DEFAULT_TYPE):
    maintenant = datetime.now()
    clients = db.get_paiements_imminents(7)
    
    for client in clients:
        client_id, prenom, nom, _, _, _, montant_du, date_limite, _, _ = client
        total_paye = db.total_paye_client(client_id)
        reste = montant_du - total_paye
        
        paiements = db.get_paiements_client(client_id)
        methode = "Non définie"
        if paiements:
            for p in paiements:
                if p[3]:
                    methode = p[3]
                    break
        
        voyages = db.get_voyages_client(client_id)
        couleur = voyages[0][3] if voyages else ""
        nom_complet = f"{prenom} {nom}".strip()
        
        try:
            date_obj = datetime.strptime(date_limite, '%d/%m/%Y')
            jours_restants = (date_obj - maintenant).days
            
            if 0 <= jours_restants <= 7:
                message = (
                    f"⏰ *RAPPEL PAIEMENT - {jours_restants} JOURS*\n\n"
                    f"{couleur}👤 *{nom_complet}*\n"
                    f"💰 Reste à payer: {reste}/{montant_du}\n"
                    f"💳 Méthode prévue: {methode}\n"
                    f"📅 Date limite: {date_limite}"
                )
                
                # 👉 REMPLACEZ 123456789 PAR VOTRE ID TELEGRAM (allez sur @userinfobot)
                await context.bot.send_message(
                    chat_id=123456789,  # <--- CHANGEZ ICI !
                    text=message,
                    parse_mode='Markdown'
                )
        except:
            pass

# ---------- MAIN ----------
def main():
    print("🚀 Démarrage du bot...")
    print(f"🤖 Bot: {BOT_USERNAME}")
    app = Application.builder().token(TOKEN).build()
    
    # Commandes
    app.add_handler(CommandHandler("start", menu_principal))
    
    # Menu principal
    app.add_handler(CallbackQueryHandler(menu_principal, pattern='^retour_menu$'))
    
    # Ajout client (étapes prénom/nom)
    app.add_handler(CallbackQueryHandler(ajouter_client, pattern='^menu_ajouter$'))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, recevoir_prenom))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, recevoir_nom))
    
    # Formulaire client
    app.add_handler(CallbackQueryHandler(retour_formulaire, pattern='^retour_formulaire$'))
    app.add_handler(CallbackQueryHandler(edit_champ, pattern='^edit_'))
    app.add_handler(CallbackQueryHandler(set_methode, pattern='^set_methode_'))
    app.add_handler(CallbackQueryHandler(toggle_voyage, pattern='^toggle_voyage_'))
    app.add_handler(CallbackQueryHandler(valider_client, pattern='^valider_client$'))
    
    # Paiement reçu
    app.add_handler(CallbackQueryHandler(paiement_recu, pattern='^menu_paiement_recu$'))
    app.add_handler(CallbackQueryHandler(paiement_client_selectionne, pattern='^paiement_client_'))
    app.add_handler(CallbackQueryHandler(force_montant, pattern='^force_montant_'))
    app.add_handler(CallbackQueryHandler(choisir_methode_paiement, pattern='^paiement_methode_'))
    
    # Voyages
    app.add_handler(CallbackQueryHandler(menu_voyages, pattern='^menu_voyages$'))
    app.add_handler(CallbackQueryHandler(voyage_creer, pattern='^voyage_creer$'))
    app.add_handler(CallbackQueryHandler(voyage_choisir_couleur, pattern='^voyage_couleur_'))
    app.add_handler(CallbackQueryHandler(voyage_detail, pattern='^voyage_detail_'))
    app.add_handler(CallbackQueryHandler(voyage_modifier, pattern='^voyage_modifier_'))
    app.add_handler(CallbackQueryHandler(voyage_supprimer, pattern='^voyage_supprimer_'))
    app.add_handler(CallbackQueryHandler(voyage_delete_confirm, pattern='^voyage_delete_confirm_'))
    
    # Recherche et listes
    app.add_handler(CallbackQueryHandler(rechercher_client, pattern='^menu_rechercher$'))
    app.add_handler(CallbackQueryHandler(liste_clients, pattern='^menu_liste$'))
    app.add_handler(CallbackQueryHandler(prochains_paiements, pattern='^menu_rappels$'))
    app.add_handler(CallbackQueryHandler(statistiques, pattern='^menu_stats$'))
    app.add_handler(CallbackQueryHandler(clients_termines, pattern='^menu_termines$'))
    app.add_handler(CallbackQueryHandler(export, pattern='^menu_export$'))
    
    # Détails client et modifications
    app.add_handler(CallbackQueryHandler(details_client_complet, pattern='^detail_'))
    app.add_handler(CallbackQueryHandler(modifier_client, pattern='^modifier_client_'))
    
    # Paiements
    app.add_handler(CallbackQueryHandler(payer_client, pattern='^payer_'))
    app.add_handler(CallbackQueryHandler(choisir_methode, pattern='^methode_'))
    app.add_handler(CallbackQueryHandler(archiver_client, pattern='^archiver_'))
    app.add_handler(CallbackQueryHandler(reactiver_client, pattern='^reactiver_'))
    
    # Validations et suppressions
    app.add_handler(CallbackQueryHandler(valider_manuel, pattern='^valider_manuel_'))
    app.add_handler(CallbackQueryHandler(supprimer_client, pattern='^supprimer_client_'))
    app.add_handler(CallbackQueryHandler(delete_confirm, pattern='^delete_confirm_'))
    
    # Messages texte (ordre important pour éviter les conflits)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, recevoir_edit))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, recevoir_recherche))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, recevoir_montant_paiement_recu))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, voyage_recevoir_nom))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, voyage_recevoir_date))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, recevoir_montant))
    
    # Planifier les vérifications automatiques à 9h30
    job_queue = app.job_queue
    if job_queue:
        # 👉 REMPLACEZ 123456789 PAR VOTRE ID TELEGRAM
        job_queue.run_daily(check_paiements_imminents, time=time(hour=9, minute=30), chat_id=123456789)
    
    print("✅ Bot démarré !")
    print(f"📱 Allez sur Telegram et recherchez {BOT_USERNAME}")
    print("👉 Tapez /start pour commencer")
    app.run_polling()

if __name__ == '__main__':
    main()