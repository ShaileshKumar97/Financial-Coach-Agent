import random
from datetime import datetime
from datetime import timedelta

import pandas as pd

from src.models.transaction import Transaction
from src.models.transaction import TransactionCategory
from src.models.transaction import TransactionType


class TransactionLoader:

    @staticmethod
    def load_from_csv(file_path: str) -> list[Transaction]:
        """Load existing transactions from a CSV file."""
        df = pd.read_csv(file_path)
        transactions = []

        for _, row in df.iterrows():
            try:
                date = pd.to_datetime(row["date"]).to_pydatetime()
                amount = float(row["amount"])
                category = TransactionCategory(row.get("category", "other").lower())
                trans_type = TransactionType(row.get("type", "debit").lower())
                description = str(row.get("description", ""))
                account_type = row.get("account_type", None)

                transactions.append(
                    Transaction(
                        date=date,
                        amount=amount,
                        category=category,
                        description=description,
                        type=trans_type,
                        account_type=account_type,
                    )
                )
            except Exception as e:
                print(f"Error parsing transaction row: {e}")
                continue

        return transactions

    @staticmethod
    def create_sample_data() -> list[Transaction]:
        """Create sample transaction data for 6 months."""
        transactions = []
        base_date = datetime.now() - timedelta(days=180)

        # Income (bi-weekly)
        for month in range(6):
            for week in [0, 2]:
                transactions.append(
                    Transaction(
                        date=base_date + timedelta(days=month * 30 + week * 14),
                        amount=2250.0,
                        category=TransactionCategory.INCOME,
                        description="Salary deposit",
                        type=TransactionType.CREDIT,
                        account_type="checking",
                    )
                )

        # Regular expenses
        for month in range(6):
            transactions.append(
                Transaction(
                    date=base_date + timedelta(days=month * 30 + 1),
                    amount=-1200.0,
                    category=TransactionCategory.RENT,
                    description="Monthly rent",
                    type=TransactionType.DEBIT,
                    account_type="checking",
                )
            )

            transactions.append(
                Transaction(
                    date=base_date + timedelta(days=month * 30 + 5),
                    amount=-350.0,
                    category=TransactionCategory.LOAN_PAYMENT,
                    description="Car loan",
                    type=TransactionType.DEBIT,
                    account_type="checking",
                )
            )

            transactions.append(
                Transaction(
                    date=base_date + timedelta(days=month * 30 + 10),
                    amount=-random.uniform(200, 500),
                    category=TransactionCategory.CREDIT_CARD_PAYMENT,
                    description="Credit card payment",
                    type=TransactionType.DEBIT,
                    account_type="checking",
                )
            )

            transactions.append(
                Transaction(
                    date=base_date + timedelta(days=month * 30 + 15),
                    amount=-120.0,
                    category=TransactionCategory.INSURANCE,
                    description="Car insurance",
                    type=TransactionType.DEBIT,
                    account_type="checking",
                )
            )

        # Weekly expenses
        for week in range(26):
            transactions.append(
                Transaction(
                    date=base_date + timedelta(days=week * 7),
                    amount=-random.uniform(80, 150),
                    category=TransactionCategory.GROCERIES,
                    description="Grocery shopping",
                    type=TransactionType.DEBIT,
                    account_type="checking",
                )
            )

            for _ in range(random.randint(2, 3)):
                transactions.append(
                    Transaction(
                        date=base_date
                        + timedelta(days=week * 7 + random.randint(0, 6)),
                        amount=-random.uniform(35, 65),
                        category=TransactionCategory.FUEL,
                        description="Gas",
                        type=TransactionType.DEBIT,
                        account_type="checking",
                    )
                )

                transactions.append(
                    Transaction(
                        date=base_date
                        + timedelta(days=week * 7 + random.randint(0, 6)),
                        amount=-random.uniform(15, 60),
                        category=TransactionCategory.DINING,
                        description="Dining out",
                        type=TransactionType.DEBIT,
                        account_type="checking",
                    )
                )

        # Monthly utilities
        for month in range(6):
            for desc, amount in [
                ("Electricity", -random.uniform(80, 150)),
                ("Internet", -random.uniform(60, 80)),
                ("Water", -random.uniform(40, 70)),
            ]:
                transactions.append(
                    Transaction(
                        date=base_date
                        + timedelta(days=month * 30 + random.randint(5, 15)),
                        amount=amount,
                        category=TransactionCategory.UTILITIES,
                        description=desc,
                        type=TransactionType.DEBIT,
                        account_type="checking",
                    )
                )

        # Occasional expenses
        for month in range(6):
            for _ in range(random.randint(2, 4)):
                transactions.append(
                    Transaction(
                        date=base_date
                        + timedelta(days=month * 30 + random.randint(0, 29)),
                        amount=-random.uniform(30, 200),
                        category=TransactionCategory.SHOPPING,
                        description="Shopping",
                        type=TransactionType.DEBIT,
                        account_type="checking",
                    )
                )

            if random.random() < 0.2:
                transactions.append(
                    Transaction(
                        date=base_date
                        + timedelta(days=month * 30 + random.randint(0, 29)),
                        amount=-random.uniform(50, 300),
                        category=TransactionCategory.CAR_SERVICE,
                        description="Car maintenance",
                        type=TransactionType.DEBIT,
                        account_type="checking",
                    )
                )

        transactions.sort(key=lambda x: x.date)
        return transactions
