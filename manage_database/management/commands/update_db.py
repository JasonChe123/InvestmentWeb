import datetime as dt
from django.conf import settings
from django.contrib.staticfiles import finders
from django.core.management.base import BaseCommand, CommandError
from InvestmentWeb.settings import STATICFILES_DIRS
from manage_database.models import Stock, CandleStick, IncomeStatement, BalanceSheet, CashFlow
import numpy as np
import pandas as pd
import os
import requests
from tqdm import tqdm


class Command(BaseCommand):
    help = "Update database: 'Financial Reports', 'Candlesticks' and 'Stock List'"

    def add_arguments(self, parser):
        # Update stock list
        parser.add_argument(
            '--update_stock_list',
            action='store_true',
            help='Update stock list from www.nasdaq.com.',
        )

        # Update candlesticks
        parser.add_argument(
            '--update_candlesticks',
            action='store_true',
            help='Update candlesticks data from yfinance.',
        )

        # Update financial reports
        parser.add_argument(
            '--update_reports',
            action='store_true',
            help='Update financial reports from www.sec.gov.',
        )
    
    def handle(self, *args, **options):
        if options.get('update_stock_list'):
            self._update_stock_list()
        
        if options.get('update_candlesticks'):
            self._update_candlesticks()
        
        if options.get('update_reports'):
            self._update_reports()
                
        # Read company 'cik to tickers' mapping
        # headers = {'User-Agent': 'Mozilla/5.0'}
        # tickers_json = requests.get('https://www.sec.gov/files/company_tickers.json', headers=headers).json()
        # file_path = 'assets/us_stocks_data/company_tickers.json'
        # df = pd.read_json(finders.find(file_path)).T

        # self.stdout.write(self.style.SUCCESS("Hello World!"))
        # a = 1
        
        self.stdout.write(self.style.SUCCESS(f"Finished '{os.path.basename(__file__).split('.')[0]}' command!"))
    
    def _update_stock_list(self):
        def get_stock_list():
            # Read csv file
            stock_list_path = 'assets/us_stocks_data/stock_list.csv'
            if not finders.find(stock_list_path):
                self.stdout.write(self.style.ERROR("File 'stock_list.csv' not found."))
                return False, None
            
            # Filter out all symbol with '^' and NaN
            df = pd.read_csv(finders.find(stock_list_path))
            df = df[~df['Symbol'].isna()]
            df = df[~df['Symbol'].str.contains(r'\^')].reset_index(drop=True)
            
            return True, df

        # Start message
        self.stdout.write(self.style.NOTICE("Start updating stock list..."))
        self.stdout.write(self.style.WARNING("Please make sure you have downloaded the updated stock list from "
                                             "'https://www.nasdaq.com/market-activity/stocks/screener'"
                                             "and saved the file to '/static/assets/us_stocks_data/stock_list.csv'"))

        # Prepare list to bluk update
        res, df = get_stock_list()
        if not res:
            self.stdout.write(self.style.NOTICE("Fail updating stock list."))
            return
        
        # Update stock list
        l_stocks = []
        for index, row in tqdm(df.iterrows(), desc="Updating database table 'Stock'..."):
            # Unpack data
            ticker = row['Symbol'].strip()
            name = row['Name'].strip()
            ipo_year = row['IPO Year']
            country = row['Country']
            sector = row['Sector']
            industry = row['Industry']
            
            # Initialize missing data
            ipo_year = 0 if np.isnan(ipo_year) else ipo_year
            country = 'Unknown' if not isinstance(country, str) else country.strip()
            sector = 'Miscellaneous' if not isinstance(sector, str) else sector.strip()
            industry = 'Miscellaneous' if not isinstance(industry, str) else industry.strip()

            # Create or update
            stock, created = Stock.objects.get_or_create(ticker=ticker)
            if all([stock.name == name,
                    stock.country == country,
                    stock.ipo_year == ipo_year,
                    stock.sector == sector,
                    stock.industry == industry]):
                continue
            stock.name = name
            stock.country = country
            stock.ipo_year = ipo_year
            stock.sector = sector
            stock.industry = industry
            
            # Add stock instance to a list, pending to be bulk updated
            l_stocks.append(stock)

        # Bulk update
        if len(l_stocks) > 0:
            self.stdout.write(self.style.NOTICE(f"Updating stock: {[s.ticker for s in l_stocks[:5]]}... total: {len(l_stocks)} stocks"))
            fields = [field.name for field in Stock._meta.get_fields() if field.concrete and field.name != 'id']
            Stock.objects.bulk_update(l_stocks, fields=fields, batch_size=100)
        else:
            self.stdout.write(self.style.NOTICE("All stocks are already update."))

        # Finish message
        self.stdout.write(self.style.NOTICE("Finish updating stock list."))

    def _update_candlesticks(self):
        # Start message
        self.stdout.write(self.style.NOTICE("Start updating candlesticks..."))

        # Default downloading 5 years candlestick data
        start_date = dt.date.today() - dt.timedelta(days=365*5)

        # Init stock list
        stocks = {stock.ticker for stock in Stock.objects.all()}
        
        # Finish message
        self.stdout.write(self.style.NOTICE("Finished updating candlesticks."))

    def _update_reports(self):
        pass
