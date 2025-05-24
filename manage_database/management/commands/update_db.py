import datetime
from django.core.management.base import BaseCommand
from django.db import transaction
from InvestmentWeb.settings import STATICFILES_DIRS
import json
from manage_database.models import (
    Stock,
    CandleStick,
    IncomeStatement,
    BalanceSheet,
    CashFlow,
    GAAP_TO_READABLE_NAME_INCOMESTATEMENT,
    GAAP_TO_READABLE_NAME_BALANCESHEET,
    GAAP_TO_READABLE_NAME_CASHFLOW,
)
import numpy as np
import os
import pandas as pd
import requests
import time
from tqdm import tqdm
import yfinance as yf
import zipfile


def print_status(func):
    def wrapper(*args, **kwargs):
        args[0].stdout.write(
            args[0].style.NOTICE(f"\nStart function '{func.__name__}'...")
        )
        result = func(*args, **kwargs)
        args[0].stdout.write(
            args[0].style.SUCCESS(f"\nFinish function '{func.__name__}'.\n")
        )
        return result

    return wrapper


class Command(BaseCommand):
    help = "Update database tables 'IncomeStatement', 'BalanceSheet', 'CashFlow', 'CandleStick', 'Stock'."

    def add_arguments(self, parser):
        """
        Add arguments to the command.
        """
        # Update stock list
        parser.add_argument(
            "--update_stock_list",
            action="store_true",
            help="Update stock list from www.nasdaq.com.",
        )

        # Update financial reports
        parser.add_argument(
            "--update_reports",
            action="store_true",
            help="Update reports in database tables 'IncomeStatement', 'BalanceSheet', 'CashFlow'.",
        )

        # Update financial reports
        parser.add_argument(
            "--update_candlesticks",
            action="store_true",
            help="Update candlesticks (from yfinance)",
        )

        # Update all
        parser.add_argument(
            "--update_all",
            action="store_true",
            help="Update stock list, reports, and candlesticks.",
        )

    def handle(self, *args, **options):
        """
        Handle command options.
        """
        if options.get("update_all"):
            self._update_stock_list()
            self._update_reports()
            self._update_candlesticks()
        else:
            if options.get("update_stock_list"):
                self._update_stock_list()

            if options.get("update_reports"):
                self._update_reports()

            if options.get("update_candlesticks"):
                self._update_candlesticks()

    @print_status
    def _update_stock_list(self):
        """
        Read the local stock_list.csv and update its info to database.
        """
        # todo: download file programmatically
        self.stdout.write(
            self.style.WARNING(
                """
    [ ATTENTION ] Please make sure you have downloaded the stock list from
    https://www.nasdaq.com/market-activity/stocks/screener"
    and saved the file 'stock_list.csv' to '/static/assets/us_stocks_data'
"""
            )
        )

        # Validate file
        res = read_stock_list()
        if isinstance(res, str):
            self.stdout.write(self.style.ERROR(res))
            return

        # Delete and create
        with transaction.atomic():
            # Delete all stocks
            self.stdout.write(self.style.NOTICE("Deleting Stocks..."))
            Stock.objects.all().delete()

            # Add stocks to bulk-create list
            instances_to_create = []
            self.stdout.write(self.style.NOTICE("Adding Stocks..."))
            for index, row in tqdm(res.iterrows(), desc="Reading stock info..."):
                ticker = row["Symbol"].strip()
                name = row["Name"].strip()
                ipo_year = row["IPO Year"]
                country = row["Country"]
                sector = row["Sector"]
                industry = row["Industry"]
                market_cap = row["Market Cap"]

                # Default value for missing data
                ipo_year = 0 if np.isnan(ipo_year) else ipo_year
                country = "Unknown" if not isinstance(country, str) else country.strip()
                sector = (
                    "Miscellaneous" if not isinstance(sector, str) else sector.strip()
                )
                industry = (
                    "Miscellaneous"
                    if not isinstance(industry, str)
                    else industry.strip()
                )
                market_cap = 0 if not market_cap else market_cap

                # Create "Stock"
                stock = Stock(
                    ticker=ticker,
                    name=name,
                    country=country,
                    ipo_year=ipo_year,
                    sector=sector,
                    industry=industry,
                    market_cap=market_cap,
                )
                instances_to_create.append(stock)

            # Bulk-create
            self.stdout.write(self.style.NOTICE("Saving Stocks..."))
            Stock.objects.bulk_create(instances_to_create, batch_size=1000)

    @print_status
    def _update_reports(self):
        """
        Download financial reports from nasdaq's website and update database tables.
        """
        # Delete all files in 'companyfacts' folder
        companyfacts_dir = os.path.join(
            STATICFILES_DIRS[0], "assets", "us_stocks_data", "companyfacts"
        )
        # self.stdout.write(
        #     self.style.NOTICE("Deleting existings companyfacts.json files.")
        # )
        # delete_files(companyfacts_dir)

        # # Download companyfacts.zip
        # self.stdout.write(
        #     self.style.NOTICE("Downloading companyfacts.zip from Nasdaq's website...")
        # )
        # res = download_companyfacts()
        # if not res:
        #     self.stdout.write(
        #         self.style.ERROR(
        #             f"Error downloading companyfacts.zip from Nasdaq's website. ({res.content})"
        #         )
        #     )
        #     return

        # # Save and extract companyfacts.zip
        # self.stdout.write(self.style.NOTICE("Saving and extracting companyfacts..."))
        # companyfacts_zip = os.path.join(companyfacts_dir, "companyfacts.zip")
        # res = save_and_extract_zip(res, companyfacts_zip, companyfacts_dir)
        # if not res:
        #     self.stdout.write(
        #         self.style.ERROR("Error saving and extracting companyfacts.zip")
        #     )
        #     return

        # Get cik/ticker mapper
        cik_ticker_path = os.path.join(
            STATICFILES_DIRS[0],
            "assets",
            "us_stocks_data",
            "company_tickers.json",
        )
        df_cik_ticker_mapper = get_cik_ticker_mapper(
            download=False, file_path=cik_ticker_path
        )  # todo: 'download' should be True
        if not isinstance(df_cik_ticker_mapper, pd.DataFrame):
            self.stdout.write(
                self.style.ERROR("No existing CIK-Ticker mapper file found.")
            )
            return

        # Read companyfacts.json
        start = time.time()
        cik_list = df_cik_ticker_mapper["cik_str"].tolist()
        json_files = [f for f in os.listdir(companyfacts_dir) if f.endswith(".json")]
        for file in tqdm(json_files, desc="Reading companyfacts.json..."):
            # Read companyfacts.json
            with open(os.path.join(companyfacts_dir, file)) as f:
                # Get cik
                cik = int(file.split(".")[0].lstrip("CIK"))
                if cik not in cik_list:
                    # this entityName can not be searched from yfinance, probably delisted
                    continue

                # Get ticker
                ticker = df_cik_ticker_mapper.loc[
                    df_cik_ticker_mapper["cik_str"] == cik, "ticker"
                ].iloc[0]

                # Check stock existence
                try:
                    stock = Stock.objects.get(ticker=ticker)
                except:
                    # Save info provided by yfinance
                    stock = save_ticker_to_stock(ticker)
                    status = (
                        "Created" if stock else "Failed to obtain info from yfinance"
                    )
                    if stock is not None:
                        self.stdout.write(
                            self.style.NOTICE(
                                f"{ticker} not found in database. ({status})"
                            )
                        )
                    else:
                        continue

                # Catch decoding error from loading companyfacts json
                try:
                    companyfacts = json.load(f)
                except UnicodeDecodeError as e:
                    self.stdout.write(
                        self.style.ERROR(f"Error reading companyfacts.json: {e}")
                    )

                # Update reports
                update_reports_db(
                    stock,
                    BalanceSheet,
                    GAAP_TO_READABLE_NAME_BALANCESHEET,
                    companyfacts,
                )
                update_reports_db(
                    stock,
                    IncomeStatement,
                    GAAP_TO_READABLE_NAME_INCOMESTATEMENT,
                    companyfacts,
                )

        # Summary
        sec = int(time.time() - start)
        mins = sec // 60
        self.stdout.write(self.style.NOTICE(f"Time used: {mins} mins {sec % 60} s"))

    @print_status
    def _update_candlesticks(self):
        if not self._update_candlesticks_yfinance():
            self._update_candlesticks_other()

    @print_status
    def _update_candlesticks_yfinance(self) -> bool:
        start_date = datetime.date(datetime.date.today().year - 6, 1, 1)
        ticker_list = [t.ticker for t in Stock.objects.all()]
        batch_size = 150  # rate limit from yfinance
        
        for i in range(0, len(ticker_list), batch_size):
            # Set timer for 1 minute (rate limit from yfinance)
            request_time_start = time.time()
            self.stdout.write(
                self.style.NOTICE(
                    f"Getting candlesticks data from yfinance: {i} to {i+batch_size}"
                )
            )

            # Download data from yfinance
            tickers_batch = ticker_list[i : i + batch_size]
            data = yf.download(tickers=tickers_batch, start=start_date, progress=False)
            data.replace(np.nan, 0.01, inplace=True)

            with transaction.atomic():
                # Delete data from
                yf_tickers = data.columns.get_level_values(1).unique().tolist()
                CandleStick.objects.filter(stock__ticker=yf_tickers).delete()

                instances_to_create = []
                for ticker in yf_tickers:
                    # Get data for ticker
                    data_for_ticker = data.xs(ticker, axis=1, level=1)
                    stock = Stock.objects.get(ticker=ticker)

                    for index, row in data_for_ticker.iterrows():
                        # Gather info for Candlestick
                        kwargs = {
                            "stock": stock,
                            "date": row.name.date(),  # Yf uses date as index name
                            "open": row["Open"],
                            "high": row["High"],
                            "low": row["Low"],
                            "close": row["Close"],
                            "volume": row["Volume"],
                            "turnover": (row["High"] - row["Low"]) / 2 * row["Volume"],
                        }

                        # Append to bulk-create later
                        instances_to_create.append(CandleStick(**kwargs))
                
                # Bulk-create
                CandleStick.objects.bulk_create(instances_to_create)

            # Wait for the next minute
            if i > len(ticker_list) - batch_size:
                wait_time = max(60 - (time.time() - request_time_start), 0)
                self.stdout.write(self.style.NOTICE(f"Wait for the next batch : {wait_time} seconds"))
                time.sleep(wait_time)
        
        return True

    @print_status
    def _update_candlesticks_other(self) -> bool:
        pass


def read_stock_list() -> pd.DataFrame | str:
    """
    Read local 'stock_list.csv' file and return a pandas DataFrame or error string.
    """
    # Validate file path
    file_name = "stock_list.csv"
    file_path = os.path.join(STATICFILES_DIRS[0], "assets", "us_stocks_data", file_name)
    if not os.path.isfile(file_path):
        return f"File {file_name} not found."

    df = pd.read_csv(file_path)
    df = df[~df["Symbol"].isna()]
    df = df[df["Symbol"].str.len() <= 5]
    df = df[~df["Symbol"].str.contains(r"\^")]
    df = df[~df["Symbol"].str.contains("/")]

    return df.reset_index()


def delete_files(folder: os.path):
    """
    Remove all files in folder.
    """
    [
        os.remove(os.path.join(folder, file))
        for file in os.listdir(folder)
        if os.path.isfile(os.path.join(folder, file))
    ]


def download_companyfacts() -> requests.models.Response | str:
    """
    Download companyfacts from us sec website.
    """
    header = {
        "Connection": "close",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0;)",
        "X-Requested-With": "XMLHttpRequest",
        "Accept": "application/json, text/javascript",
    }
    url = "https://www.sec.gov/Archives/edgar/daily-index/xbrl/companyfacts.zip"
    try:
        res = requests.get(url, stream=True, headers=header)
        if not res.ok:
            return res

        return res
    except Exception as e:
        return e


def save_and_extract_zip(res, file_path, dir_path) -> bool:
    """
    Save zip file and extract all.
    """
    # Write
    with open(file_path, mode="wb") as file:
        for chunk in res.iter_content(chunk_size=10 * 1024):
            file.write(chunk)

    # Extract
    if zipfile.is_zipfile(file_path):
        with zipfile.ZipFile(file_path, "r") as zip_ref:
            zip_ref.extractall(dir_path)
        return True
    else:
        return False


def get_cik_ticker_mapper(download: bool, file_path: os.path) -> pd.DataFrame | None:
    """
    Download cik/ticker mapper from sec.gov, if fail, get existing file from static folder.
    """
    if download:
        header = {
            "Connection": "close",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0;)",
            "X-Requested-With": "XMLHttpRequest",
            "Accept": "application/json, text/javascript",
        }
        try:
            res = requests.get(
                "https://www.sec.gov/files/company_tickers.json", headers=header
            )
            if not res.ok:
                return

            # Save it to local for backup
            with open(file_path, "wb") as file:
                for chunk in res.iter_content(chunk_size=10 * 1024):
                    file.write(chunk)

        except Exception as e:
            print(
                f"Error downloading cik/ticker mapper: {e}, load existing file instead"
            )

    try:
        df = get_existing_cik_ticker_file(file_path)
        if not isinstance(df, pd.DataFrame):
            return

        return df

    except Exception as e:
        print(f"Error loading existing cik/ticker mapper: {e}")
        return


def get_existing_cik_ticker_file(cik_ticker_path: os.path) -> pd.DataFrame | None:
    """
    Read cik/tikcer mapper file from static folder.
    """
    if os.path.exists(cik_ticker_path):
        with open(cik_ticker_path) as f:
            return pd.read_json(f).T

    return


def save_ticker_to_stock(ticker: str) -> Stock | None:
    """
    Get stock info from yfinance and save it to database.
    """
    res = yf.Search(ticker).quotes
    if res:
        stock = Stock.objects.create(
            ticker=ticker,
            name=res[0].get("shortname"),
            sector=res[0].get("sector"),
            industry=res[0].get("industry"),
        )
        stock.save()

        return stock

    return


def update_reports_db(
    stock: Stock,
    model: IncomeStatement | BalanceSheet | CashFlow,
    gaap_to_readable_name: dict,
    companyfacts: dict,
):
    # Validate data
    try:
        us_gaap = companyfacts["facts"]["us-gaap"]
    except:
        return

    # Extract necessary gaap
    required_gaap = set(gaap_to_readable_name.keys()).intersection(set(us_gaap))
    df = pd.DataFrame()
    for gaap in required_gaap:
        units = us_gaap[gaap].get("units")
        if not units:
            continue

        for k, v in units.items():
            for i in v:
                filed = i.get("filed")
                period = i.get("fp")
                if not filed or not period:
                    continue
                df.loc[gaap_to_readable_name.get(gaap), filed + " " + period] = i.get(
                    "val"
                )

    if df.empty:
        return

    # Filter out same filed date with report period 'FY' or older quarter. 'Sorted' do this thing.
    validate_cols = []
    required_cols = []
    for col in sorted(df.columns):
        date_str = col.split(" ")[0]
        if date_str not in validate_cols:
            validate_cols.append(date_str)
            required_cols.append(col)
        else:
            required_cols[-1] = col
    df = df[list(required_cols)]

    # Bulk create
    df.replace(np.nan, 0, inplace=True)
    create_instances = []
    for col in df.columns:
        file_date = col.split(" ")[0]
        # Ignore existing data
        if not model.objects.filter(stock=stock, FileDate=file_date).exists():
            create_instances.append(
                model(stock=stock, FileDate=file_date, **df[col].to_dict())
            )

    model.objects.bulk_create(create_instances, batch_size=1000)
