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

async def main():
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

    # Inicia keep-alive em background
    keep_alive_task = asyncio.create_task(start_keep_alive())

    # Configuração do webhook
    webhook_url = os.getenv('WEBHOOK_URL')
    port_str = os.getenv('PORT')
    port = int(port_str) if port_str and port_str.isdigit() else 8443

    if not webhook_url:
        logger.error("WEBHOOK_URL não configurado! Defina a URL pública do seu serviço Render.")
        return

    try:
        logger.info(f"Iniciando bot em modo webhook na porta {port}...")
        await application.run_webhook(
            listen="0.0.0.0",
            port=port,
            webhook_url=webhook_url,
            stop_signals=None
        )
    except KeyboardInterrupt:
        logger.info("Parando o bot...")
    finally:
        stop_keep_alive()
        keep_alive_task.cancel()
        notification_manager.stop_scheduler()
        logger.info("Bot parado com sucesso!")



def run_bot():
    """
    Função para executar o bot (compatível com diferentes ambientes).
    """
    import nest_asyncio
    import asyncio
    import sys

    nest_asyncio.apply()

    try:
        if sys.platform == "win32":
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Se o loop já estiver rodando (como no Render), apenas cria a tarefa
            loop.create_task(main())
        else:
            loop.run_until_complete(main())
    except KeyboardInterrupt:
        logger.info("Bot interrompido pelo usuário")
    except Exception as e:
        logger.error(f"Erro ao executar o bot: {e}")



if __name__ == '__main__':
    run_bot()