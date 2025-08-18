import os
import logging
from telegram.ext import Updater, CommandHandler

# Configuración de logging (para debug en Render)
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Función para iniciar el bot
def start(update, context):
    update.message.reply_text('¡Bot funcionando correctamente en Render! ✅')

def main():
    # Cargar token y chat ID desde variables de entorno
    TOKEN = os.getenv('TELEGRAM_TOKEN')
    if not TOKEN:
        raise ValueError("Error: No se encontró la variable TELEGRAM_TOKEN en el entorno")

    # Inicializar el bot
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    # Comandos
    dp.add_handler(CommandHandler('start', start))

    # Iniciar el bot
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
