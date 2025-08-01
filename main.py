"""
Arquivo principal do Bot de Controle Financeiro
Integra o bot Telegram com o sistema de notificações e keep-alive
"""

import os
import asyncio
import logging
from dotenv import load_dotenv
from bot import FinanceBotManager
from notifications import NotificationManager
from keep_alive import start_keep_alive, stop_keep_alive

# Carrega variáveis de ambiente
load_dotenv()

# Configuração de logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def main():
    """
    Função principal que executa o bot, sistema de notificações e keep-alive.
    """
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    mongodb_uri = os.getenv('MONGODB_URI')

    if not bot_token:
        logger.error("TELEGRAM_BOT_TOKEN não configurado!")
        return

    if not mongodb_uri:
        logger.error("MONGODB_URI não configurado!")
        return

    logger.info("Iniciando Bot de Controle Financeiro...")

    # Inicializa o gerenciador de notificações
    notification_manager = NotificationManager(bot_token, mongodb_uri)
    notification_manager.start_scheduler()

    # Inicializa o bot
    bot_manager = FinanceBotManager()
    application = bot_manager.create_application()

    # Configuração do webhook
    webhook_url = os.getenv('WEBHOOK_URL')
    port_str = os.getenv('PORT')
    try:
        port = int(port_str) if port_str else 8443
    except ValueError:
        logger.warning(f"PORT inválido: '{port_str}', usando 8443 como padrão.")
        port = 8443

    if not webhook_url:
        logger.error("WEBHOOK_URL não configurado! Defina a URL pública do seu serviço Render.")
        return

    try:
        logger.info(f"Iniciando bot em modo webhook na porta {port}...")
        application.run_webhook(
            listen="0.0.0.0",
            port=port,
            webhook_url=webhook_url,
            stop_signals=None
        )
    except KeyboardInterrupt:
        logger.info("Parando o bot...")
    finally:
        notification_manager.stop_scheduler()
        logger.info("Bot parado com sucesso!")

def run_bot():
    """
    Executa o bot de forma compatível com ambientes como Render.
    """
    import nest_asyncio
    nest_asyncio.apply()

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot interrompido pelo usuário")
    except Exception as e:
        logger.error(f"Erro ao executar o bot: {e}")


if __name__ == '__main__':
    run_bot()
