import datetime as dt
from django.conf import settings
from django.core.management.base import BaseCommand
import logging
from long_short_strategy.models import Stock, FinancialReport, BalanceSheet, CashFlow, CandleStick
import numpy as np
import os
import pandas as pd
from tqdm import tqdm
from typing import Tuple, Type
import yfinance as yf


class Command(BaseCommand):
    help = 'Initialize the database for long_short_strategy'

    def handle(self, *args, **options):
        df_stock_list = get_stock_list()
        self.querying_delete_all_stock()
        self.querying_update_all_stock(df_stock_list)
        self.querying_update_all_candlestick(df_stock_list)
        self.querying_update_financial_report(df_stock_list)

    def querying_delete_all_stock(self):
        self.stdout.write(self.style.WARNING("'DELETE' ALL DATA? It would be irreversible."))
        while (ans := input('(y/n) ').strip().lower()) not in ('y', 'n'):
            print("Please enter 'y' or 'n")
        if ans.strip().lower() == 'y':
            delete_data_from_db_table(Stock)
            self.stdout.write(self.style.SUCCESS("Stock data 'DELETE' success!"))

    def querying_update_all_stock(self, df_stock_list: pd.DataFrame):
        self.stdout.write(self.style.WARNING("'UPDATE' STOCK DATA?"))
        while (ans := input('(y/n) ').strip().lower()) not in ('y', 'n'):
            print("Please enter 'y' or 'n")
        if ans.strip().lower() == 'y':
            update_stock_list_db(df_stock_list)
            self.stdout.write(self.style.SUCCESS("Stock data 'UPDATE' success!"))

    def querying_update_all_candlestick(self, df_stock_list: pd.DataFrame):
        self.stdout.write(self.style.WARNING("'UPDATE' CANDLESTICK DATA?"))
        print("It will delete all candlestick data and download it again.")
        while (ans := input('(y/n) ').strip().lower()) not in ('y', 'n'):
            print("Please enter 'y' or 'n")
        if ans.strip().lower() == 'y':
            update_candlestick_db(df_stock_list)
            self.stdout.write(self.style.SUCCESS("Candlestick data 'UPDATE' success!"))

    def querying_update_financial_report(self, df_stock_list: pd.DataFrame):
        self.stdout.write(self.style.WARNING("'UPDATE' FINANCIAL REPORT?"))
        while (ans := input('(y/n) ').strip().lower()) not in ('y', 'n'):
            print("Please enter 'y' or 'n")
        if ans.strip().lower() == 'n':
            self.stdout.write(self.style.NOTICE('Financial report data "UPDATE" canceled!'))
            return

        # Get all stock objects and store them in a dictionary
        stocks = {stock.ticker: stock for stock in Stock.objects.all()}

        # Loop over the stock list
        for index, row in tqdm(df_stock_list.iterrows(), desc="Updating financial report database..."):
            # Get symbol from Stock table
            symbol = row['Symbol']
            stock = stocks.get(symbol)
            if not stock:
                continue

            financials = yf.Ticker(symbol).quarterly_financials
            update_reports(financials, stock, FinancialReport)

            balance_sheet = yf.Ticker(symbol).quarterly_balance_sheet
            update_reports(balance_sheet, stock, BalanceSheet)

            cash_flow = yf.Ticker(symbol).quarterly_cash_flow
            update_reports(cash_flow, stock, CashFlow)

        # Success message
        self.stdout.write(self.style.SUCCESS("Financial data 'UPDATE' success!"))


def get_stock_list() -> pd.DataFrame:
    # Get stock list, source: https://www.nasdaq.com/market-activity/stocks/screener
    csv_file = os.path.join(settings.BASE_DIR, 'static', 'stock_list', 'nasdaq_screener.csv')

    # Filter out all stocks with '^' in symbol
    df = pd.read_csv(csv_file)
    df = df[~df['Symbol'].str.contains(r'\^')].reset_index(drop=True)

    return df


def delete_data_from_db_table(table: Type[Stock]):
    print("You are going to delete the stock data, it will delete its related data, "
          "like any price data and non price data, and it is irreversible."
          "\nAre you sure to delete all records? (y/n) ")
    while (ans := input('(y/n) ').strip().lower()) not in ('y', 'n'):
        print("Please enter 'y' or 'n")
    if ans.strip().lower() == 'n':
        return

    logging.warning("Deleting all records...")
    table.objects.all().delete()
    print("All stock data was deleted.")


def update_stock_list_db(stock_list: pd.DataFrame):
    # Prepare list to bulk update
    l_stocks = []

    # Loop over the stock list
    for index, row in tqdm(stock_list.iterrows(), desc="Updating stock table from database..."):
        # Initialize missing data
        ipo_year = 0 if np.isnan(row['IPO Year']) else row['IPO Year']
        market_cap = 0 if np.isnan(row['Market Cap']) else row['Market Cap']
        sector = 'Miscellaneous' if isinstance(row['Sector'], float) else row['Sector'].strip()
        industry = 'Miscellaneous' if isinstance(row['Industry'], float) else row['Industry'].strip()

        # Create or update Stock
        stock, created = Stock.objects.get_or_create(ticker=row['Symbol'].strip())
        stock.name = row['Name'].strip()
        stock.country = row['Country'].strip()
        stock.ipo_year = ipo_year
        stock.sector = sector
        stock.industry = industry
        stock.market_cap = market_cap

        # Add Stock instance to a list, pending to be bulk updated
        l_stocks.append(stock)

    # Bulk update
    fields = [field.name for field in Stock._meta.get_fields() if field.concrete and field.name != 'id']
    Stock.objects.bulk_update(l_stocks, fields=fields, batch_size=100)
    print("All stock basic data was updated.")


def update_candlestick_db(stock_list: pd.DataFrame):
    # Delete all existing data
    CandleStick.objects.all().delete()

    # Prepare list to bulk update
    l_candlesticks = []

    # Default downloading 3 years candlestick data
    start_date = dt.date.today() - dt.timedelta(days=365 * 3)
    stocks = {stock.ticker: stock for stock in Stock.objects.all()}

    # Download data for all stocks at once
    candlestick_data = {ticker: yf.download(ticker, start=start_date) for ticker in
                        stock_list['Symbol'].unique().tolist()}

    # Create candlestick objects in bulk
    for ticker, stock_data in tqdm(candlestick_data.items(), desc="Updating candlestick table from database..."):
        # Drop multiple columns 'Ticker'
        stock_data.columns = stock_data.columns.droplevel('Ticker')

        stock = stocks.get(ticker)
        if stock:
            for index, row in stock_data.iterrows():
                data = row.to_dict()
                # To turn 'Adj Close' to 'adj_close' for all keys (to match for column format of CandleStick model)
                data = {key.replace(' ', '_').lower(): value for key, value in data.items()}
                candlestick = CandleStick(stock=stock, date=row.name, **data, )

                # Add to pending list
                l_candlesticks.append(candlestick)

    # Bulk create candlestick objects
    CandleStick.objects.bulk_create(l_candlesticks, batch_size=100, ignore_conflicts=True)
    print("All candlestick data was updated.")


def update_reports(report: pd.DataFrame,
                   stock: Stock,
                   model: Type[FinancialReport | BalanceSheet | CashFlow]):
    # Prepare list to bulk update
    report_list = []

    for date, report_data in report.to_dict().items():
        # To turn 'Total Revenue' to 'TotalRevenue' for all keys (to match for column format of relevant model)
        data = {key.replace(' ', ''): value for key, value in report_data.items()}

        report, created = model.objects.get_or_create(stock=stock, date=date)
        [setattr(report, key, 0 if np.isnan(value) else value) for key, value in data.items()]
        report_list.append(report)

    fields_to_update = [field.name for field in model._meta.get_fields() if field.name != 'id']
    model.objects.bulk_update(report_list, fields=fields_to_update, batch_size=100)
