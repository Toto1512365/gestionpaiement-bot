import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from database import Database
from datetime import datetime, time
import pandas as pd
from io import BytesIO
import os

# 🔐 VOTRE TOKEN
TOKEN = "8489899130:AAFAFe3tkKUrixHokYQO_d0Pt3wkicGZX80"

# ✅ VOTRE ID TELEGRAM (récupéré de @userinfobot)
ADMIN_ID = 1099086639

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
    row1 = []
    row1.append(InlineKeyboardButton(
        f"👤 Prénom: {prenom or '?'}",
        callback_data='modif_prenom'
    ))
    row1.append(InlineKeyboardButton(
        f"👤 Nom: {nom or '?'}",
        callback_data='modif_nom'
    ))
    keyboard.append(row1)
    
    # Téléphone et Email
    row2 = []
    row2.append(InlineKeyboardButton(
        f"📞 Tél: {client.get('telephone') or '?'}",
        callback_data='modif_telephone'
    ))
    row2.append(InlineKeyboardButton(
        f"📧 Email: {client.get('email') or '?'}",
        callback_data='modif_email'
    ))
    keyboard.append(row2)
    
    # Description
    keyboard.append([InlineKeyboardButton(
        f"📝 Description: {client.get('description')[:15] or '?'}",
        callback_data='modif_description'
    )])
    
    # Montant dû
    keyboard.append([InlineKeyboardButton(
        f"💰 Montant dû: {client.get('montant_du', 0)}",
        callback_data='modif_montant'
    )])
    
    # Date limite
    keyboard.append([InlineKeyboardButton(
        f"📅 Date limite: {client.get('date_limite') or '?'}",
        callback_data='modif_date'
    )])
    
    # Méthode de paiement
    keyboard.append([InlineKeyboardButton(
        f"💳 Méthode: {client.get('methode_paiement') or '?'}",
        callback_data='modif_methode'
    )])
    
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
    
    # Validation
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
            selected = voyage_id in context.user_data['nouveau_client'].get('voyages', [])
            prefix = "✅ " if selected else ""
            keyboard.append([InlineKeyboardButton(
                f"{prefix}{couleur} {nom} ({date_voyage or '?'})", 
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
        context.user_data['etape'] = f'attente_{champ}'

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
        db.ajouter_paiement(
            client_id=client_id,
            montant=0,
            methode=client.get('methode_paiement'),
            notes="Méthode de paiement prévue"
        )
    
    if client.get('voyages'):
        for voyage_id in client['voyages']:
            db.attribuer_voyage_client(client_id, voyage_id)
    
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
                f"{couleur} {nom} ({date_voyage or '?'})", 
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
        "📅 ÉTAPE 2/3 - Envoyez la *date* du voyage (MM/AAAA)\n"
        "Exemple: `06/2024` pour Juin 2024\n"
        "Ou envoyez 'skip' pour passer",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )
    context.user_data['etape'] = 'voyage_attente_date'

async def voyage_recevoir_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('etape') != 'voyage_attente_date':
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
    
    couleurs = ["🔴", "🟠", "🟡", "🟢", "🔵", "🟣", "🟤", "⚫", "⚪"]
    
    keyboard = []
    
    row1 = []
    for i in range(3):
        row1.append(InlineKeyboardButton(couleurs[i], callback_data=f'voyage_couleur_{couleurs[i]}'))
    keyboard.append(row1)
    
    row2 = []
    for i in range(3, 6):
        row2.append(InlineKeyboardButton(couleurs[i], callback_data=f'voyage_couleur_{couleurs[i]}'))
    keyboard.append(row2)
    
    row3 = []
    for i in range(6, 9):
        row3.append(InlineKeyboardButton(couleurs[i], callback_data=f'voyage_couleur_{couleurs[i]}'))
    keyboard.append(row3)
    
    keyboard.append([InlineKeyboardButton("🔙 RETOUR", callback_data='menu_voyages')])
    
    await update.message.reply_text(
        f"✈️ *CRÉER UN VOYAGE*\n\n"
        f"Nom: *{context.user_data['nouveau_voyage']['nom']}*\n"
        f"Date: *{context.user_data['nouveau_voyage'].get('date', 'Non définie')}*\n\n"
        f"🎨 ÉTAPE 3/3 - Choisissez une couleur :",
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
    
    voyage_id = db.ajouter_voyage(
        nom=voyage_data['nom'],
        date_voyage=voyage_data.get('date', ''),
        couleur=couleur
    )
    
    await query.edit_message_text(
        f"✅ *VOYAGE CRÉÉ !*\n\n"
        f"{couleur} *{voyage_data['nom']}*\n"
        f"📅 Date: {voyage_data.get('date', 'Non définie')}\n"
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
    
    context.user_data.clear()

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
                
                await context.bot.send_message(
                    chat_id=ADMIN_ID,
                    text=message,
                    parse_mode='Markdown'
                )
        except:
            pass

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
    
    # Modifications
    app.add_handler(CallbackQueryHandler(modif_champ, pattern='^modif_'))
    app.add_handler(CallbackQueryHandler(toggle_voyage, pattern='^toggle_voyage_'))
    app.add_handler(CallbackQueryHandler(set_methode, pattern='^set_methode_'))
    app.add_handler(CallbackQueryHandler(valider_client, pattern='^valider_client$'))
    app.add_handler(CallbackQueryHandler(retour_formulaire, pattern='^retour_formulaire$'))
    
    # Voyages
    app.add_handler(CallbackQueryHandler(menu_voyages, pattern='^menu_voyages$'))
    app.add_handler(CallbackQueryHandler(voyage_creer, pattern='^voyage_creer$'))
    app.add_handler(CallbackQueryHandler(voyage_choisir_couleur, pattern='^voyage_couleur_'))
    
    # Recherche et listes (simplifiés pour l'instant)
    app.add_handler(CallbackQueryHandler(menu_principal, pattern='^menu_rechercher$'))
    app.add_handler(CallbackQueryHandler(menu_principal, pattern='^menu_liste$'))
    app.add_handler(CallbackQueryHandler(menu_principal, pattern='^menu_rappels$'))
    app.add_handler(CallbackQueryHandler(menu_principal, pattern='^menu_stats$'))
    app.add_handler(CallbackQueryHandler(menu_principal, pattern='^menu_termines$'))
    app.add_handler(CallbackQueryHandler(menu_principal, pattern='^menu_export$'))
    app.add_handler(CallbackQueryHandler(menu_principal, pattern='^menu_paiement_recu$'))
    
    # Messages texte
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, recevoir_prenom))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, recevoir_nom))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, voyage_recevoir_nom))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, voyage_recevoir_date))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, recevoir_modification))
    
    # Planifier les vérifications automatiques à 9h30
    job_queue = app.job_queue
    if job_queue:
        job_queue.run_daily(check_paiements_imminents, time=time(hour=9, minute=30), chat_id=ADMIN_ID)
    
    print("✅ Bot démarré !")
    print(f"📱 Allez sur Telegram et recherchez {BOT_USERNAME}")
    print("👉 Tapez /start pour commencer")
    app.run_polling()

if __name__ == '__main__':
    main()
