from datetime import datetime
from django.db import models
from django.db.models.base import ModelBase


GAAP_TO_READABLE_NAME_INCOMESTATEMENT = {
    "Revenues": "Revenues",
    "CostOfGoodsAndServicesSold": "Cost of Goods Sold",
    "GrossProfit": "Gross Profit",
    "SellingGeneralAndAdministrativeExpense": "Selling, General and Administrative Expense",
    "ResearchAndDevelopmentExpense": "Research and Development Expense",
    "OperatingIncomeLoss": "Operating Income (Loss), EBIT",
    "InvestmentIncomeInterestAndDividend": "Investment Income, Interest and Dividend",
    "InterestExpense": "Interest Expense",
    "NetIncomeLoss": "Net Income (Loss)",
    "EarningsPerShareBasic": "Earnings Per Share, Basic",  # Decimal
    "EarningsPerShareDiluted": "Earnings Per Share, Diluted",  # Decimal
    "DepreciationAndAmortization": "Depreciation, Depletion and Amortization",
}
GAAP_TO_READABLE_NAME_BALANCESHEET = {
    "CashAndCashEquivalentsAtCarryingValue": "Cash and Cash Equivalents",
    "CashAndCashEquivalentsPeriodIncreaseDecrease": "Increase (Decrease) in Cash and Cash Equivalents",
    "MarketableSecuritiesCurrent": "Marketable Securities, Current",
    "MarketableSecuritiesNoncurrent": "Marketable Securities, Noncurrent",
    "MarketableSecuritiesRealizedGainLoss": "Marketable Securities, Realized Gain (Loss)",
    "AccountsReceivableNetCurrent": "Accounts Receivable",
    "IncreaseDecreaseInAccountsReceivable": "Increase (Decrease) in Accounts Receivable",
    "InventoryNet": "Inventory, Net",
    "IncreaseDecreaseInInventories": "Increase (Decrease) in Inventories",
    "InventoryRawMaterialsAndPurchasedPartsNetOfReserves": "Inventory, Raw Materials and Purchased Parts",
    "InventoryFinishedGoodsNetOfReserves": "Inventories, Finished Goods",
    "NoncurrentAssets": "Long-Lived Assets",
    "Assets": "Total Assets",
    "AccountsPayable": "Accounts Payable",
    "AccountsPayableCurrent": "Accounts Payable, Current",
    "IncreaseDecreaseInAccountsPayable": "Increase (Decrease) in Accounts Payable",
    "TaxesPayableCurrent": "Taxes Payable, Current",
    "RepaymentsOfShortTermDebtMaturingInMoreThanThreeMonths": "Short-term Debt",
    "DeferredRevenueCurrent": "Deferred Revenue, Current",
    "LongTermDebt": "Long-term Debt",
    "LiabilitiesCurrent": "Liabilities, Current",
    "LiabilitiesNoncurrent": "Liabilities, Noncurrent",
    "Liabilities": "Total Liabilities",
    "CommonStockSharesOutstanding": "Common Stock, Shares, Outstanding",
    "RetainedEarningsAccumulatedDeficit": "Retained Earnings",
    "StockholdersEquity": "Stockholders' Equity",
}
GAAP_TO_READABLE_NAME_CASHFLOW = {
    # Cash Flow from Operation
    "NetIncomeLoss": "Net Income (Loss) from Continuing Operations",
    "DepreciationDepletionAndAmortization": "Depreciation, Depletion and Amortization",
    "NetCashProvidedByUsedInOperatingActivities": "Cash Flow from Operations",
    # Cash Flow from Investing
    "PaymentsToAcquirePropertyPlantAndEquipment": "Purchase of Property, Plant and Equipment",
    "PaymentsToAcquireAvailableForSaleSecuritiesDebt": "Purchase of Investment",
    "PaymentsToAcquireBusinessesNetOfCashAcquired": "Purchase of Business",
    "NetCashProvidedByUsedInInvestingActivities": "Cash Flow from Investing",
    # Cash Flow from Financing
    "PaymentsForRepurchaseOfCommonStock": "Repurchase of Stock",
    "NetCashProvidedByUsedInFinancingActivities": "Cash Flow from Financing",
    # Others
    "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents": "Ending Cash Position",
    "PaymentsToAcquirePropertyPlantAndEquipment": "Capital Expendtiures",
}
GAAP_TO_READABLE_NAME_OTHERDATA = {
    "CommonStockDividendsPerShareDeclared": "Dividends per Share",
}

OTHER_NAMES_INCOMESTATEMENT = [
    "Gross Margin",  # gross profit / revenues
    "Total Operating Expenses",  # selling, general and administration expense + research and development expense
    "Operating Margin",  # operating income (loss) / revenues
    "Net Interest Income",  # investment income, interest and dividend - interest expense
    "Net Margin",  # net income (loss) / revenues
    "EBITDA",  # operating income (loss) + depreciation and amortization
    "EBITDA Margin",  # EBITDA / revenues
]
OTHER_NAMES_BALANCESHEET = [
    "Total Receivables",
    "Total Inventories",
    "Current Assets",
    "Debt to Equity",  # decimal
    "Equity to Assets",  # decimal
]
OTHER_NAMES_CASHFLOW = [
    "Free Cash Flow",  # operating cash flow - capital expenditures
]
OTHER_NAMES_OTHERDATA = [
    "Revenue per Shares",
    "EBIT per Shares",
    "EBITDA per Shares",
    "Free Cash Flow per Shares",
    "Operating Cash Flow per Shares",
    "Cash per Shares",
    "Price to Earnings Ratio, PE Ratio",  # market price / earnings per share
    "Price to Book Ratio, PB Ratio",  # market price / book value (total assets - total liabilities)
]


class Stock(models.Model):
    ticker = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=255, null=True)
    country = models.CharField(max_length=255, null=True)
    ipo_year = models.IntegerField(null=True)
    sector = models.CharField(max_length=255, null=True)
    industry = models.CharField(max_length=255, null=True)
    market_cap = models.BigIntegerField(null=True)

    def __str__(self):
        return f"<{self.ticker}> {self.name}"

    class Meta:
        ordering = ["ticker", "name"]


class CandleStick(models.Model):
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE)
    date = models.DateField()
    open = models.DecimalField(max_digits=20, decimal_places=2, null=True)
    high = models.DecimalField(max_digits=20, decimal_places=2, null=True)
    low = models.DecimalField(max_digits=20, decimal_places=2, null=True)
    close = models.DecimalField(max_digits=20, decimal_places=2, null=True)
    # adj_close = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    volume = models.BigIntegerField(null=True, blank=True)
    turnover = models.BigIntegerField(null=True, blank=True)

    def __str__(self):
        return f"CandleStick <{self.stock.ticker}> {datetime.strftime(self.date, '%Y-%m-%d')}"

    class Meta:
        ordering = ["stock__id", "-date"]
        unique_together = ("stock", "date")


# --------------------------------------------------------------------------- #
# Metaclasses                                                                 #
# --------------------------------------------------------------------------- #
class IncomeStatementMeta(ModelBase):
    """
    This class is used to dynamicaaly add fields to the IncomeStatement model.
    """
    def __new__(cls, name, bases, attrs):
        for value in GAAP_TO_READABLE_NAME_INCOMESTATEMENT.values():
            if value in ("Earnings Per Share, Basic", "Earnings Per Share, Diluted"):
                attrs[value] = models.DecimalField(
                    null=True, decimal_places=3, max_digits=20
                )
            else:
                attrs[value] = models.BigIntegerField(null=True)

        for other_name in OTHER_NAMES_INCOMESTATEMENT:
            if other_name in (
                "Gross Margin",
                "Operating Margin",
                "Net Margin",
                "EBITDA Margin",
            ):
                attrs[other_name] = models.DecimalField(
                    null=True, decimal_places=3, max_digits=20
                )
            else:
                attrs[other_name] = models.BigIntegerField(null=True)

        return super().__new__(cls, name, bases, attrs)


class BalanceSheetMeta(ModelBase):
    """
    This class is used to dynamicaaly add fields to the BalanceSheet model.
    """

    def __new__(cls, name, bases, attrs):
        for value in GAAP_TO_READABLE_NAME_BALANCESHEET.values():
            attrs[value] = models.BigIntegerField(null=True)

        for other_name in OTHER_NAMES_BALANCESHEET:
            if other_name in ("Debt to Equity", "Equity to Assets"):
                attrs[other_name] = models.DecimalField(
                    null=True, decimal_places=3, max_digits=20
                )
            else:
                attrs[other_name] = models.BigIntegerField(null=True)

        return super().__new__(cls, name, bases, attrs)


class CashFlowMeta(ModelBase):
    """
    This class is used to dynamicaaly add fields to the CashFlow model.
    """

    def __new__(cls, name, bases, attrs):
        for value in GAAP_TO_READABLE_NAME_CASHFLOW.values():
            if value:
                attrs[value] = models.BigIntegerField(null=True)
        
        for other_name in OTHER_NAMES_CASHFLOW:
            attrs[other_name] = models.BigIntegerField(null=True)

        return super().__new__(cls, name, bases, attrs)


class OtherDataMeta(ModelBase):
    """
    This class is used to dynamicaaly add fields to the PerShareData model.
    """

    def __new__(cls, name, bases, attrs):
        for value in GAAP_TO_READABLE_NAME_OTHERDATA.values():
            attrs[value] = models.DecimalField(null=True, decimal_places=3, max_digits=20)
        
        for other_name in OTHER_NAMES_OTHERDATA:
            attrs[other_name] = models.DecimalField(null=True, decimal_places=3, max_digits=20)
        
        return super().__new__(cls, name, bases, attrs)


# --------------------------------------------------------------------------- #
# Normal classes                                                              #
# --------------------------------------------------------------------------- #
class IncomeStatement(models.Model, metaclass=IncomeStatementMeta):
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE)
    FileDate = models.DateField(null=True)
    EndDate = models.DateField(null=True)

    def __str__(self):
        return f"IncomeStatement <{self.stock.ticker}> {self.FileDate}"

    class Meta:
        unique_together = [["stock", "FileDate"]]
        ordering = ["stock__id", "-FileDate"]


class BalanceSheet(models.Model, metaclass=BalanceSheetMeta):
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE)
    FileDate = models.DateField(null=True)
    EndDate = models.DateField(null=True)

    def __str__(self):
        return f"BalanceSheet <{self.stock.ticker}> {self.FileDate}"

    class Meta:
        unique_together = [["stock", "FileDate"]]
        ordering = ["stock__id", "-FileDate"]


class CashFlow(models.Model, metaclass=CashFlowMeta):
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE)
    FileDate = models.DateField(null=True)
    EndDate = models.DateField(null=True)

    def __str__(self):
        return f"CashFlow <{self.stock.ticker}> {self.FileDate}"

    class Meta:
        unique_together = [["stock", "FileDate"]]
        ordering = ["stock__id", "-FileDate"]


class OtherData(models.Model, metaclass=OtherDataMeta):
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE)
    FileDate = models.DateField(null=True)
    EndDate = models.DateField(null=True)

    def __str__(self):
        return f"OtherData <{self.stock.ticker}> {self.FileDate}"

    class Meta:
        unique_together = [["stock", "FileDate"]]
        ordering = ["stock__id", "-FileDate"]
