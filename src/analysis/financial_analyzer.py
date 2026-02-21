from collections import defaultdict
from typing import Any

from src.models.transaction import Transaction
from src.models.transaction import TransactionCategory


class FinancialAnalyzer:

    def __init__(self, transactions: list[Transaction]):
        self.transactions = transactions
        self._validate_data()

    def _validate_data(self):
        if not self.transactions:
            raise ValueError("No transactions provided.")
        dates = [t.date for t in self.transactions]
        span = (max(dates) - min(dates)).days
        if span < 30:
            raise ValueError(f"Not enough data: only {span} days of transactions.")

    def _months(self) -> float:
        dates = [t.date for t in self.transactions]
        return max((max(dates) - min(dates)).days / 30.0, 1.0)

    def get_spending_by_category(self) -> dict[str, float]:
        result: dict[str, float] = defaultdict(float)
        for t in self.transactions:
            if t.amount < 0:
                result[t.category] += abs(t.amount)
        return dict(result)

    def get_monthly_spending(self) -> dict[str, float]:
        result: dict[str, float] = defaultdict(float)
        for t in self.transactions:
            if t.amount < 0:
                result[t.date.strftime("%Y-%m")] += abs(t.amount)
        return dict(result)

    def get_income_summary(self) -> dict[str, float]:
        income_txns = [t for t in self.transactions if t.amount > 0]
        if not income_txns:
            return {
                "total": 0,
                "average_monthly": 0,
                "count": 0,
                "months_covered": 0,
                "monthly_savings": 0,
                "savings_rate": 0,
                "average_monthly_spending": 0,
            }

        total = sum(t.amount for t in income_txns)
        dates = [t.date for t in income_txns]
        months = max((max(dates) - min(dates)).days / 30, 1)
        avg_income = total / months

        monthly_spending = self.get_monthly_spending()
        avg_spending = (
            sum(monthly_spending.values()) / len(monthly_spending)
            if monthly_spending
            else 0
        )
        savings = avg_income - avg_spending

        return {
            "total": total,
            "average_monthly": avg_income,
            "count": len(income_txns),
            "months_covered": months,
            "monthly_savings": savings,
            "savings_rate": (savings / avg_income * 100) if avg_income > 0 else 0,
            "average_monthly_spending": avg_spending,
        }

    def get_debt_analysis(self) -> dict[str, Any]:
        debt_categories = {
            TransactionCategory.LOAN_PAYMENT,
            TransactionCategory.DEBT_PAYMENT,
            TransactionCategory.CREDIT_CARD_PAYMENT,
        }
        debt_txns = [t for t in self.transactions if t.category in debt_categories]
        total = sum(abs(t.amount) for t in debt_txns)

        monthly: dict[str, float] = defaultdict(float)
        for t in debt_txns:
            monthly[t.date.strftime("%Y-%m")] += abs(t.amount)

        avg_monthly = sum(monthly.values()) / len(monthly) if monthly else 0
        available = self.get_income_summary().get("monthly_savings", 0)
        potential = avg_monthly + max(0, available * 0.5)

        strategies = []
        if avg_monthly > 0:
            strategies = [
                {
                    "strategy": "debt_snowball",
                    "description": "Pay minimums on all debts, then put extra toward the smallest balance.",
                    "monthly_allocation": potential,
                },
                {
                    "strategy": "debt_avalanche",
                    "description": "Pay minimums on all debts, then put extra toward the highest-interest balance.",
                    "monthly_allocation": potential,
                },
            ]

        return {
            "total_debt_payments": total,
            "average_monthly_debt": avg_monthly,
            "debt_transaction_count": len(debt_txns),
            "monthly_breakdown": dict(monthly),
            "strategies": strategies,
            "available_for_debt": available,
        }

    def identify_spending_patterns(self) -> list[dict[str, Any]]:
        patterns = []
        category_spending = self.get_spending_by_category()
        monthly_spending = self.get_monthly_spending()
        avg_monthly = (
            sum(monthly_spending.values()) / len(monthly_spending)
            if monthly_spending
            else 0
        )
        months = self._months()

        for category, total in sorted(
            category_spending.items(), key=lambda x: x[1], reverse=True
        ):
            monthly_avg = total / months
            if monthly_avg > avg_monthly * 0.3:
                patterns.append(
                    {
                        "type": "high_spending",
                        "category": category,
                        "monthly_average": monthly_avg,
                        "insight": f"High spending in {category}: ${monthly_avg:,.2f}/month",
                    }
                )

        if TransactionCategory.FUEL in category_spending:
            fuel_transactions = [
                t for t in self.transactions if t.category == TransactionCategory.FUEL
            ]
            fuel_frequency = len(fuel_transactions)
            if fuel_frequency > 4 * months * 1.5:
                patterns.append(
                    {
                        "type": "frequent_fuel",
                        "category": TransactionCategory.FUEL,
                        "frequency": fuel_frequency,
                        "insight": f"Frequent fuel purchases: {fuel_frequency} times over the period",
                    }
                )

        if TransactionCategory.DINING in category_spending:
            dining_transactions = [
                t for t in self.transactions if t.category == TransactionCategory.DINING
            ]
            dining_frequency = len(dining_transactions)
            if dining_frequency > 8 * months * 1.5:
                patterns.append(
                    {
                        "type": "frequent_dining",
                        "category": TransactionCategory.DINING,
                        "frequency": dining_frequency,
                        "insight": f"Frequent dining out: {dining_frequency} times over the period",
                    }
                )

        return patterns

    def get_budget_recommendations(self) -> dict[str, Any]:
        income = self.get_income_summary()
        spending = self.get_spending_by_category()
        avg_income = income.get("average_monthly", 0)
        months = self._months()

        targets = {
            TransactionCategory.RENT: 30,
            TransactionCategory.GROCERIES: 10,
            TransactionCategory.FUEL: 5,
            TransactionCategory.UTILITIES: 5,
            TransactionCategory.DINING: 5,
            TransactionCategory.SHOPPING: 5,
        }

        recommendations = []
        total_recommended = 0.0
        for category, pct in targets.items():
            recommended = (avg_income * pct / 100) if avg_income > 0 else 0
            actual = spending.get(category.value, 0) / months
            total_recommended += recommended
            if actual > recommended * 1.2:
                cat_name = category.value.replace("_", " ").title()
                recommendations.append(
                    {
                        "category": cat_name,
                        "recommended_monthly": recommended,
                        "actual_monthly": actual,
                        "suggestion": (
                            f"Consider reducing {cat_name} by "
                            f"${actual - recommended:,.2f}/month"
                        ),
                    }
                )

        return {
            "recommendations": recommendations,
            "average_monthly_income": avg_income,
            "average_monthly_spending": income.get("average_monthly_spending", 0),
            "total_recommended_budget": total_recommended,
        }
