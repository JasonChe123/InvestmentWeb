import datetime as dt
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q
from InvestmentWeb.settings import STATICFILES_DIRS
import json
import logging
from manage_database.models import (
    Stock,
    CandleStick,
    IncomeStatement,
    BalanceSheet,
    CashFlow,
)
from manage_database.models import (
    GAAP_TO_READABLE_NAME_BALANCE_SHEET,
    GAAP_TO_READABLE_NAME_CASH_FLOW,
    GAAP_TO_READABLE_NAME_INCOME_STATEMENT,
)
import numpy as np
import os
import pandas as pd
import requests
import time
from tqdm import tqdm
from typing import Type
import yfinance as yf
import zipfile


class Command(BaseCommand):
    help = "Update database: 'Financial Reports', 'Candlesticks' and 'Stock List'"

    def add_arguments(self, parser):
        # Update stock list
        parser.add_argument(
            "--update_stock_list",
            action="store_true",
            help="Update stock list from www.nasdaq.com.",
        )

        # Update candlesticks
        parser.add_argument(
            "--update_candlesticks",
            action="store_true",
            help="Update candlesticks data from yfinance.",
        )

        # Update financial reports
        parser.add_argument(
            "--update_reports",
            action="store_true",
            help="Update financial reports from www.sec.gov.",
        )

    def handle(self, *args, **options):
        if options.get("update_stock_list"):
            self._update_stock_list()

        if options.get("update_candlesticks"):
            self._update_candlesticks()
            # self._update_candlesticks_by_ibapi()

        if options.get("update_reports"):
            self._update_reports()

        self.stdout.write(
            self.style.SUCCESS(
                f"Finished '{os.path.basename(__file__).split('.')[0]}' command!"
            )
        )

    def _update_stock_list(self):
        def get_stock_list() -> bool | pd.DataFrame:
            # Read csv file
            stock_list_path = os.path.join(
                STATICFILES_DIRS[0], "assets", "us_stocks_data", "stock_list.csv"
            )
            if not os.path.isfile(stock_list_path):
                self.stdout.write(self.style.ERROR("File 'stock_list.csv' not found."))
                return False, None

            # Filter out all symbol with '^' and NaN
            df = pd.read_csv(stock_list_path)
            df = df[~df["Symbol"].isna()]
            df = df[df["Symbol"].str.len() < 5]
            df = df[~df["Symbol"].str.contains(r"\^")]
            df = df[~df["Symbol"].str.contains("/")].reset_index(drop=True)

            return True, df

        # Start message
        self.stdout.write(self.style.NOTICE("Start updating stock list..."))
        self.stdout.write(
            self.style.WARNING(
                "[ ATTENTION ] Please make sure you downloaded the stock list from "
                "\n    https://www.nasdaq.com/market-activity/stocks/screener"
                "\n    and saved the file 'stock_list.csv' to '/static/assets/us_stocks_data/'"
            )
        )

        # Get stock list
        res, df = get_stock_list()
        if not res:
            self.stdout.write(self.style.NOTICE("Fail updating stock list."))
            return

        # Update stock list
        l_stocks = []
        for index, row in tqdm(
            df.iterrows(), desc="Updating Stock table from database..."
        ):
            # Unpack data
            ticker = row["Symbol"].strip()
            name = row["Name"].strip()
            ipo_year = row["IPO Year"]
            country = row["Country"]
            sector = row["Sector"]
            industry = row["Industry"]
            market_cap = row['Market Cap']

            # Deal with missing data
            ipo_year = 0 if np.isnan(ipo_year) else ipo_year
            country = "Unknown" if not isinstance(country, str) else country.strip()
            sector = "Miscellaneous" if not isinstance(sector, str) else sector.strip()
            industry = (
                "Miscellaneous" if not isinstance(industry, str) else industry.strip()
            )
            market_cap = 0 if not market_cap else market_cap

            # Create or update
            stock, created = Stock.objects.get_or_create(ticker=ticker)

            # If no change
            if all(
                [
                    stock.name == name,
                    stock.ipo_year == ipo_year,
                    stock.country == country,
                    stock.sector == sector,
                    stock.industry == industry,
                    stock.market_cap == market_cap,
                ]
            ):
                continue

            # If new or changes, then update it
            stock.name = name
            stock.ipo_year = ipo_year
            stock.country = country
            stock.sector = sector
            stock.industry = industry
            stock.market_cap = market_cap

            # Add stock instance to a list, pending to be bulk updated
            l_stocks.append(stock)

        # Bulk update
        if len(l_stocks) > 0:
            self.stdout.write(
                self.style.NOTICE(
                    f"Updating stock: {[s.ticker for s in l_stocks[:5]]}... total: {len(l_stocks)} stocks"
                )
            )
            fields = [
                field.name
                for field in Stock._meta.get_fields()
                if field.concrete and field.name != "id"
            ]
            Stock.objects.bulk_update(l_stocks, fields=fields, batch_size=100)
        else:
            self.stdout.write(self.style.NOTICE("All stocks are already update."))

        # Finish message
        self.stdout.write(self.style.NOTICE("Finish updating stock list."))

    def _update_candlesticks(self):
        # Start message
        self.stdout.write(self.style.NOTICE("Start updating candlesticks..."))

        # Default downloading 5 years candlestick data
        start_date = dt.date.today() - dt.timedelta(days=365 * 5)

        # Init stock list
        stocks = {stock.ticker: stock for stock in Stock.objects.all().exclude(ticker="SFB")}
        ticker_list = list(stocks.keys())
        batch_size = 150

        for i in range(0, len(ticker_list), batch_size):
            start_time = time.time()

            # Progress message
            time_now = dt.datetime.strftime(dt.datetime.now(), "%Y-%m-%d %H:%M:%S")
            message = f"Processing {i}-{min(len(ticker_list), i + batch_size)} of {len(ticker_list)} stocks..."
            self.stdout.write(self.style.NOTICE(f"[ {time_now} ] {message}"))

            # Download data from yfinance
            batch = ticker_list[i : i + batch_size]
            data = yf.download(tickers=batch, start=start_date, progress=False)

            with transaction.atomic():
                # Delete from database
                yf_tickers = data.columns.get_level_values(1).unique().tolist()
                CandleStick.objects.filter(Q(stock__ticker__in=yf_tickers)).delete()

                # Update candlesticks
                l_candlesticks = []
                for ticker in yf_tickers:
                    data_for_ticker = data.xs(ticker, axis=1, level=1)
                    for index, row in data_for_ticker.iterrows():
                        stock = stocks.get(ticker)
                        
                        # Validate stock before create CandleStick
                        if not stock:
                            logging.info(f"{ticker} not found from database, Please.")
                            continue
                        
                        date = row.name  # yf uses date as index name
                        date = date.replace(tzinfo=dt.timezone.utc)
                        open_ = None if np.isnan(row["Open"]) else row["Open"].round(2)
                        high = None if np.isnan(row["High"]) else row["High"].round(2)
                        low = None if np.isnan(row["Low"]) else row["Low"].round(2)
                        close = None if np.isnan(row["Close"]) else row["Close"].round(2)
                        volume = None if np.isnan(row["Volume"]) else row["Volume"]
                        
                        candlestick = CandleStick(
                            stock=stock,
                            date=date,
                            open=open_,
                            high=high,
                            low=low,
                            close=close,
                            volume=volume,
                        )

                        l_candlesticks.append(candlestick)

                # Bulk create
                CandleStick.objects.bulk_create(l_candlesticks, ignore_conflicts=True)

            # Wait to avoid hitting the rate limit of yfinance
            if len(ticker_list) - i <= batch_size:
                wait_time = 60 - (time.time() - start_time)
                if wait_time > 0:
                    time.sleep(wait_time)

        # Finish message
        self.stdout.write(self.style.NOTICE("Finished updating candlesticks."))

    def _update_reports(self):
        def get_column_name(data: dict) -> str:
            """
            Return flied_date + fiscal_period as a column name.
            """
            if not data.get("filed"):
                return

            file_date = data.get("filed")
            fiscal_period = data.get("fp")

            return " ".join([file_date, str(fiscal_period)])

        def update_data(gaap_to_readable_name, companyfact) -> pd.DataFrame:
            df = pd.DataFrame(
                index=["StartDate", "EndDate", "FiscalPeriod"]
                + list(gaap_to_readable_name.values())
            )

            # Get share issued
            share_issued = "EntityCommonStockSharesOutstanding"
            try:
                share_issued_data = companyfact["facts"]["dei"][share_issued]
                for data in share_issued_data["units"]["shares"]:
                    col = get_column_name(data)
                    if not col:
                        return df

                    df.at["EndDate", col] = data.get("end")
                    df.at["StartDate", col] = data.get("start")
                    df.at["ShareIssued", col] = data.get("val")
            except (KeyError, AttributeError, TypeError) as e:
                # self.stdout.write(self.style.ERROR(f"{companyfact.keys()}: {e}"))
                pass

            # Get other data
            facts = companyfact.get("facts")
            if not facts:
                return df

            gaap_data = facts.get("us-gaap")
            if not gaap_data:
                return df

            us_gaaps = companyfact["facts"]["us-gaap"]
            for gaap in set(gaap_to_readable_name.keys()).intersection(set(us_gaaps)):
                # if gaap in us_gaaps:
                units = us_gaaps[gaap]["units"]
                index = gaap_to_readable_name[gaap]
                for unit in units.keys():
                    for data in units[unit]:
                        col = get_column_name(data)
                        df.at["StartDate", col] = data.get("start")
                        df.at["EndDate", col] = data.get("end")
                        df.at["FiscalPeriod", col] = data.get("fp")
                        df.at[index, col] = data.get("val")

            return df.reindex(sorted(df.columns, reverse=True), axis=1)

        def update_report_db(
            report_df: pd.DataFrame,
            stock: Stock,
            model: Type[IncomeStatement | BalanceSheet | CashFlow],
            gaap_to_readable_name: dict,
        ):
            """
            Update database.
            """
            # Report list to bulk update
            report_list = []

            # Append reports to report list
            for col in report_df.columns:
                # Get or create record by stock, file_date and fiscal_period
                filed_date = col.split(" ")[0]
                fiscal_period = report_df[col]["FiscalPeriod"]
                try:
                    report, created = model.objects.get_or_create(
                        stock=stock,
                        FileDate=filed_date,
                        FiscalPeriod=fiscal_period,
                    )
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(
                            f"Error updating database, Ticker: {stock.ticker}, {model.__name__}, {e}"
                        )
                    )
                    return

                # Update 'StartDate' and 'EndDate'
                report.StartDate = report_df.at["StartDate", col]
                report.EndDate = report_df.at["EndDate", col]

                # report.StartDate = report_df[col].loc["StartDate"]
                # report.EndDate = report_df[col].loc["EndDate"]

                # Update other gaap values
                (
                    setattr(report, name, report_df.at[name, col])
                    for name in gaap_to_readable_name.values()
                )

                # for name in gaap_to_readable_name.values():
                #     value = report_df[col].loc[name]
                #     setattr(report, name, None if np.isnan(value) else value)

                # Append to report_list
                report_list.append(report)

            # Get fields to update
            fields_to_update = [
                field.name for field in model._meta.get_fields() if field.name != "id"
            ]

            # Bulk update
            model.objects.bulk_update(
                report_list, fields=fields_to_update, batch_size=100
            )

        def delete_downloaded_data():
            """
            Remove all files from dir_companyfacts.
            """
            for file_name in os.listdir(dir_companyfacts):
                file = os.path.join(dir_companyfacts, file_name)
                os.remove(file)

        def get_existing_cik_ticker_file():
            with open(
                os.path.join(
                    STATICFILES_DIRS[0],
                    "assets",
                    "us_stocks_data",
                    "company_tickers.json",
                )
            ) as f:
                return pd.read_json(f).T

        def add_important_indicators_to_income_statement(df: pd.DataFrame):
            if df.empty:
                return

            df.loc["GrossProfit"] = df.loc["TotalRevenue"] - df.loc["CostOfSales"]
            df.loc["TotalExpenses"] = df.loc["TotalRevenue"] - df.loc["OperatingIncome"]
            df.loc["InterestExpenses"] = (
                df.loc["InterestIncome"] - df.loc["InterestNet"]
            )
            df.loc["EBIT"] = (
                df.loc["TotalRevenue"]
                - df.loc["CostOfSales"]
                - df.loc["OperatingSellingGeneralAndAdministrativeExpenses"]
            )

        def add_important_indicatros_to_balance_sheet(df: pd.DataFrame):
            if df.empty:
                return

            df.loc["TotalNonCurrentAssets"] = (
                df.loc["TotalAssets"] - df.loc["TotalCurrentAssets"]
            )
            df.loc["TotalNonCurrentLiabilities"] = (
                df.loc["TotalLiabilitiesRedeemableNoncontrollingInterestAndEquity"]
                - df.loc["TotalCurrentLiabilities"]
                - df.loc["TotalEquity"]
            )
            df.loc["TotalLiabilities"] = (
                df.loc["TotalCurrentLiabilities"] + df.loc["TotalNonCurrentLiabilities"]
            )
            df.loc["TotalCapitalization"] = (
                df.loc["TotalShareholdersEquity"] + df.loc["LongTermDebt"]
            )
            df.loc["NetTangibleAssets"] = (
                df.loc["TotalShareholdersEquity"] - df.loc["Goodwill"]
            )
            df.loc["NetWorkingCapital"] = (
                df.loc["TotalCurrentAssets"] - df.loc["TotalCurrentLiabilities"]
            )
            df.loc["InvestedCapital"] = (
                df.loc["TotalShareholdersEquity"]
                + df.loc["LongTermDebt"]
                - df_cash_flow.loc["FinancingCashFlow"]  # data from 'Cash Flow'
            )
            df.loc["NetDebt"] = df.loc["TotalDebt"] - df.loc["EndCashPosition"]

        def add_important_indicatros_to_cash_flow(df: pd.DataFrame):
            if df.empty:
                return

            df.loc["CapitalExpenditures"] = (
                df.loc["PropertyAndEquipmentNet"]
                - df.loc["PropertyAndEquipmentNet"].shift(-1)
                - df.loc["DepreciationAndAmortization"]
            )
            df.loc["FreeCashFlow"] = (
                df.loc["OperatingCashFlow"] + df.loc["CapitalExpenditures"]
            )

        # Start message
        self.stdout.write(self.style.NOTICE("Start updating financial reports..."))

        # Define zip-file path for companyfacts
        dir_companyfacts = os.path.join(
            STATICFILES_DIRS[0], "assets", "us_stocks_data", "companyfacts"
        )
        zip_file_path = os.path.join(dir_companyfacts, "companyfacts.zip")

        # # Delete all files in dir_companyfacts
        delete_downloaded_data()

        # Prepare header for requests module
        header = {
            "Host": "www.sec.gov",
            "Connection": "close",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "X-Requested-With": "XMLHttpRequest",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.163 Safari/537.36",
        }

        # Downlaod zip-file for companyfacts
        try:
            url = "https://www.sec.gov/Archives/edgar/daily-index/xbrl/companyfacts.zip"
            res = requests.get(url, stream=True, headers=header)
            if not res.ok:
                self.stdout.write(
                    self.style.ERROR(
                        f"Error downloading from www.sec.gov\n{res.content}"
                    )
                )
                self.stdout.write(self.style.NOTICE("Exit updating financial reports"))
                return
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Error downloading reports from SEC website: {e}")
            )
            self.stdout.write(self.style.NOTICE("Exit updating financial reports"))
            return

        # Save zip-file
        with open(zip_file_path, mode="wb") as file:
            for chunk in res.iter_content(chunk_size=10 * 1024):
                file.write(chunk)

        # Extract companyfacts from zip-file
        if zipfile.is_zipfile(zip_file_path):
            with zipfile.ZipFile(zip_file_path, mode="r") as archive:
                archive.extractall(dir_companyfacts)
        else:
            self.stdout.write(
                self.style.ERROR("File 'companyfacts.zip' is not a zip file")
            )
            self.stdout.write(self.style.NOTICE("Exit updating financial reports"))
            return

        # Download cik/ticker mapper
        try:
            res = requests.get(
                "https://www.sec.gov/files/company_tickers.json", headers=header
            )
            df_cik_ticker_mapper = pd.DataFrame(res.json()).T
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(
                    f"Error downloading 'company_tickers.json', load existing file instead."
                )
            )
            try:
                df_cik_ticker_mapper = get_existing_cik_ticker_file()
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(
                        f"Error loading existing 'company_tickers.json': {e}"
                    )
                )
                self.stdout.write(self.style.NOTICE("Exit updating financial reports"))
                return

        # Create ticker list from database
        stock_list = {s.ticker: s for s in Stock.objects.all()}

        # Filter cik/ticker mapper by ticker list
        df_cik_ticker_mapper = df_cik_ticker_mapper[
            df_cik_ticker_mapper["ticker"].isin(stock_list.keys())
        ]

        # Create dict for cik/ticker mapper
        l_cik = df_cik_ticker_mapper["cik_str"].tolist()
        l_ticker = df_cik_ticker_mapper["ticker"].tolist()
        dict_cik_ticker_mapper = {cik: ticker for cik, ticker in zip(l_cik, l_ticker)}

        # Read companyfacts
        for file in tqdm(os.listdir(dir_companyfacts), desc="Updating reports..."):
            # Check if companyfacts in stock_list
            file_name, file_type = file.split(".")
            if (
                file_type == "json"
                and int(file_name.lstrip("CIK")) not in dict_cik_ticker_mapper.keys()
            ):
                continue

            with open(os.path.join(dir_companyfacts, file)) as f:
                # Load companyfacts.json
                try:
                    companyfacts = json.load(f)
                except UnicodeDecodeError as e:
                    # self.stdout.write(
                    #     self.style.ERROR(f"Error reading file: {file}: {e}")
                    # )
                    continue

                # Get ticker by cik from (companyfacts or filename)
                cik = companyfacts.get("cik")
                cik = int(cik) if cik else int(file_name.lstrip("CIK"))
                ticker = dict_cik_ticker_mapper.get(cik)

                # Extract necessary data from companyfacts
                df_income_statement = update_data(
                    GAAP_TO_READABLE_NAME_INCOME_STATEMENT, companyfacts
                )
                df_balance_sheet = update_data(
                    GAAP_TO_READABLE_NAME_BALANCE_SHEET, companyfacts
                )
                df_cash_flow = update_data(
                    GAAP_TO_READABLE_NAME_CASH_FLOW, companyfacts
                )

                # Add other important financial indicators
                add_important_indicators_to_income_statement(df_income_statement)
                add_important_indicatros_to_balance_sheet(df_balance_sheet)
                add_important_indicatros_to_cash_flow(df_cash_flow)

                # Update database
                stock = stock_list.get(ticker)
                update_report_db(
                    df_income_statement,
                    stock,
                    IncomeStatement,
                    GAAP_TO_READABLE_NAME_INCOME_STATEMENT,
                )
                update_report_db(
                    df_balance_sheet,
                    stock,
                    BalanceSheet,
                    GAAP_TO_READABLE_NAME_BALANCE_SHEET,
                )
                update_report_db(
                    df_cash_flow, stock, CashFlow, GAAP_TO_READABLE_NAME_CASH_FLOW
                )

        # # Delete downloaded files
        delete_downloaded_data()

        # Finish message
        self.stdout.write(self.style.NOTICE("Finish updating financial reports"))
