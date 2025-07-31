"""
Sistema de Notificações para o Bot de Controle Financeiro
"""

import os
import asyncio
import logging
from datetime import datetime, date, timedelta
from typing import List, Dict
from telegram import Bot
from telegram.error import TelegramError
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from database import DatabaseManager

logger = logging.getLogger(__name__)

class NotificationManager:
    def __init__(self, bot_token: str, mongodb_uri: str):
        """
        Inicializa o gerenciador de notificações.
        
        Args:
            bot_token: Token do bot Telegram
            mongodb_uri: URI de conexão com MongoDB
        """
        self.bot = Bot(token=bot_token)
        self.db = DatabaseManager(mongodb_uri)
        self.scheduler = AsyncIOScheduler()
        
    async def send_notification(self, chat_id: int, message: str):
        """
        Envia uma notificação para um usuário.
        
        Args:
            chat_id: ID do chat do usuário
            message: Mensagem a ser enviada
        """
        try:
            await self.bot.send_message(
                chat_id=chat_id,
                text=message,
                parse_mode='Markdown'
            )
            logger.info(f"Notificação enviada para chat_id: {chat_id}")
            
        except TelegramError as e:
            logger.error(f"Erro ao enviar notificação para {chat_id}: {e}")
    
    async def check_due_transactions(self):
        """
        Verifica transações com vencimento próximo e envia notificações.
        """
        logger.info("Verificando transações com vencimento próximo...")
        
        try:
            # Busca transações com vencimento em 3 dias
            due_transactions = self.db.get_due_transactions(days_ahead=3)
            
            today = date.today()
            
            for transaction in due_transactions:
                user_id = transaction['user_id']
                user = self.db.get_user(user_id)
                
                if not user or not user.get('chat_id'):
                    continue
                
                chat_id = user['chat_id']
                due_date = transaction['due_date']
                days_until_due = (due_date - today).days
                
                # Determina o tipo de notificação
                if days_until_due < 0:
                    # Vencimento atrasado
                    emoji = "🚨"
                    status = f"VENCIDA há {abs(days_until_due)} dia(s)"
                    urgency = "URGENTE"
                elif days_until_due == 0:
                    # Vence hoje
                    emoji = "⚠️"
                    status = "VENCE HOJE"
                    urgency = "ATENÇÃO"
                elif days_until_due <= 1:
                    # Vence amanhã
                    emoji = "📅"
                    status = "vence AMANHÃ"
                    urgency = "LEMBRETE"
                else:
                    # Vence em alguns dias
                    emoji = "📋"
                    status = f"vence em {days_until_due} dias"
                    urgency = "LEMBRETE"
                
                # Monta a mensagem de notificação
                message = (
                    f"{emoji} *{urgency} - Despesa {status}*\n\n"
                    f"💸 *{transaction['category']}*\n"
                    f"📝 {transaction['description']}\n"
                    f"💰 Valor: R$ {transaction['value']:.2f}\n"
                    f"📅 Vencimento: {due_date.strftime('%d/%m/%Y')}\n"
                    f"🆔 ID: `{str(transaction['_id'])}`\n\n"
                )
                
                if transaction.get('is_installment') and transaction.get('installment_details'):
                    details = transaction['installment_details']
                    message += (
                        f"💳 Parcela {details['current_installment']}/{details['total_installments']} "
                        f"(R$ {details['installment_value']:.2f})\n\n"
                    )
                
                if days_until_due < 0:
                    message += "⚡ *Ação necessária:* Marque como paga usando /pagar ou atualize o vencimento."
                else:
                    message += "💡 *Dica:* Use /pagar para marcar como paga quando efetuar o pagamento."
                
                await self.send_notification(chat_id, message)
                
                # Pequena pausa entre notificações para evitar spam
                await asyncio.sleep(0.5)
        
        except Exception as e:
            logger.error(f"Erro ao verificar transações com vencimento: {e}")
    
    async def send_daily_summary(self):
        """
        Envia resumo diário para usuários que possuem transações.
        """
        logger.info("Enviando resumos diários...")
        
        try:
            # Busca todos os usuários que têm transações
            users_with_transactions = self.db.transactions.distinct("user_id")
            
            for user_id in users_with_transactions:
                user = self.db.get_user(user_id)
                if not user or not user.get('chat_id'):
                    continue
                
                chat_id = user['chat_id']
                
                # Busca transações abertas do usuário
                open_transactions = self.db.get_transactions(
                    user_id, status="aberto"
                )
                
                if not open_transactions:
                    continue
                
                # Conta transações por tipo
                receitas_abertas = [t for t in open_transactions if t['type'] == 'receita']
                despesas_abertas = [t for t in open_transactions if t['type'] == 'despesa']
                
                # Calcula valores
                valor_receitas = sum(t['value'] for t in receitas_abertas)
                valor_despesas = sum(t['value'] for t in despesas_abertas)
                
                # Busca despesas com vencimento hoje
                today = date.today()
                vencendo_hoje = [
                    t for t in despesas_abertas 
                    if t.get('due_date') == today
                ]
                
                # Monta mensagem do resumo
                message = (
                    f"🌅 *Resumo Diário - {today.strftime('%d/%m/%Y')}*\n\n"
                    f"📊 *Transações Abertas:*\n"
                    f"📈 Receitas: {len(receitas_abertas)} (R$ {valor_receitas:.2f})\n"
                    f"💸 Despesas: {len(despesas_abertas)} (R$ {valor_despesas:.2f})\n\n"
                )
                
                if vencendo_hoje:
                    message += (
                        f"⚠️ *{len(vencendo_hoje)} despesa(s) vencem hoje:*\n"
                    )
                    for t in vencendo_hoje[:3]:  # Mostra até 3 despesas
                        message += f"• {t['category']}: R$ {t['value']:.2f}\n"
                    
                    if len(vencendo_hoje) > 3:
                        message += f"• ... e mais {len(vencendo_hoje) - 3}\n"
                    
                    message += "\n"
                
                message += (
                    "💡 *Dicas:*\n"
                    "• Use /listar para ver todas as transações\n"
                    "• Use /pagar para marcar despesas como pagas\n"
                    "• Use /relatorio para ver o resumo mensal"
                )
                
                await self.send_notification(chat_id, message)
                await asyncio.sleep(1)  # Pausa entre usuários
        
        except Exception as e:
            logger.error(f"Erro ao enviar resumos diários: {e}")
    
    async def send_weekly_report(self):
        """
        Envia relatório semanal para usuários ativos.
        """
        logger.info("Enviando relatórios semanais...")
        
        try:
            # Busca usuários que tiveram atividade na última semana
            week_ago = datetime.utcnow() - timedelta(days=7)
            
            recent_users = self.db.transactions.distinct(
                "user_id",
                {"created_at": {"$gte": week_ago}}
            )
            
            for user_id in recent_users:
                user = self.db.get_user(user_id)
                if not user or not user.get('chat_id'):
                    continue
                
                chat_id = user['chat_id']
                
                # Busca transações da semana
                weekly_transactions = self.db.transactions.find({
                    "user_id": user_id,
                    "created_at": {"$gte": week_ago}
                })
                
                weekly_transactions = list(weekly_transactions)
                
                if not weekly_transactions:
                    continue
                
                # Calcula estatísticas da semana
                receitas = [t for t in weekly_transactions if t['type'] == 'receita']
                despesas = [t for t in weekly_transactions if t['type'] == 'despesa']
                
                valor_receitas = sum(t['value'] for t in receitas)
                valor_despesas = sum(t['value'] for t in despesas)
                saldo_semanal = valor_receitas - valor_despesas
                
                # Categoria mais usada
                categorias = {}
                for t in weekly_transactions:
                    cat = t['category']
                    categorias[cat] = categorias.get(cat, 0) + 1
                
                categoria_top = max(categorias.items(), key=lambda x: x[1]) if categorias else None
                
                # Monta relatório
                today = date.today()
                week_start = today - timedelta(days=7)
                
                message = (
                    f"📊 *Relatório Semanal*\n"
                    f"📅 {week_start.strftime('%d/%m')} - {today.strftime('%d/%m/%Y')}\n\n"
                    f"📈 Receitas: R$ {valor_receitas:.2f} ({len(receitas)})\n"
                    f"💸 Despesas: R$ {valor_despesas:.2f} ({len(despesas)})\n"
                    f"💰 Saldo: R$ {saldo_semanal:.2f}\n"
                    f"📋 Total: {len(weekly_transactions)} transações\n\n"
                )
                
                if categoria_top:
                    message += f"🏆 Categoria mais usada: *{categoria_top[0]}* ({categoria_top[1]}x)\n\n"
                
                if saldo_semanal > 0:
                    message += "✅ Parabéns! Saldo positivo na semana!"
                elif saldo_semanal < 0:
                    message += "⚠️ Atenção! Despesas superaram receitas."
                else:
                    message += "⚖️ Receitas e despesas equilibradas."
                
                await self.send_notification(chat_id, message)
                await asyncio.sleep(1)
        
        except Exception as e:
            logger.error(f"Erro ao enviar relatórios semanais: {e}")
    
    def start_scheduler(self):
        """
        Inicia o agendador de notificações.
        """
        # Verifica vencimentos todos os dias às 9:00
        self.scheduler.add_job(
            self.check_due_transactions,
            CronTrigger(hour=9, minute=0),
            id='check_due_transactions',
            replace_existing=True
        )
        
        # Envia resumo diário às 8:00
        self.scheduler.add_job(
            self.send_daily_summary,
            CronTrigger(hour=8, minute=0),
            id='daily_summary',
            replace_existing=True
        )
        
        # Envia relatório semanal às segundas-feiras às 10:00
        self.scheduler.add_job(
            self.send_weekly_report,
            CronTrigger(day_of_week='mon', hour=10, minute=0),
            id='weekly_report',
            replace_existing=True
        )
        
        # Verifica vencimentos também às 18:00 (segundo lembrete)
        self.scheduler.add_job(
            self.check_due_transactions,
            CronTrigger(hour=18, minute=0),
            id='check_due_transactions_evening',
            replace_existing=True
        )
        
        self.scheduler.start()
        logger.info("Agendador de notificações iniciado!")
    
    def stop_scheduler(self):
        """
        Para o agendador de notificações.
        """
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("Agendador de notificações parado!")

async def main():
    """
    Função principal para testar o sistema de notificações.
    """
    from dotenv import load_dotenv
    load_dotenv()
    
    notification_manager = NotificationManager(
        bot_token=os.getenv('TELEGRAM_BOT_TOKEN'),
        mongodb_uri=os.getenv('MONGODB_URI')
    )
    
    # Inicia o agendador
    notification_manager.start_scheduler()
    
    try:
        # Mantém o programa rodando
        while True:
            await asyncio.sleep(60)
    except KeyboardInterrupt:
        logger.info("Parando sistema de notificações...")
        notification_manager.stop_scheduler()

if __name__ == '__main__':
    asyncio.run(main())

