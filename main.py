import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import os

# Configuration
TOKEN = os.environ.get('TOKEN', "8489899130:AAFAFe3tkKUrixHokYQO_d0Pt3wkicGZX80")
logging.basicConfig(level=logging.INFO)

# Dictionnaire temporaire pour stocker les clients (simulé)
clients = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Commande /start"""
    await update.message.reply_text(
        "👋 Bienvenue sur le bot de gestion !\n\n"
        "Commandes disponibles:\n"
        "/nouveau - Créer un nouveau client"
    )

async def nouveau(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Commence la création d'un client"""
    user_id = update.effective_user.id
    clients[user_id] = {'etape': 'prenom'}
    
    await update.message.reply_text(
        "👤 ÉTAPE 1/2 - Envoyez le *prénom* du client :",
        parse_mode='Markdown'
    )

async def recevoir_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reçoit les messages des utilisateurs"""
    user_id = update.effective_user.id
    texte = update.message.text
    
    # Vérifier si l'utilisateur est en train de créer un client
    if user_id not in clients:
        await update.message.reply_text("Utilisez /nouveau pour créer un client")
        return
    
    etape = clients[user_id].get('etape')
    
    if etape == 'prenom':
        # Sauvegarder le prénom
        clients[user_id]['prenom'] = texte
        clients[user_id]['etape'] = 'nom'
        await update.message.reply_text(
            f"✅ Prénom enregistré : {texte}\n\n"
            "ÉTAPE 2/2 - Envoyez le *nom* du client :",
            parse_mode='Markdown'
        )
    
    elif etape == 'nom':
        # Sauvegarder le nom et terminer
        prenom = clients[user_id].get('prenom', '')
        nom = texte
        nom_complet = f"{prenom} {nom}".strip()
        
        # Simuler la sauvegarde en base
        clients[user_id]['nom'] = nom
        clients[user_id]['etape'] = 'termine'
        
        await update.message.reply_text(
            f"✅ Client *{nom_complet}* créé avec succès !\n\n"
            "Utilisez /nouveau pour créer un autre client",
            parse_mode='Markdown'
        )

def main():
    print("🚀 Démarrage du bot...")
    app = Application.builder().token(TOKEN).build()
    
    # Commandes
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("nouveau", nouveau))
    
    # Messages texte
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, recevoir_message))
    
    print("✅ Bot démarré !")
    app.run_polling()

if __name__ == '__main__':
    main()
