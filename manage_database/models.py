from django.db import models


# GAAP / Data Name Mapper
GAAP_TO_READABLE_NAME_INCOME_STATEMENT = {
    "RevenueFromContractWithCustomerExcludingAssessedTax": "NetSales",
    "OtherIncome": "OtherIncome",
    "Revenues": "TotalRevenue",
    "CostOfRevenue": "CostOfSales",
    "SellingGeneralAndAdministrativeExpense": "OperatingSellingGeneralAndAdministrativeExpenses",
    "OperatingIncomeLoss": "OperatingIncome",
    "InterestExpenseDebt": "Debt",
    "FinanceLeaseInterestExpense": "FinanceLease",
    "InvestmentIncomeInterest": "InterestIncome",
    "InterestIncomeExpenseNonoperatingNet": "InterestNet",
    "NonoperatingIncomeExpense": "OtherIncomeExpense",
    "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest": "IncomeBeforeIncomeTaxes",
    "IncomeTaxExpenseBenefit": "ProvisionForIncomeTaxes",
    "ProfitLoss": "ConsolidatedNetIncome",
    "NetIncomeLossAttributableToNoncontrollingInterest": "ConsolidatedNetIncomeAttributableToNoncontrollingInterest",
    "NetIncomeLoss": "ConsolidatedNetIncomeAttributableToThisCompany",
    "EarningsPerShareBasic": "BasicEarningPerShareEPS",
    "EarningsPerShareDiluted": "DilutedEarningPerShareEPS",
    "WeightedAverageNumberOfSharesOutstandingBasic": "BasicWeightedAverageShares",
    "WeightedAverageNumberOfDilutedSharesOutstanding": "DilutedWeightedAverageShares",
    "CommonStockDividendsPerShareDeclared": "DividendsPerShareDPS",
}
GAAP_TO_READABLE_NAME_BALANCE_SHEET = {
    "CashAndCashEquivalentsAtCarryingValue": "CashAndCashEquivalents",
    "CashAndCashEquivalentsAtCarryingValue": "ReceivablesNet",
    "InventoryNet": "Inventories",
    "PrepaidExpenseAndOtherAssetsCurrent": "PrepaidExpensesAndOther",
    "AssetsCurrent": "TotalCurrentAssets",
    "PropertyPlantAndEquipmentNet": "PropertyAndEquipmentNet",
    "OperatingLeaseRightOfUseAsset": "OperatingLeaseRightOfUseAssets",
    "FinanceLeaseRightOfUseAsset": "FinanceLeaseRightOfUseAssetsNet",
    "Goodwill": "Goodwill",
    "OtherAssetsNoncurrent": "OtherLongTermAssets",
    "Assets": "TotalAssets",
    "ShortTermBorrowings": "ShortTermBorrowings",
    "AccountsPayableCurrent": "AccountsPayable",
    "DividendsPayableCurrent": "DividendsPayable",
    "AccruedLiabilitiesCurrent": "AccruedLiabilities",
    "AccruedIncomeTaxesCurrent": "AccruedIncomeTaxes",
    "LongTermDebtCurrent": "LongTermDebtDueWithinOneYear",
    "ShortTermBorrowings": "ShortTermDebt",
    "DebtLongtermAndShorttermCombinedAmount": "TotalDebt",
    "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents": "EndCashPosition",
    "OperatingLeaseLiabilityCurrent": "OperatingLeaseObligationsDueWithinOneYear",
    "FinanceLeaseLiabilityCurrent": "FinanceLeaseObligationsDueWithinOneYear",
    "LiabilitiesCurrent": "TotalCurrentLiabilities",
    "LongTermDebtNoncurrent": "LongTermDebt",
    "OperatingLeaseLiabilityNoncurrent": "LongTermOperatingLeaseObligations",
    "FinanceLeaseLiabilityNoncurrent": "LongTermFinanceLeaseObligations",
    "DeferredIncomeTaxesAndOtherLiabilitiesNoncurrent": "DeferredIncomeTaxesAndOther",
    "RedeemableNoncontrollingInterestEquityCarryingAmount": "RedeemableNoncontrollingInterest",
    "CommonStockValue": "CommonStock",
    "AdditionalPaidInCapital": "CapitalInExcessOfParValue",
    "RetainedEarningsAccumulatedDeficit": "RetainedEarnings",
    "AccumulatedOtherComprehensiveIncomeLossNetOfTax": "AccumulatedOtherComprehensiveLoss",
    "StockholdersEquity": "TotalShareholdersEquity",
    "MinorityInterest": "NonredeemableNoncontrollingInterest",
    "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest": "TotalEquity",
    "LiabilitiesAndStockholdersEquity": "TotalLiabilitiesRedeemableNoncontrollingInterestAndEquity",
}
GAAP_TO_READABLE_NAME_CASH_FLOW = {
    "ProfitLoss": "ConsolidatedNetIncome",
    "DepreciationAmortizationAndAccretionNet": "DepreciationAndAmortization",
    "GainLossOnInvestments": "InvestmentGainsAndLossesNet",
    "IncreaseDecreaseInDeferredIncomeTaxes": "DeferredIncomeTaxes",
    "OtherNoncashIncomeExpense": "OtherOperatingActivities",
    "IncreaseDecreaseInAccountsAndOtherReceivables": "ChangesInReceivablesNet",
    "IncreaseDecreaseInRetailRelatedInventories": "ChangesInInventories",
    "IncreaseDecreaseInAccountsPayable": "ChangesInAccountsPayable",
    "IncreaseDecreaseInAccruedLiabilities": "ChangesInAccruedLiabilities",
    "IncreaseDecreaseInAccruedTaxesPayable": "ChangesInAccruedIncomeTaxes",
    "NetCashProvidedByUsedInOperatingActivities": "OperatingCashFlow",
    "PaymentsToAcquirePropertyPlantAndEquipment": "PaymentsForPropertyAndEquipment",
    "ProceedsFromSaleOfPropertyPlantAndEquipment": "ProceedsFromDisposalOfPropertyAndEquipment",
    "ProceedsFromDivestitureOfBusinesses": "ProceedsFfromDisposalOfCertainOperations",
    "ProceedsFromSaleOfEquitySecuritiesFvNi": "ProceedsFromDisposalOfCertainStrategicInvestments",
    "PaymentsForProceedsFromOtherInvestingActivities": "OtherInvestingActivities",
    "NetCashProvidedByUsedInInvestingActivities": "InvestingCashFlow",
    "ProceedsFromRepaymentsOfShortTermDebt": "NetChangeInShortTermBorrowings",
    "ProceedsFromIssuanceOfLongTermDebt": "ProceedsFromIssuanceOfLongTermDebt",
    "RepaymentsOfLongTermDebt": "RepaymentsOfLongTermDebt",
    "PaymentsOfDividendsCommonStock": "DividendsPaid",
    "PaymentsForRepurchaseOfCommonStock": "PurchaseOfCompanyStock",
    "PaymentsOfDividendsMinorityInterest": "DividendsPaidToNoncontrollingInterest",
    "ProceedsFromIssuanceOrSaleOfEquity": "SaleOfSubsidiaryStock",
    "PaymentsToMinorityShareholders": "PurchaseOfNoncontrollingInterest",
    "ProceedsFromPaymentsForOtherFinancingActivities": "OtherFinancingActivities",
    "NetCashProvidedByUsedInFinancingActivities": "FinancingCashFlow",
    "EffectOfExchangeRateOnCashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents": "EffectOfExchangeRatesOnCcashCashEquivalentsAndRestrictedCash",
    "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalentsPeriodIncreaseDecreaseIncludingExchangeRateEffect": "NetIncreaseInCashCashEquivalentsAndRestrictedCash",
    "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents": "EndCashPosition",
    "PropertyPlantAndEquipmentNet": "PropertyAndEquipmentNet",
}


"""
Please make sure the values of the above dict match the following class attributes.
"""

class Stock(models.Model):
    ticker = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=255)
    country = models.CharField(max_length=255)
    ipo_year = models.IntegerField(null=True)
    sector = models.CharField(max_length=255)
    industry = models.CharField(max_length=255)
    market_cap = models.BigIntegerField(null=True)

    def __str__(self):
        return self.ticker


class CandleStick(models.Model):
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE)
    date = models.DateTimeField()
    open = models.DecimalField(max_digits=20, decimal_places=2, null=True)
    high = models.DecimalField(max_digits=20, decimal_places=2, null=True)
    low = models.DecimalField(max_digits=20, decimal_places=2, null=True)
    close = models.DecimalField(max_digits=20, decimal_places=2, null=True)
    # adj_close = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    volume = models.IntegerField(null=True)


class IncomeStatement(models.Model):
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE)
    FileDate = models.DateField(null=True)
    StartDate = models.DateField(null=True)
    EndDate = models.DateField(null=True)
    FiscalPeriod = models.CharField(max_length=5, blank=True, null=True)

    # Data downloaded from www.sec.gov
    NetSales = models.BigIntegerField(null=True)
    OtherIncome = models.BigIntegerField(null=True)
    TotalRevenue = models.BigIntegerField(null=True)
    CostOfSales = models.BigIntegerField(null=True)
    OperatingSellingGeneralAndAdministrativeExpenses = models.BigIntegerField(null=True)
    OperatingIncome = models.BigIntegerField(null=True)
    Debt = models.BigIntegerField(null=True)
    FinanceLease = models.BigIntegerField(null=True)
    InterestIncome = models.BigIntegerField(null=True)
    InterestNet = models.BigIntegerField(null=True)
    OtherIncomeExpense = models.BigIntegerField(null=True)
    IncomeBeforeIncomeTaxes = models.BigIntegerField(null=True)
    ProvisionForIncomeTaxes = models.BigIntegerField(null=True)
    ConsolidatedNetIncome = models.BigIntegerField(null=True)
    ConsolidatedNetIncomeAttributableToNoncontrollingInterest = models.BigIntegerField(
        null=True
    )
    ConsolidatedNetIncomeAttributableToThisCompany = models.BigIntegerField(null=True)
    BasicEarningPerShareEPS = models.DecimalField(
        max_digits=20, decimal_places=2, null=True
    )
    DilutedEarningPerShareEPS = models.DecimalField(
        max_digits=20, decimal_places=2, null=True
    )
    BasicWeightedAverageShares = models.BigIntegerField(null=True)
    DilutedWeightedAverageShares = models.BigIntegerField(null=True)
    DividendsPerShareDPS = models.DecimalField(
        max_digits=20, decimal_places=2, null=True
    )

    # Other important indicators calculated separately
    GrossProfit = models.BigIntegerField(null=True)
    TotalExpenses = models.BigIntegerField(null=True)
    InterestExpenses = models.BigIntegerField(null=True)
    Ebit = models.BigIntegerField(null=True)


class BalanceSheet(models.Model):
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE)
    FileDate = models.DateField(null=True)
    StartDate = models.DateField(null=True)
    EndDate = models.DateField(null=True)
    FiscalPeriod = models.CharField(max_length=5, blank=True, null=True)

    # Data downloaded from www.sec.gov
    CashAndCashEquivalents = models.BigIntegerField(null=True)
    ReceivablesNet = models.BigIntegerField(null=True)
    Inventories = models.BigIntegerField(null=True)
    PrepaidExpensesAndOther = models.BigIntegerField(null=True)
    TotalCurrentAssets = models.BigIntegerField(null=True)
    PropertyAndEquipmentNet = models.BigIntegerField(null=True)
    OperatingLeaseRightOfUseAssets = models.BigIntegerField(null=True)
    FinanceLeaseRightOfUseAssetsNet = models.BigIntegerField(null=True)
    Goodwill = models.BigIntegerField(null=True)
    OtherLongTermAssets = models.BigIntegerField(null=True)
    TotalAssets = models.BigIntegerField(null=True)
    ShortTermBorrowings = models.BigIntegerField(null=True)
    AccountsPayable = models.BigIntegerField(null=True)
    DividendsPayable = models.BigIntegerField(null=True)
    AccruedLiabilities = models.BigIntegerField(null=True)
    AccruedIncomeTaxes = models.BigIntegerField(null=True)
    LongTermDebtDueWithinOneYear = models.BigIntegerField(null=True)
    ShortTermDebt = models.BigIntegerField(null=True)
    TotalDebt = models.BigIntegerField(null=True)
    EndCashPosition = models.BigIntegerField(null=True)
    OperatingLeaseObligationsDueWithinOneYear = models.BigIntegerField(null=True)
    FinanceLeaseObligationsDueWithinOneYear = models.BigIntegerField(null=True)
    TotalCurrentLiabilities = models.BigIntegerField(null=True)
    LongTermDebt = models.BigIntegerField(null=True)
    LongTermOperatingLeaseObligations = models.BigIntegerField(null=True)
    LongTermFinanceLeaseObligations = models.BigIntegerField(null=True)
    DeferredIncomeTaxesAndOther = models.BigIntegerField(null=True)
    RedeemableNoncontrollingInterest = models.BigIntegerField(null=True)
    CommonStock = models.BigIntegerField(null=True)
    CapitalInExcessOfParValue = models.BigIntegerField(null=True)
    RetainedEarnings = models.BigIntegerField(null=True)
    AccumulatedOtherComprehensiveLoss = models.BigIntegerField(null=True)
    TotalShareholdersEquity = models.BigIntegerField(null=True)
    NonredeemableNoncontrollingInterest = models.BigIntegerField(null=True)
    TotalEquity = models.BigIntegerField(null=True)
    TotalLiabilitiesRedeemableNoncontrollingInterestAndEquity = models.BigIntegerField(
        null=True
    )

    # Other import indicators calculated spearately
    TotalNonCurrentAssets = models.BigIntegerField(null=True)
    TotalNonCurrentLiabilities = models.BigIntegerField(null=True)
    TotalLiabilities = models.BigIntegerField(null=True)
    TotalCapitalization = models.BigIntegerField(null=True)
    NetTangibleAssets = models.BigIntegerField(null=True)
    NetWorkingCapital = models.BigIntegerField(null=True)
    InvestedCapital = models.BigIntegerField(null=True)
    NetDebt = models.BigIntegerField(null=True)


class CashFlow(models.Model):
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE)
    FileDate = models.DateField(null=True)
    StartDate = models.DateField(null=True)
    EndDate = models.DateField(null=True)
    FiscalPeriod = models.CharField(max_length=5, blank=True, null=True)

    # Data downloaded from www.sec.gov
    ConsolidatedNetIncome = models.BigIntegerField(null=True)
    DepreciationAndAmortization = models.BigIntegerField(null=True)
    InvestmentGainsAndLossesNet = models.BigIntegerField(null=True)
    DeferredIncomeTaxes = models.BigIntegerField(null=True)
    OtherOperatingActivities = models.BigIntegerField(null=True)
    ChangesInReceivablesNet = models.BigIntegerField(null=True)
    ChangesInInventories = models.BigIntegerField(null=True)
    ChangesInAccountsPayable = models.BigIntegerField(null=True)
    ChangesInAccruedLiabilities = models.BigIntegerField(null=True)
    ChangesInAccruedIncomeTaxes = models.BigIntegerField(null=True)
    OperatingCashFlow = models.BigIntegerField(null=True)
    PaymentsForPropertyAndEquipment = models.BigIntegerField(null=True)
    ProceedsFromDisposalOfPropertyAndEquipment = models.BigIntegerField(null=True)
    ProceedsFfromDisposalOfCertainOperations = models.BigIntegerField(null=True)
    ProceedsFromDisposalOfCertainStrategicInvestments = models.BigIntegerField(
        null=True
    )
    OtherInvestingActivities = models.BigIntegerField(null=True)
    InvestingCashFlow = models.BigIntegerField(null=True)
    NetChangeInShortTermBorrowings = models.BigIntegerField(null=True)
    ProceedsFromIssuanceOfLongTermDebt = models.BigIntegerField(null=True)
    RepaymentsOfLongTermDebt = models.BigIntegerField(null=True)
    DividendsPaid = models.BigIntegerField(null=True)
    PurchaseOfCompanyStock = models.BigIntegerField(null=True)
    DividendsPaidToNoncontrollingInterest = models.BigIntegerField(null=True)
    SaleOfSubsidiaryStock = models.BigIntegerField(null=True)
    PurchaseOfNoncontrollingInterest = models.BigIntegerField(null=True)
    OtherFinancingActivities = models.BigIntegerField(null=True)
    FinancingCashFlow = models.BigIntegerField(null=True)
    EffectOfExchangeRatesOnCcashCashEquivalentsAndRestrictedCash = (
        models.BigIntegerField(null=True)
    )
    NetIncreaseInCashCashEquivalentsAndRestrictedCash = models.BigIntegerField(
        null=True
    )
    EndCashPosition = models.BigIntegerField(null=True)
    PropertyAndEquipmentNet = models.BigIntegerField(null=True)

    # Other important indicators calculated separately
    CapitalExpenditure = models.BigIntegerField(null=True)
    FreeCashFlow = models.BigIntegerField(null=True)
