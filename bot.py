"""
Bot Telegram para Controle Financeiro Pessoal
"""

import os
import logging
import asyncio
from datetime import datetime, date
from typing import Dict, Any
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, 
    CallbackQueryHandler, ConversationHandler, filters, ContextTypes
)
from dotenv import load_dotenv
from database import DatabaseManager

# Carrega variáveis de ambiente
load_dotenv()

# Configuração de logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Estados da conversa
(RECEITA_CATEGORIA, RECEITA_DESCRICAO, RECEITA_VALOR, RECEITA_DATA,
 DESPESA_CATEGORIA, DESPESA_DESCRICAO, DESPESA_VALOR, DESPESA_VENCIMENTO,
 DESPESA_PARCELAMENTO, DESPESA_PARCELAS, DESPESA_VALOR_PARCELA,
 PAGAR_DATA) = range(12)

class FinanceBotManager:
    def __init__(self):
        self.db = DatabaseManager(os.getenv('MONGODB_URI'))
        self.user_data = {}
    

    async def error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        logger.error("Exception while handling an update:", exc_info=context.error)
        if update and isinstance(update, Update) and update.message:
            await update.message.reply_text("❌ Ocorreu um erro inesperado. Tente novamente mais tarde.")
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /start - Inicia a interação com o bot."""
        user = update.effective_user
        chat_id = update.effective_chat.id
        
        # Registra o usuário no banco de dados
        self.db.create_user(user.id, user.username, chat_id)
        
        welcome_message = f"""
🏦 *Bem-vindo ao Bot de Controle Financeiro!*

Olá {user.first_name}! Eu sou seu assistente pessoal para controle financeiro.

*Comandos disponíveis:*
• /receita - Registrar uma nova receita
• /despesa - Registrar uma nova despesa
• /listar - Ver suas transações
• /pagar - Marcar despesa como paga
• /categorias - Ver suas categorias
• /relatorio - Gerar relatório mensal
• /help - Ajuda e instruções

Para começar, use /receita para registrar uma receita ou /despesa para registrar uma despesa.
        """
        
        await update.message.reply_text(welcome_message, parse_mode='Markdown')
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /help - Exibe ajuda."""
        help_text = """
🆘 *Ajuda - Bot de Controle Financeiro*

*Comandos principais:*

📈 */receita* - Registra uma nova receita
   Exemplo: salário, freelance, vendas

💸 */despesa* - Registra uma nova despesa
   Exemplo: aluguel, alimentação, transporte
   Suporta parcelamento automático

📋 */listar* - Lista suas transações
   Opções: receitas, despesas, abertas, pagas

💰 */pagar <ID>* - Marca despesa como paga
   Exemplo: /pagar 507f1f77bcf86cd799439011

🏷️ */categorias* - Mostra suas categorias

📊 */relatorio* - Relatório mensal atual

*Funcionalidades:*
• ✅ Controle de receitas e despesas
• 📅 Vencimentos e lembretes automáticos
• 💳 Suporte a parcelamentos
• 📊 Relatórios mensais
• 🏷️ Categorização automática

*Dicas:*
• Use categorias consistentes para melhor organização
• Configure vencimentos para receber lembretes
• Marque como "pago" para manter o controle atualizado
        """
        
        await update.message.reply_text(help_text, parse_mode='Markdown')
    
    async def receita_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Inicia o fluxo de registro de receita."""
        await update.message.reply_text(
            "💰 *Registrar Nova Receita*\n\n"
            "Qual a categoria desta receita?\n"
            "Exemplos: Salário, Freelance, Vendas, Investimentos",
            parse_mode='Markdown'
        )
        return RECEITA_CATEGORIA
    
    async def receita_categoria(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Recebe a categoria da receita."""
        context.user_data['receita_categoria'] = update.message.text
        await update.message.reply_text(
            f"Categoria: *{update.message.text}*\n\n"
            "Agora, digite uma descrição para esta receita:",
            parse_mode='Markdown'
        )
        return RECEITA_DESCRICAO
    
    async def receita_descricao(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Recebe a descrição da receita."""
        context.user_data['receita_descricao'] = update.message.text
        await update.message.reply_text(
            f"Descrição: *{update.message.text}*\n\n"
            "Qual o valor desta receita? (apenas números)",
            parse_mode='Markdown'
        )
        return RECEITA_VALOR
    
    async def receita_valor(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Recebe o valor da receita."""
        try:
            valor = float(update.message.text.replace(',', '.'))
            context.user_data['receita_valor'] = valor
            
            await update.message.reply_text(
                f"Valor: *R$ {valor:.2f}*\n\n"
                "Qual a data de recebimento? (DD/MM/AAAA)\n"
                "Ou digite 'hoje' para a data atual:",
                parse_mode='Markdown'
            )
            return RECEITA_DATA
            
        except ValueError:
            await update.message.reply_text(
                "❌ Valor inválido! Digite apenas números.\n"
                "Exemplo: 1500.50 ou 1500,50"
            )
            return RECEITA_VALOR
    
    async def receita_data(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Recebe a data da receita e finaliza o registro."""
        try:
            data_texto = update.message.text.lower()
            
            if data_texto == 'hoje':
                data_receita = date.today()
            else:
                data_receita = datetime.strptime(data_texto, '%d/%m/%Y').date()
            
            # Registra a receita no banco
            user_id = update.effective_user.id
            transaction_id = self.db.create_transaction(
                user_id=user_id,
                transaction_type="receita",
                category=context.user_data['receita_categoria'],
                description=context.user_data['receita_descricao'],
                value=context.user_data['receita_valor'],
                due_date=data_receita
            )
            
            if transaction_id:
                await update.message.reply_text(
                    "✅ *Receita registrada com sucesso!*\n\n"
                    f"📈 Categoria: {context.user_data['receita_categoria']}\n"
                    f"📝 Descrição: {context.user_data['receita_descricao']}\n"
                    f"💰 Valor: R$ {context.user_data['receita_valor']:.2f}\n"
                    f"📅 Data: {data_receita.strftime('%d/%m/%Y')}\n"
                    f"🆔 ID: `{transaction_id}`",
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text(
                    "❌ Erro ao registrar receita. Tente novamente."
                )
            
            # Limpa os dados temporários
            context.user_data.clear()
            return ConversationHandler.END
            
        except ValueError:
            await update.message.reply_text(
                "❌ Data inválida! Use o formato DD/MM/AAAA\n"
                "Exemplo: 25/12/2024 ou digite 'hoje'"
            )
            return RECEITA_DATA
    
    async def despesa_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Inicia o fluxo de registro de despesa."""
        await update.message.reply_text(
            "💸 *Registrar Nova Despesa*\n\n"
            "Qual a categoria desta despesa?\n"
            "Exemplos: Alimentação, Transporte, Aluguel, Lazer",
            parse_mode='Markdown'
        )
        return DESPESA_CATEGORIA
    
    async def despesa_categoria(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Recebe a categoria da despesa."""
        context.user_data['despesa_categoria'] = update.message.text
        await update.message.reply_text(
            f"Categoria: *{update.message.text}*\n\n"
            "Agora, digite uma descrição para esta despesa:",
            parse_mode='Markdown'
        )
        return DESPESA_DESCRICAO
    
    async def despesa_descricao(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Recebe a descrição da despesa."""
        context.user_data['despesa_descricao'] = update.message.text
        await update.message.reply_text(
            f"Descrição: *{update.message.text}*\n\n"
            "Qual o valor desta despesa? (apenas números)",
            parse_mode='Markdown'
        )
        return DESPESA_VALOR
    
    async def despesa_valor(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Recebe o valor da despesa."""
        try:
            valor = float(update.message.text.replace(',', '.'))
            context.user_data['despesa_valor'] = valor
            
            await update.message.reply_text(
                f"Valor: *R$ {valor:.2f}*\n\n"
                "Qual a data de vencimento? (DD/MM/AAAA)\n"
                "Ou digite 'hoje' para a data atual:",
                parse_mode='Markdown'
            )
            return DESPESA_VENCIMENTO
            
        except ValueError:
            await update.message.reply_text(
                "❌ Valor inválido! Digite apenas números.\n"
                "Exemplo: 150.50 ou 150,50"
            )
            return DESPESA_VALOR
    
    async def despesa_vencimento(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Recebe a data de vencimento da despesa."""
        try:
            data_texto = update.message.text.lower()
            
            if data_texto == 'hoje':
                data_vencimento = date.today()
            else:
                data_vencimento = datetime.strptime(data_texto, '%d/%m/%Y').date()
            
            context.user_data['despesa_vencimento'] = data_vencimento
            
            # Pergunta sobre parcelamento
            keyboard = [
                [InlineKeyboardButton("Sim", callback_data="parcelado_sim")],
                [InlineKeyboardButton("Não", callback_data="parcelado_nao")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                f"Vencimento: *{data_vencimento.strftime('%d/%m/%Y')}*\n\n"
                "Esta despesa é parcelada?",
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
            return DESPESA_PARCELAMENTO
            
        except ValueError:
            await update.message.reply_text(
                "❌ Data inválida! Use o formato DD/MM/AAAA\n"
                "Exemplo: 25/12/2024 ou digite 'hoje'"
            )
            return DESPESA_VENCIMENTO
    
    async def despesa_parcelamento(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Trata a resposta sobre parcelamento."""
        query = update.callback_query
        await query.answer()
        
        if query.data == "parcelado_sim":
            await query.edit_message_text(
                "💳 *Despesa Parcelada*\n\n"
                "Quantas parcelas? (número inteiro)",
                parse_mode='Markdown'
            )
            return DESPESA_PARCELAS
        else:
            # Finaliza o registro sem parcelamento
            return await self.finalizar_despesa(update, context, False)
    
    async def despesa_parcelas(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Recebe o número de parcelas."""
        texto = update.message.text.strip()
        if not texto:
            await update.message.reply_text(
                "❌ Número de parcelas não pode ser vazio! Digite um número inteiro positivo.\n"
                "Exemplo: 12"
            )
            return DESPESA_PARCELAS
        try:
            parcelas = int(texto)
            if parcelas <= 0:
                raise ValueError("Número de parcelas deve ser positivo")
            context.user_data['despesa_parcelas'] = parcelas
            await update.message.reply_text(
                f"Parcelas: *{parcelas}x*\n\n"
                "Qual o valor de cada parcela? (apenas números)",
                parse_mode='Markdown'
            )
            return DESPESA_VALOR_PARCELA
        except ValueError:
            await update.message.reply_text(
                "❌ Número de parcelas inválido! Digite um número inteiro positivo.\n"
                "Exemplo: 12"
            )
            return DESPESA_PARCELAS
    
    async def despesa_valor_parcela(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Recebe o valor da parcela e finaliza o registro."""
        try:
            valor_parcela = float(update.message.text.replace(',', '.'))
            context.user_data['despesa_valor_parcela'] = valor_parcela
            
            return await self.finalizar_despesa(update, context, True)
            
        except ValueError:
            await update.message.reply_text(
                "❌ Valor inválido! Digite apenas números.\n"
                "Exemplo: 150.50 ou 150,50"
            )
            return DESPESA_VALOR_PARCELA
    
    async def finalizar_despesa(self, update: Update, context: ContextTypes.DEFAULT_TYPE, parcelado: bool):
        """Finaliza o registro da despesa."""
        user_id = update.effective_user.id
        
        installment_details = None
        if parcelado:
            installment_details = {
                "total_installments": context.user_data['despesa_parcelas'],
                "current_installment": 1,
                "installment_value": context.user_data['despesa_valor_parcela']
            }
        
        transaction_id = self.db.create_transaction(
            user_id=user_id,
            transaction_type="despesa",
            category=context.user_data['despesa_categoria'],
            description=context.user_data['despesa_descricao'],
            value=context.user_data['despesa_valor'],
            due_date=context.user_data['despesa_vencimento'],
            is_installment=parcelado,
            installment_details=installment_details
        )
        
        if transaction_id:
            mensagem = (
                "✅ *Despesa registrada com sucesso!*\n\n"
                f"💸 Categoria: {context.user_data['despesa_categoria']}\n"
                f"📝 Descrição: {context.user_data['despesa_descricao']}\n"
                f"💰 Valor: R$ {context.user_data['despesa_valor']:.2f}\n"
                f"📅 Vencimento: {context.user_data['despesa_vencimento'].strftime('%d/%m/%Y')}\n"
            )
            
            if parcelado:
                mensagem += (
                    f"💳 Parcelado: {context.user_data['despesa_parcelas']}x de "
                    f"R$ {context.user_data['despesa_valor_parcela']:.2f}\n"
                )
            
            mensagem += f"🆔 ID: `{transaction_id}`"
            
            await update.message.reply_text(mensagem, parse_mode='Markdown')
        else:
            await update.message.reply_text(
                "❌ Erro ao registrar despesa. Tente novamente."
            )
        
        # Limpa os dados temporários
        context.user_data.clear()
        return ConversationHandler.END
    
    async def listar_transacoes(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Lista as transações do usuário."""
        user_id = update.effective_user.id
        
        # Busca as últimas 10 transações
        transacoes = self.db.get_transactions(user_id)[:10]
        
        if not transacoes:
            await update.message.reply_text(
                "📋 Você ainda não possui transações registradas.\n"
                "Use /receita ou /despesa para começar!"
            )
            return
        
        mensagem = "📋 *Suas Últimas Transações:*\n\n"
        
        for t in transacoes:
            emoji = "📈" if t["type"] == "receita" else "💸"
            status_emoji = "✅" if t["status"] == "pago" else "⏳"
            
            mensagem += (
                f"{emoji} *{t['category']}* {status_emoji}\n"
                f"📝 {t['description']}\n"
                f"💰 R$ {t['value']:.2f}\n"
                f"🆔 `{str(t['_id'])}`\n"
            )
            
            if t.get('due_date'):
                mensagem += f"📅 Venc: {t['due_date'].strftime('%d/%m/%Y')}\n"
            
            mensagem += "\n"
        
        await update.message.reply_text(mensagem, parse_mode='Markdown')
    
    async def pagar_despesa(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Inicia o processo de marcar despesa como paga."""
        args = context.args
        
        if not args:
            await update.message.reply_text(
                "💰 Para marcar uma despesa como paga, use:\n"
                "/pagar <ID_da_despesa>\n\n"
                "Exemplo: /pagar 507f1f77bcf86cd799439011\n\n"
                "Use /listar para ver os IDs das suas despesas."
            )
            return ConversationHandler.END
        
        transaction_id = args[0]
        
        # Verifica se a transação existe e pertence ao usuário
        user_id = update.effective_user.id
        transacao = self.db.get_transaction_by_id(transaction_id, user_id)
        
        if not transacao:
            await update.message.reply_text(
                "❌ Transação não encontrada ou não pertence a você.\n"
                "Verifique o ID e tente novamente."
            )
            return ConversationHandler.END
        
        if transacao['type'] != 'despesa':
            await update.message.reply_text(
                "❌ Esta transação não é uma despesa.\n"
                "Apenas despesas podem ser marcadas como pagas."
            )
            return ConversationHandler.END
        
        if transacao['status'] == 'pago':
            await update.message.reply_text(
                "✅ Esta despesa já está marcada como paga!"
            )
            return ConversationHandler.END
        
        # Armazena o ID da transação para uso posterior
        context.user_data['transaction_id'] = transaction_id
        context.user_data['transaction'] = transacao
        
        await update.message.reply_text(
            f"💰 *Marcar como Pago*\n\n"
            f"💸 {transacao['category']}\n"
            f"📝 {transacao['description']}\n"
            f"💰 R$ {transacao['value']:.2f}\n\n"
            "Qual a data do pagamento? (DD/MM/AAAA)\n"
            "Ou digite 'hoje' para a data atual:",
            parse_mode='Markdown'
        )
        return PAGAR_DATA
    
    async def pagar_data(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Recebe a data de pagamento e finaliza o processo."""
        try:
            data_texto = update.message.text.lower()
            
            if data_texto == 'hoje':
                data_pagamento = date.today()
            else:
                data_pagamento = datetime.strptime(data_texto, '%d/%m/%Y').date()
            
            # Marca a despesa como paga
            transaction_id = context.user_data['transaction_id']
            user_id = update.effective_user.id
            
            sucesso = self.db.mark_as_paid(transaction_id, user_id, data_pagamento)
            
            if sucesso:
                transacao = context.user_data['transaction']
                await update.message.reply_text(
                    "✅ *Despesa marcada como paga!*\n\n"
                    f"💸 {transacao['category']}\n"
                    f"📝 {transacao['description']}\n"
                    f"💰 R$ {transacao['value']:.2f}\n"
                    f"📅 Pago em: {data_pagamento.strftime('%d/%m/%Y')}",
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text(
                    "❌ Erro ao marcar despesa como paga. Tente novamente."
                )
            
            # Limpa os dados temporários
            context.user_data.clear()
            return ConversationHandler.END
            
        except ValueError:
            await update.message.reply_text(
                "❌ Data inválida! Use o formato DD/MM/AAAA\n"
                "Exemplo: 25/12/2024 ou digite 'hoje'"
            )
            return PAGAR_DATA
    
    async def categorias(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Lista as categorias do usuário."""
        user_id = update.effective_user.id
        categorias = self.db.get_user_categories(user_id)
        
        mensagem = "🏷️ *Suas Categorias:*\n\n"
        
        if categorias['receitas']:
            mensagem += "📈 *Receitas:*\n"
            for cat in categorias['receitas']:
                mensagem += f"• {cat}\n"
            mensagem += "\n"
        
        if categorias['despesas']:
            mensagem += "💸 *Despesas:*\n"
            for cat in categorias['despesas']:
                mensagem += f"• {cat}\n"
        
        if not categorias['receitas'] and not categorias['despesas']:
            mensagem = "🏷️ Você ainda não possui categorias.\nRegistre algumas transações primeiro!"
        
        await update.message.reply_text(mensagem, parse_mode='Markdown')
    
    async def relatorio(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Gera relatório mensal."""
        user_id = update.effective_user.id
        hoje = date.today()
        
        resumo = self.db.get_monthly_summary(user_id, hoje.year, hoje.month)
        
        mensagem = (
            f"📊 *Relatório - {hoje.strftime('%B/%Y')}*\n\n"
            f"📈 Receitas: R$ {resumo['receitas']:.2f}\n"
            f"💸 Despesas: R$ {resumo['despesas']:.2f}\n"
            f"💰 Saldo: R$ {resumo['saldo']:.2f}\n"
            f"📋 Total de transações: {resumo['total_transacoes']}\n\n"
        )
        
        if resumo['saldo'] > 0:
            mensagem += "✅ Parabéns! Você teve um saldo positivo este mês!"
        elif resumo['saldo'] < 0:
            mensagem += "⚠️ Atenção! Suas despesas superaram as receitas."
        else:
            mensagem += "⚖️ Suas receitas e despesas estão equilibradas."
        
        await update.message.reply_text(mensagem, parse_mode='Markdown')
    
    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Cancela a operação atual."""
        context.user_data.clear()
        await update.message.reply_text(
            "❌ Operação cancelada. Use /help para ver os comandos disponíveis."
        )
        return ConversationHandler.END
    
    def create_application(self):
        """Cria e configura a aplicação do bot."""
        application = Application.builder().token(os.getenv('TELEGRAM_BOT_TOKEN')).build()
        
        # Handlers de comando
        application.add_handler(CommandHandler("start", self.start_command))
        application.add_handler(CommandHandler("help", self.help_command))
        application.add_handler(CommandHandler("listar", self.listar_transacoes))
        application.add_handler(CommandHandler("categorias", self.categorias))
        application.add_handler(CommandHandler("relatorio", self.relatorio))
        
        # Conversation Handler para receitas
        receita_handler = ConversationHandler(
            entry_points=[CommandHandler("receita", self.receita_start)],
            states={
                RECEITA_CATEGORIA: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.receita_categoria)],
                RECEITA_DESCRICAO: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.receita_descricao)],
                RECEITA_VALOR: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.receita_valor)],
                RECEITA_DATA: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.receita_data)],
            },
            fallbacks=[CommandHandler("cancel", self.cancel)]
        )
        
        # Conversation Handler para despesas
        despesa_handler = ConversationHandler(
            entry_points=[CommandHandler("despesa", self.despesa_start)],
            states={
                DESPESA_CATEGORIA: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.despesa_categoria)],
                DESPESA_DESCRICAO: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.despesa_descricao)],
                DESPESA_VALOR: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.despesa_valor)],
                DESPESA_VENCIMENTO: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.despesa_vencimento)],
                DESPESA_PARCELAMENTO: [CallbackQueryHandler(self.despesa_parcelamento)],
                DESPESA_PARCELAS: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.despesa_parcelas)],
                DESPESA_VALOR_PARCELA: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.despesa_valor_parcela)],
            },
            fallbacks=[CommandHandler("cancel", self.cancel)]
        )
        
        # Conversation Handler para pagamentos
        pagar_handler = ConversationHandler(
            entry_points=[CommandHandler("pagar", self.pagar_despesa)],
            states={
                PAGAR_DATA: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.pagar_data)],
            },
            fallbacks=[CommandHandler("cancel", self.cancel)]
        )
        
        application.add_handler(receita_handler)
        application.add_handler(despesa_handler)
        application.add_handler(pagar_handler)
        
    application.add_error_handler(self.error_handler)
        return application

