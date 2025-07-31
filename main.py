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
    # Verifica se as variáveis de ambiente estão configuradas
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
    
    try:
        logger.info("Bot, notificações e keep-alive iniciados com sucesso!")
        logger.info("Pressione Ctrl+C para parar...")
        
        # Executa o bot
        await application.initialize()
        await application.start()
        await application.run_polling()
        
        # Mantém o programa rodando
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Parando o bot...")
        
    finally:
        # Para o keep-alive
        stop_keep_alive()
        keep_alive_task.cancel()
        
        # Para o sistema de notificações
        notification_manager.stop_scheduler()
        
        # Para o bot
        
        
        logger.info("Bot parado com sucesso!")

def run_bot():
    """
    Função para executar o bot (compatível com diferentes ambientes).
    """
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot interrompido pelo usuário")
    except Exception as e:
        logger.error(f"Erro ao executar o bot: {e}")

if __name__ == '__main__':
    run_bot()

