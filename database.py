"""
Módulo de conexão e operações com o banco de dados MongoDB.
"""

import os
from datetime import datetime, date
from typing import List, Dict, Optional
from pymongo import MongoClient
from bson import ObjectId
import logging

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self, mongodb_uri: str):
        """
        Inicializa a conexão com o MongoDB.
        
        Args:
            mongodb_uri: URI de conexão com o MongoDB Atlas
        """
        self.client = MongoClient(mongodb_uri)
        self.db = self.client.finance_bot
        self.users = self.db.users
        self.transactions = self.db.transactions
        
    def create_user(self, user_id: int, username: str = None, chat_id: int = None) -> bool:
        """
        Cria um novo usuário no banco de dados.
        
        Args:
            user_id: ID do usuário no Telegram
            username: Nome de usuário do Telegram (opcional)
            chat_id: ID do chat do Telegram
            
        Returns:
            True se o usuário foi criado, False se já existia
        """
        try:
            existing_user = self.users.find_one({"user_id": user_id})
            if existing_user:
                # Atualiza o chat_id se necessário
                if chat_id and existing_user.get("chat_id") != chat_id:
                    self.users.update_one(
                        {"user_id": user_id},
                        {"$set": {"chat_id": chat_id}}
                    )
                return False
            
            user_data = {
                "user_id": user_id,
                "username": username,
                "chat_id": chat_id,
                "created_at": datetime.utcnow()
            }
            
            self.users.insert_one(user_data)
            logger.info(f"Usuário criado: {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao criar usuário: {e}")
            return False
    
    def get_user(self, user_id: int) -> Optional[Dict]:
        """
        Busca um usuário pelo ID.
        
        Args:
            user_id: ID do usuário no Telegram
            
        Returns:
            Dados do usuário ou None se não encontrado
        """
        try:
            return self.users.find_one({"user_id": user_id})
        except Exception as e:
            logger.error(f"Erro ao buscar usuário: {e}")
            return None
    
    def create_transaction(self, user_id: int, transaction_type: str, category: str, 
                          description: str, value: float, due_date: date = None,
                          is_installment: bool = False, installment_details: Dict = None) -> str:
        """
        Cria uma nova transação.
        
        Args:
            user_id: ID do usuário
            transaction_type: Tipo da transação ("receita" ou "despesa")
            category: Categoria da transação
            description: Descrição da transação
            value: Valor da transação
            due_date: Data de vencimento (para despesas)
            is_installment: Se é parcelada
            installment_details: Detalhes do parcelamento
            
        Returns:
            ID da transação criada
        """
        try:
            if due_date and isinstance(due_date, date) and not isinstance(due_date, datetime):
    due_date = datetime.combine(due_date, datetime.min.time())

transaction_data = {
                "user_id": user_id,
                "type": transaction_type,
                "category": category,
                "description": description,
                "value": value,
                "is_installment": is_installment,
                "due_date": due_date,
                "payment_date": None,
                "status": "aberto",
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            
            if is_installment and installment_details:
                transaction_data["installment_details"] = installment_details
            
            result = self.transactions.insert_one(transaction_data)
            logger.info(f"Transação criada: {result.inserted_id}")
            return str(result.inserted_id)
            
        except Exception as e:
            logger.error(f"Erro ao criar transação: {e}")
            return None
    
    def get_transactions(self, user_id: int, transaction_type: str = None, 
                        status: str = None, category: str = None) -> List[Dict]:
        """
        Busca transações do usuário com filtros opcionais.
        
        Args:
            user_id: ID do usuário
            transaction_type: Tipo da transação (opcional)
            status: Status da transação (opcional)
            category: Categoria da transação (opcional)
            
        Returns:
            Lista de transações
        """
        try:
            query = {"user_id": user_id}
            
            if transaction_type:
                query["type"] = transaction_type
            if status:
                query["status"] = status
            if category:
                query["category"] = category
            
            transactions = list(self.transactions.find(query).sort("created_at", -1))
            return transactions
            
        except Exception as e:
            logger.error(f"Erro ao buscar transações: {e}")
            return []
    
    def update_transaction_status(self, transaction_id: str, status: str, 
                                 payment_date: date = None) -> bool:
        """
        Atualiza o status de uma transação.
        
        Args:
            transaction_id: ID da transação
            status: Novo status
            payment_date: Data de pagamento (opcional)
            
        Returns:
            True se atualizado com sucesso
        """
        try:
            if payment_date and isinstance(payment_date, date) and not isinstance(payment_date, datetime):
    payment_date = datetime.combine(payment_date, datetime.min.time())

update_data = {
                "status": status,
                "updated_at": datetime.utcnow()
            }
            
            if payment_date:
                update_data["payment_date"] = payment_date
            
            result = self.transactions.update_one(
                {"_id": ObjectId(transaction_id)},
                {"$set": update_data}
            )
            
            return result.modified_count > 0
            
        except Exception as e:
            logger.error(f"Erro ao atualizar transação: {e}")
            return False
    
    def get_due_transactions(self, days_ahead: int = 3) -> List[Dict]:
        """
        Busca transações com vencimento próximo.
        
        Args:
            days_ahead: Quantos dias à frente buscar
            
        Returns:
            Lista de transações com vencimento próximo
        """
        try:
            from datetime import timedelta
            
            today = date.today()
    today = datetime.combine(today, datetime.min.time())
            target_date = today + timedelta(days=days_ahead)
    target_date = datetime.combine(target_date, datetime.min.time())
            
            query = {
                "type": "despesa",
                "status": "aberto",
                "due_date": {"$lte": target_date}
            }
            
            transactions = list(self.transactions.find(query))
            return transactions
            
        except Exception as e:
            logger.error(f"Erro ao buscar transações com vencimento: {e}")
            return []
    
    def get_categories(self, user_id: int) -> Dict[str, List[str]]:
        """
        Busca todas as categorias usadas pelo usuário.
        
        Args:
            user_id: ID do usuário
            
        Returns:
            Dicionário com categorias de receitas e despesas
        """
        try:
            receitas = self.transactions.distinct("category", 
                                                {"user_id": user_id, "type": "receita"})
            despesas = self.transactions.distinct("category", 
                                                {"user_id": user_id, "type": "despesa"})
            
            return {
                "receitas": receitas,
                "despesas": despesas
            }
            
        except Exception as e:
            logger.error(f"Erro ao buscar categorias: {e}")
            return {"receitas": [], "despesas": []}
    
    def get_monthly_summary(self, user_id: int, year: int, month: int) -> Dict:
        """
        Gera resumo mensal das transações.
        
        Args:
            user_id: ID do usuário
            year: Ano
            month: Mês
            
        Returns:
            Resumo mensal com receitas, despesas e saldo
        """
        try:
            from datetime import datetime
            
            start_date = datetime(year, month, 1)
            if month == 12:
                end_date = datetime(year + 1, 1, 1)
            else:
                end_date = datetime(year, month + 1, 1)
            
            query = {
                "user_id": user_id,
                "created_at": {"$gte": start_date, "$lt": end_date}
            }
            
            transactions = list(self.transactions.find(query))
            
            receitas = sum(t["value"] for t in transactions if t["type"] == "receita")
            despesas = sum(t["value"] for t in transactions if t["type"] == "despesa")
            saldo = receitas - despesas
            
            return {
                "receitas": receitas,
                "despesas": despesas,
                "saldo": saldo,
                "total_transacoes": len(transactions)
            }
            
        except Exception as e:
            logger.error(f"Erro ao gerar resumo mensal: {e}")
            return {"receitas": 0, "despesas": 0, "saldo": 0, "total_transacoes": 0}

