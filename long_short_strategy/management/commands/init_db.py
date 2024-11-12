import datetime as dt
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import models
import json
import logging
from long_short_strategy.models import Stock, FinancialReport, BalanceSheet, CashFlow, IncomeStatement
import numpy as np
import os
import pandas as pd
from tqdm import tqdm
from typing import Tuple, Type
import yfinance as yf


class Command(BaseCommand):
    help = 'Initialize the database for long_short_strategy'

    def handle(self, *args, **options):
        # Decision of deleting all stocks
        self.stdout.write(self.style.WARNING("'DELETE' ALL DATA? It would be irreversible."))
        while (ans := input('(y/n) ').strip().lower()) not in ('y', 'n'):
            print("Please enter 'y' or 'n")
        if ans == 'y':
            delete_data_from_db_table(Stock, FinancialReport)
            self.stdout.write(self.style.SUCCESS("Stock data 'DELETE' success!"))

        # Decision of updating all stocks
        self.stdout.write(self.style.WARNING("'UPDATE' STOCK DATA?"))
        df_stock_list = get_stock_list()
        while (ans := input('(y/n) ').strip().lower()) not in ('y', 'n'):
            print("Please enter 'y' or 'n")
        if ans == 'y':
            update_stock_list_db(df_stock_list)
            self.stdout.write(self.style.SUCCESS("Stock data 'UPDATE' success!"))

        # Decision of updating all financial reports
        self.stdout.write(self.style.WARNING("'UPDATE' FINANCIAL REPORT?"))
        while (ans := input('(y/n) ').strip().lower()) not in ('y', 'n'):
            print("Please enter 'y' or 'n")
        if ans == 'n':
            self.stdout.write(self.style.NOTICE('Financial report data "UPDATE" canceled!'))
            return

        # Get all stock objects and store them in a dictionary
        stocks = {stock.symbol: stock for stock in Stock.objects.all()}

        # Initialize pending lists to be bulk updated
        l_financial_reports = []
        l_balance_sheets = []
        l_cash_flows = []
        l_income_statements = []

        # Loop over the stock list
        for index, row in tqdm(df_stock_list.iterrows(), desc="Initializing financial report database..."):
            # Fetch data from yfinance
            financials, balance_sheet, cash_flow, income_statement = get_financial_data(row['Symbol'])

            # Get symbol from Stock table
            stock = stocks.get(row['Symbol'])

            # If the stock doesn't exist, you cannot create its financial report
            if stock:
                db_financial = get_or_create_from_db(stock, financials, FinancialReport)
                db_balance_sheet = get_or_create_from_db(stock, balance_sheet, BalanceSheet)
                db_cash_flow = get_or_create_from_db(stock, cash_flow, CashFlow)
                db_income_statement = get_or_create_from_db(stock, income_statement, IncomeStatement)

                # Add to pending list
                l_financial_reports.append(db_financial)
                l_balance_sheets.append(db_balance_sheet)
                l_cash_flows.append(db_cash_flow)
                l_income_statements.append(db_income_statement)

        # Prepare fields to update
        fields_to_update_fn = [field.name for field in FinancialReport._meta.get_fields() if
                               field.concrete and field.name != 'id' and field.name != 'symbol_id']
        fields_to_update_bs = [field.name for field in BalanceSheet._meta.get_fields() if
                               field.concrete and field.name != 'id' and field.name != 'symbol_id']
        fields_to_update_cf = [field.name for field in CashFlow._meta.get_fields() if
                               field.concrete and field.name != 'id' and field.name != 'symbol_id']
        fields_to_update_is = [field.name for field in IncomeStatement._meta.get_fields() if
                               field.concrete and field.name != 'id' and field.name != 'symbol_id']

        # Bulk update
        FinancialReport.objects.bulk_update(l_financial_reports, fields=fields_to_update_fn, batch_size=100)
        BalanceSheet.objects.bulk_update(l_balance_sheets, fields=fields_to_update_bs, batch_size=100)
        CashFlow.objects.bulk_update(l_cash_flows, fields=fields_to_update_cf, batch_size=100)
        IncomeStatement.objects.bulk_update(l_income_statements, fields=fields_to_update_is, batch_size=100)

        # Success
        self.stdout.write(self.style.SUCCESS("Financial data 'UPDATE' success!"))


def delete_data_from_db_table(*args) -> bool:
    """
    Delete data from database
    :param args: Table object(models.Model)
    :return: Success of fail (True/ False)
    """
    res = input(
        "You are going to delete the stock data, it will delete its related data, like any price data and non price data, and it is irreversible.\nAre you sure to delete all records? (y/n) ")
    if res.strip().lower() == 'n':
        return False

    logging.warning("Deleting all records...")
    [table.objects.all().delete() for table in args]

    return True


def update_stock_list_db(stock_list: pd.DataFrame):
    l_stocks = []

    # Loop over the stock list
    for index, row in tqdm(stock_list.iterrows(), desc="Updating stock table from database..."):
        # Create or update Stock
        ipo_year = 0 if np.isnan(row['IPO Year']) else row['IPO Year']
        market_cap = 0 if np.isnan(row['Market Cap']) else row['Market Cap']

        stock, created = Stock.objects.get_or_create(symbol=row['Symbol'])
        stock.name = row['Name']
        stock.country = row['Country']
        stock.ipo_year = ipo_year
        stock.sector = row['Sector']
        stock.industry = row['Industry']
        stock.market_cap = market_cap

        # Add Stock instance to a list, pending to be bulk updated
        l_stocks.append(stock)

    # Bulk update
    fields = [field.name for field in Stock._meta.get_fields() if field.concrete and field.name != 'id']
    Stock.objects.bulk_update(l_stocks, fields=fields, batch_size=100)


def get_stock_list() -> pd.DataFrame:
    # Get stock list, download from https://www.nasdaq.com/market-activity/stocks/screener
    csv_file = os.path.join(settings.BASE_DIR, 'static', 'stock_list', 'nasdaq_screener.csv')
    return pd.read_csv(csv_file)


def get_financial_data(symbol: str) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    ticker = yf.Ticker(symbol)
    financials = ticker.quarterly_financials
    balance_sheet = ticker.quarterly_balance_sheet
    cash_flow = ticker.quarterly_cash_flow
    income_statement = ticker.quarterly_income_stmt

    return financials, balance_sheet, cash_flow, income_statement


def get_or_create_from_db(stock: models.Model,
                          data: pd.DataFrame,
                          model: Type[FinancialReport | BalanceSheet | CashFlow | IncomeStatement]
                          ) -> models.Model:
    # Create dict: {report_date: report_data, ...}
    report_dates = {}
    for report_date in data.columns:
        report_date_str = dt.datetime.strftime(report_date, '%b%y')
        report_dates[report_date_str] = json.loads(data[report_date].to_json())

    # Create or update data
    report, created = model.objects.get_or_create(symbol=stock)
    for date, report_data in report_dates.items():
        setattr(report, date, report_data)

    return report
