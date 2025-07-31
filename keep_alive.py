"""
Script para manter o bot ativo em plataformas de hospedagem gratuita
que colocam aplicações em modo de suspensão após inatividade.
"""

import os
import asyncio
import aiohttp
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class KeepAlive:
    def __init__(self, url: str = None, interval: int = 300):
        """
        Inicializa o sistema de keep-alive.
        
        Args:
            url: URL para fazer ping (opcional, usa variável de ambiente se não fornecida)
            interval: Intervalo entre pings em segundos (padrão: 5 minutos)
        """
        self.url = url or os.getenv('KEEP_ALIVE_URL')
        self.interval = interval
        self.running = False
    
    async def ping(self):
        """
        Faz um ping HTTP para manter a aplicação ativa.
        """
        if not self.url:
            logger.warning("URL de keep-alive não configurada")
            return
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.url, timeout=10) as response:
                    if response.status == 200:
                        logger.info(f"Keep-alive ping successful: {datetime.now()}")
                    else:
                        logger.warning(f"Keep-alive ping returned status {response.status}")
                        
        except asyncio.TimeoutError:
            logger.warning("Keep-alive ping timeout")
        except Exception as e:
            logger.error(f"Erro no keep-alive ping: {e}")
    
    async def start(self):
        """
        Inicia o sistema de keep-alive.
        """
        if not self.url:
            logger.info("Keep-alive desabilitado (URL não configurada)")
            return
        
        self.running = True
        logger.info(f"Keep-alive iniciado: ping a cada {self.interval} segundos")
        
        while self.running:
            await self.ping()
            await asyncio.sleep(self.interval)
    
    def stop(self):
        """
        Para o sistema de keep-alive.
        """
        self.running = False
        logger.info("Keep-alive parado")

# Instância global para uso em outros módulos
keep_alive = KeepAlive()

async def start_keep_alive():
    """
    Função para iniciar o keep-alive em background.
    """
    await keep_alive.start()

def stop_keep_alive():
    """
    Função para parar o keep-alive.
    """
    keep_alive.stop()

