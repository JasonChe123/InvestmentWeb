from calendar import monthrange
from concurrent.futures.thread import ThreadPoolExecutor
import csv
import datetime as dt
from dateutil.relativedelta import relativedelta
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Q
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render
from django.template.context_processors import csrf
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.http import require_POST
import json
import logging
from manage_database.models import (
    Stock,
    IncomeStatement,
    BalanceSheet,
    CashFlow,
    CandleStick,
)
import numpy as np
import pandas as pd
import pdb
import re
from typing import Tuple
from .models import LongShortEquity


# todo:
# 1. Order: Type: REL, Price 5% from previous close, allow outside RTH, Aux. Price 0.01, round qty to nearest decimal if possible
# 2. Ignore any order if its amount is less $100


market_cap = {
    "Mega (>$200B)": 200_000_000_000,
    "Large ($10B-$200B)": range(10_000_000_000, 200_000_000_001),
    "Medium ($2B-$10B)": range(2_000_000_000, 10_000_000_001),
    "Small ($300M-$2B)": range(300_000_000, 2_000_000_001),
    "Micro ($50M-$300M)": range(50_000_000, 300_000_001),
    "Nano (<$50M)": range(0, 50_000_001),
}
sectors = [
    "Basic Materials",
    "Consumer Discretionary",
    "Consumer Staples",
    "Energy",
    "Finance",
    "Health Care",
    "Industrials",
    "Miscellaneous",
    "Real Estate",
    "Technology",
    "Telecommunications",
    "Utilities",
]


@method_decorator(login_required, name="dispatch")
class BackTestView(View):
    def __init__(self):
        super().__init__()
        self.market_cap = market_cap
        self.backtest_years = [i for i in range(1, 6)]
        self.pos_hold = [50, 40, 30, 20, 10]
        self.min_stock_price = [1, 2, 3, 4, 5, 10]
        self.sectors = {sector: 0 for sector in sectors}
        self.long_total = 0
        self.short_total = 0
        self.longshort_annualized = 0

        # Get a list of income statement data
        self.income_statement = sorted(
            [
                separate_words(field.name)
                for field in IncomeStatement._meta.get_fields()
                if field.concrete
                and field.name
                not in (
                    "id",
                    "stock",
                    "FileDate",
                    "StartDate",
                    "EndDate",
                    "FiscalPeriod",
                )
            ]
        )

        # Get a list of balance sheet data
        self.balance_sheet_data = sorted(
            [
                separate_words(field.name)
                for field in BalanceSheet._meta.get_fields()
                if field.concrete
                and field.name
                not in (
                    "id",
                    "stock",
                    "FileDate",
                    "StartDate",
                    "EndDate",
                    "FiscalPeriod",
                )
            ]
        )

        # Get a list of cash flow data
        self.cash_flow_data = sorted(
            [
                separate_words(field.name)
                for field in CashFlow._meta.get_fields()
                if field.concrete
                and field.name
                not in (
                    "id",
                    "stock",
                    "FileDate",
                    "StartDate",
                    "EndDate",
                    "FiscalPeriod",
                )
            ]
        )

        # Setup html context
        self.html_context = {
            "methods_income_statement": self.income_statement,
            "methods_balance_sheet": self.balance_sheet_data,
            "methods_cash_flow": self.cash_flow_data,
            "market_cap": self.market_cap.keys(),
            "sectors": self.sectors,
            "all_stocks_num": 0,
            "backtest_years": self.backtest_years,
            "pos_hold": self.pos_hold,
            "min_stock_price": self.min_stock_price,
        }

    def get(self, request):
        # Default parameters
        self.html_context["selected_market_cap"] = list(self.market_cap.keys())[:-1]
        self.html_context["selected_backtest_years"] = 1
        self.html_context["selected_pos_hold"] = 10
        self.html_context["selected_min_stock_price"] = 10
        self.html_context["selected_sorting_method"] = "Descending"
        self.html_context["csrf_token"] = csrf(request)["csrf_token"]

        return render(request, "long_short/index.html", self.html_context)

    def post(self, request):
        """Start backtesting"""
        # Get user's inputs
        market_cap = request.POST.getlist("market-cap")
        method = request.POST.get("selected-method").rstrip("+-*/")
        sectors = [s for s in self.sectors if request.POST.get(s)]
        backtest_years = int(request.POST.get("backtest_years"))
        pos_hold = int(request.POST.get("pos_hold"))
        min_stock_price = int(request.POST.get("min_stock_price"))
        sorting_method = request.POST.get("sorting_method")

        # Add to context
        self.html_context.update(
            {
                "selected_market_cap": market_cap,
                "selected_method": method,
                "selected_sectors": sectors,
                "selected_backtest_years": backtest_years,
                "selected_pos_hold": pos_hold,
                "selected_min_stock_price": min_stock_price,
                "selected_sorting_method": sorting_method,
            }
        )

        # Check input validity
        if not market_cap:
            messages.warning(request, "Please select Market Cap.")
            return render(request, "long_short/index.html", self.html_context)
        if not sectors:
            messages.warning(request, "Please select Sectors.")
            return render(request, "long_short/index.html", self.html_context)
        if not method:
            messages.warning(request, "Please select Method.")
            return render(request, "long_short/index.html", self.html_context)
        if method.count("(") != method.count(")"):
            messages.warning(request, "Your method is in-valid, please check.")
            return render(request, "long_short/index.html", self.html_context)

        # Start backtesting
        self.html_context["data"] = []
        with ThreadPoolExecutor(max_workers=min(len(sectors), 12)) as executor:
            for sector in sectors:
                executor.submit(
                    self.start_backtest,
                    request,
                    market_cap,
                    sector,
                    method,
                    backtest_years,
                    pos_hold,
                    min_stock_price,
                    sorting_method,
                )

        # Sort result by sector
        self.html_context["data"] = sorted(
            self.html_context["data"], key=lambda data: data["sector"]
        )

        # Add chart data
        chart_data = self.add_chart_data()
        chart_data.iloc[:, 1:] = chart_data.iloc[:, 1:].astype(float).round(2)
        chart_data["date"] = chart_data["date"].apply(
            lambda value: dt.datetime.strftime(value, "%d-%b-%Y")
        )
        chart_data = chart_data.infer_objects(copy=False)
        chart_data.ffill(inplace=True)
        chart_data_clean = chart_data.copy()
        chart_data_clean = chart_data_clean.infer_objects(copy=False)
        chart_data_clean.fillna(0, inplace=True)
        self.html_context["chart_data"] = json.dumps(
            chart_data_clean.to_dict(orient="list")
        )

        # Get performance indicator (mdd, risk/return ratio)
        for col in chart_data.columns:
            # Only consider Total columns
            if "_total" in col.lower():
                mdd = get_mdd(chart_data[col])
                rtr = get_risk_to_return_ratio(mdd, chart_data[col])

                # Add indicators to html context
                for i in self.html_context["data"]:
                    if i["sector"] == col.replace("_Total", ""):
                        i["mdd"] = mdd
                        i["rtr"] = rtr

        # Get a list of sectors from LongShortEquity
        my_strategy = get_my_strategy(
            request.user,
            market_cap,
            pos_hold,
            min_stock_price,
            sorting_method.lower() == "ascending",
            method,
        )
        self.html_context["my_strategy"] = my_strategy

        # Update html context
        self.html_context["result"] = True
        self.html_context["long_total"] = round(self.long_total, 2)
        self.html_context["short_total"] = round(self.short_total, 2)
        self.html_context["longshort_total"] = round(
            self.long_total - self.short_total, 2
        )
        self.html_context["longshort_annualized"] = round(
            self.longshort_annualized / len(sectors), 2
        )

        # Add S&P500 data
        if not chart_data.empty:
            total = chart_data["S&P_500"].iloc[-1]
            mdd = get_mdd(chart_data["S&P_500"])
            self.html_context["sp500_total"] = total
            self.html_context["sp500_annualized"] = round(total / backtest_years, 2)
            self.html_context["sp500_mdd"] = mdd
            self.html_context["sp500_rtr"] = get_risk_to_return_ratio(
                mdd, chart_data["S&P_500"]
            )

        return render(request, "long_short/index.html", self.html_context)

    def start_backtest(
        self,
        request,
        market_cap,
        sector,
        method,
        backtest_years,
        pos_hold,
        min_stock_price,
        sorting_method,
    ):
        """
        Backtest strategy and add the result to self.html_context.
        """
        # Get US stocks
        try:
            df_us_stocks = get_us_stocks(market_cap, sector)
        except Exception as e:
            messages.warning(request, f"Error fetching US stocks for {sector}. ({e})")
            return

        if len(df_us_stocks) == 0 and not messages.get_messages(request):
            messages.warning(request, "No stocks found, please adjust your filter.")
            return

        # Get re-balancing dates
        l_re_balancing_dates = get_re_balancing_dates(backtest_years)

        # Get result by method for all stocks
        results = get_result_from_method(
            method,
            df_us_stocks["Ticker"].tolist(),
            min_stock_price,
            l_re_balancing_dates,
        )

        # Sort stocks by method, get top and bottom stocks by pos_hold, and split results by re-balancing dates
        result_subset = ranking(results, sorting_method, min_stock_price)

        # Get performance for all stocks
        df_top, df_bottom = get_performance(result_subset, pos_hold)
        if df_top.empty or df_bottom.empty:
            messages.warning(
                request,
                f"No financial data available for {sector}, please adjust your filter.",
            )
            return

        # Add row "Average" to dataframe
        get_average_performance(df_top)
        get_average_performance(df_bottom)

        # Calculate total performance for long and short stocks
        long_total = round(df_top.iloc[-1].sum(skipna=True), 2)
        short_total = round(df_bottom.iloc[-1].sum(skipna=True), 2)

        # Format dataframe
        """
        Ticker  Jan 2024    Perf(%)
        AAPL    0.25        3.07
        MSTR    0.16        -1.07
                0.21        1.00
        ...
        """
        for df in (df_top, df_bottom):
            df.rename(
                columns={col: "Perf(%)" for col in df.columns if "performance" in col},
                inplace=True,
            )
            df.rename(
                columns={"stock__ticker": "Ticker"},
                inplace=True,
            )
            df.rename(
                columns={
                    col: dt.datetime.strftime(
                        dt.datetime.strptime(col, "%Y-%m-%d"), "%b %Y"
                    )
                    for col in df.columns
                    if col not in ["Ticker", "Perf(%)"]
                },
                inplace=True,
            )
            df.replace(np.nan, "", inplace=True)

        # Get annualized return
        long_annualized = (
            df_top.loc["Average"].apply(pd.to_numeric, errors="coerce").mean() * 12
        )
        short_annualized = (
            df_bottom.loc["Average"].apply(pd.to_numeric, errors="coerce").mean() * 12
        )
        longshort_annualized = round((long_annualized - short_annualized), 2)

        # Add annualized performance to "Total"
        self.long_total += long_total
        self.short_total += short_total
        self.longshort_annualized += longshort_annualized

        # Set html context
        data = {
            "sector": sector,
            "df_top": df_top,
            "df_bottom": df_bottom,
            "long_total": long_total,
            "short_total": short_total,
            "longshort_total": round(long_total - short_total, 2),
            "longshort_annualized": longshort_annualized,
        }
        self.html_context["data"].append(data)

    def add_chart_data(self) -> pd.DataFrame:
        """Return a dataframe of chart_data for frontend chart."""

        def get_combine_performance(
            df_data: pd.DataFrame,
            df_candlesticks: pd.DataFrame,
            matching_columns: list,
            result_col_name: str,
        ) -> pd.DataFrame | bool:
            # Calculate performance
            df_all = pd.DataFrame(columns=["date"])

            for i in range(0, len(df_data.columns), 3):
                # Validate columns
                columns = df_data.columns[i : i + 3]
                if (
                    columns[0] != "Ticker"
                    or columns[1] not in matching_columns
                    or columns[2] != "Perf(%)"
                ):
                    logging.error(
                        f"Invalid columns: {columns} from {df_data.columns}. Please Check!"
                    )
                    return False

                # Initialize dataframe
                df = df_data.iloc[:, i : i + 3][["Ticker"]]

                # Get start date and end date
                date = df_data.iloc[:, i : i + 3].columns[1]
                start_date = dt.datetime.strptime(date, "%b %Y").replace(
                    tzinfo=dt.timezone.utc
                )
                end_date = start_date.replace(
                    day=monthrange(start_date.year, start_date.month)[-1]
                )

                # Filter candlesticks
                df_candlesticks_filter = df_candlesticks[
                    (df_candlesticks["date"] >= start_date)
                    & (df_candlesticks["date"] <= end_date)
                    & (df_candlesticks["stock__ticker"].isin(df["Ticker"].tolist()))
                ]

                # Get daily performance for each stock
                grouped = df_candlesticks_filter.groupby("stock__ticker")
                df_temp = pd.DataFrame(columns=["date"])
                for ticker, data in grouped:
                    # Init dataframe for ticker
                    df_ticker = data.copy().reset_index(drop=True)

                    # Calculate performance
                    df_ticker[f"{ticker}_perf_percent"] = (
                        df_ticker["close"] / df_ticker["open"][0] - 1
                    ) * 100

                    # Merge to df_temp
                    df_temp = df_temp.merge(
                        df_ticker[["date", f"{ticker}_perf_percent"]],
                        on="date",
                        how="outer",
                    )

                # Get average performance for all tickers
                df_temp[result_col_name] = df_temp.iloc[:, 1:].mean(axis=1)

                # Continue from the last month
                if not df_all.empty:
                    df_temp[result_col_name] += df_all[result_col_name].iloc[-1]

                # Extract necessary columns
                df_temp = df_temp[["date", result_col_name]]

                # df_temp joins df_all
                if df_temp.empty:
                    continue
                elif df_all.empty and not df_temp.empty:
                    df_all = df_temp.copy()
                else:
                    df_all = pd.concat([df_all, df_temp], axis=0)

            return df_all.reset_index(drop=True)

        # Loop through each sector
        df_total = pd.DataFrame(columns=["date"])
        for data in self.html_context["data"]:
            # Get all tickers
            tickers_long = set(data["df_top"]["Ticker"].values.flatten())
            tickers_short = set(data["df_bottom"]["Ticker"].values.flatten())
            tickers = tickers_long.union(tickers_short)

            # Get start_date and end_date
            date_pattern = r"^[A-Za-z]{3} \d{4}$"
            matching_columns = [
                col for col in data["df_top"].columns if re.match(date_pattern, col)
            ]
            start_date = dt.datetime.strptime(matching_columns[0], "%b %Y").replace(
                tzinfo=dt.timezone.utc
            )
            end_date = dt.datetime.strptime(matching_columns[-1], "%b %Y").replace(
                tzinfo=dt.timezone.utc
            )
            end_date = end_date.replace(
                day=monthrange(end_date.year, end_date.month)[-1]
            )

            # Get candlesticks (date, stock__ticker, open, close) for all tickers, from start_date to end_date
            res = CandleStick.objects.filter(
                stock__ticker__in=tickers,
                date__gte=start_date,
                date__lte=end_date,
            ).values("date", "stock__ticker", "open", "close")
            df_candlesticks = pd.DataFrame(res)

            # Add performance from start_date to end_date
            df_long = get_combine_performance(
                data["df_top"],
                df_candlesticks,
                matching_columns,
                f"{data['sector']}_Long",
            )
            df_short = get_combine_performance(
                data["df_bottom"],
                df_candlesticks,
                matching_columns,
                f"{data['sector']}_Short",
            )
            df_short[f"{data['sector']}_Short"] = -df_short[f"{data['sector']}_Short"]

            # Merge df_long and df_short to df_total
            df_total = df_total.merge(df_long, on="date", how="outer")
            df_total = df_total.merge(df_short, on="date", how="outer")
            df_total[f"{data['sector']}_Total"] = (
                df_long[f"{data['sector']}_Long"] + df_short[f"{data['sector']}_Short"]
            )

        # Add performance of S&P_500 (ticker: ^GSPC) to df_total
        if self.html_context["data"]:
            res = CandleStick.objects.filter(
                stock__ticker="^GSPC",
                date__gte=start_date,
                date__lte=end_date,
            ).values("date", "stock__ticker", "open", "close")
            df_sp500 = pd.DataFrame(res)
            df_sp500["S&P_500"] = (df_sp500["close"] / df_sp500["open"][0] - 1) * 100
            df_sp500["S&P_500"] = df_sp500["S&P_500"].astype(float).round(2)
            df_total = df_total.merge(
                df_sp500[["date", "S&P_500"]], on="date", how="left"
            )

        return df_total


def separate_words(string: str) -> str:
    """
    To separate words, e.g. from 'ResearchAndDevelopment' to 'Research And Development'
    """
    return re.sub(r"(?<![A-Z])(?=[A-Z])", " ", string).strip()


def get_my_strategy(
    user: User,
    market_cap: list,
    pos_side_per_sector: int,
    min_stock_price: int,
    sort_ascending: bool,
    formula: str,
) -> set:
    """Return a set of sectors which matches the criteria'"""
    res = LongShortEquity.objects.filter(
        user=user,
        market_cap=market_cap,
        position_side_per_sector=pos_side_per_sector,
        min_stock_price=min_stock_price,
        sort_ascending=sort_ascending,
        formula=formula,
    ).values_list("sector", flat=True)

    if res.count() == 0:
        return []

    return [sector.replace("-", " ").title() for sector in res]


def get_us_stocks(
    market_cap_filter: list = [],
    sector_filter: str | list = None,
) -> pd.DataFrame:
    """
    Return us stocks information by selected market cap and sectors.
    """
    market_cap_str = list(market_cap.keys())
    market_cap_value = list(market_cap.values())

    # Get selected market cap
    mega = market_cap_str[0] in market_cap_filter
    large = market_cap_str[1] in market_cap_filter
    medium = market_cap_str[2] in market_cap_filter
    small = market_cap_str[3] in market_cap_filter
    micro = market_cap_str[4] in market_cap_filter
    nano = market_cap_str[5] in market_cap_filter

    # MarketCap query
    mega_q = Q(market_cap__gte=market_cap_value[0]) if mega else Q()
    large_q = (
        Q(market_cap__range=[market_cap_value[1][0], market_cap_value[1][-1]])
        if large
        else Q()
    )
    medium_q = (
        Q(market_cap__range=[market_cap_value[2][0], market_cap_value[2][-1]])
        if medium
        else Q()
    )
    small_q = (
        Q(market_cap__range=[market_cap_value[3][0], market_cap_value[3][-1]])
        if small
        else Q()
    )
    micro_q = (
        Q(market_cap__range=[market_cap_value[4][0], market_cap_value[4][-1]])
        if micro
        else Q()
    )
    nano_q = (
        Q(market_cap__range=[market_cap_value[5][0], market_cap_value[5][-1]])
        if nano
        else Q()
    )

    # Sector query
    if sector_filter:
        if isinstance(sector_filter, str):
            sector_q = Q(sector=sector_filter)
        elif isinstance(sector_filter, list):
            sector_q = Q(sector__in=sector_filter)
        else:
            sector_q = Q()
    else:
        sector_q = Q()

    # Get stock information by marketcap and sectors
    results = Stock.objects.filter(
        (mega_q | large_q | medium_q | small_q | micro_q | nano_q),
        sector_q,
        ticker__regex=r"^[a-zA-Z]{1,5}$",
    )
    results = pd.DataFrame(results.values())
    results.rename(columns={"ticker": "Ticker"}, inplace=True)

    return results


def get_re_balancing_dates(backtest_years: int = 1) -> list:
    """
    Retrun a list of re-balancing dates for backtesting.
    (re-balancing dates are the first day of every months)
    """
    l_months = []
    this_month = dt.datetime.now(tz=dt.timezone.utc).replace(
        day=1, hour=0, minute=0, second=0, microsecond=0
    )
    [
        l_months.append(this_month - relativedelta(months=m))
        for m in reversed(range(backtest_years * 12))
    ]

    return l_months


def get_result_from_method(
    formula: str,
    stock_list: list,
    min_stock_price: float,
    re_balancing_dates: list,
) -> pd.DataFrame:
    """
    Add results from the given formula and return as a DataFrame.

    ticker  date1   date2   date3
    AAPL    0.52    0.51    0.1
    NVDA    0.22    0.11    0.1
    ...
    pd.DataFrame()

    """
    # Extract data names from 'formula'
    datas = re.findall(r"\w+(?:\s+\w+)*", formula)

    # Trun data nammes to GAAP format (data names in database)
    datas = [data.replace(" ", "").strip() for data in datas]
    formula = formula.replace(" ", "").strip()

    # Validate report data
    l_income_statement = list(
        set(datas).intersection(
            set([field.name for field in IncomeStatement._meta.get_fields()])
        )
    )
    l_balance_sheet = list(
        set(datas).intersection(
            set([field.name for field in BalanceSheet._meta.get_fields()])
        )
    )
    l_cash_flow = list(
        set(datas).intersection(
            set([field.name for field in CashFlow._meta.get_fields()])
        )
    )

    # Get data from database and apply formula for each re-balancing date
    df_result = pd.DataFrame(columns=["stock__ticker"], data=stock_list)

    for date in re_balancing_dates:
        # Get stock ids by min_stock_price and dates
        res = CandleStick.objects.filter(
            stock__ticker__in=stock_list,
            close__gte=min_stock_price,
            date__lt=date,
            date__gte=date - dt.timedelta(days=30),
        ).values_list("stock__id", flat=True)
        stock_ids = list(set(res))

        # Get data from database
        df_report = pd.DataFrame(columns=["stock__ticker"])
        if l_income_statement:
            df_report = merge_report(
                IncomeStatement,
                df_report,
                stock_ids,
                date,
                l_income_statement,
            )
        if l_balance_sheet:
            df_report = merge_report(
                BalanceSheet, df_report, stock_ids, date, l_balance_sheet
            )
        if l_cash_flow:
            df_report = merge_report(CashFlow, df_report, stock_ids, date, l_cash_flow)

        # Apply formula
        column_name = dt.datetime.strftime(date, "%Y-%m-%d")
        df_report.fillna(0, inplace=True)
        values = apply_formula(df_report, formula, column_name)
        df_result = df_result.merge(
            values[["stock__ticker", column_name]], how="left", on="stock__ticker"
        )

    return df_result.replace(np.nan, 0).replace(np.inf, 0).replace(-np.inf, 0)


def merge_report(
    model: Tuple[IncomeStatement | BalanceSheet | CashFlow],
    report: pd.DataFrame,
    stock_ids: list,
    date: dt.datetime,
    data_name: list,
) -> pd.DataFrame:
    """Get data from database and merge into report."""
    # Drop duplicate columnsn
    if set(data_name).intersection(set(report.columns)):
        report.drop(columns=data_name, inplace=True)

    # Query database by stock ids and date
    query_res = model.objects.filter(
        stock__id__in=stock_ids,
        FileDate__lt=date,
        FileDate__gt=date - dt.timedelta(days=365),
        **{f"{data}__isnull": False for data in data_name},
    ).order_by("-FileDate")

    # Get most updated data
    df = pd.DataFrame(
        query_res.values(
            "stock__ticker",
            "FileDate",
            *[data for data in data_name],
        )
    ).drop_duplicates(subset="stock__ticker")

    # Merge df to report
    result = report.merge(
        df[["stock__ticker"] + data_name], on=["stock__ticker"], how="outer"
    )

    return result


def apply_formula(df: pd.DataFrame, formula: str, result_col_name: str) -> pd.DataFrame:
    # Replace formula to "df[data_name] +-*/ df[data_name]..."
    for col in df.columns:
        formula = formula.replace(col, f'df["{col}"]')
        if col != "stock__ticker":
            df[col] = df[col].astype(float)

    # Evaluate
    df[result_col_name] = eval(formula)

    # Format the result column values
    df[result_col_name] = df[result_col_name].apply(
        lambda x: (
            f"{x:.2e}"
            if (x != 0 and (abs(x) >= 1e6 or abs(x) <= 1e-6))
            else round(x, 2)
        )
    )

    return df


def ranking(results: pd.DataFrame, sorting_method: str, min_stock_price: float) -> dict:
    """
    Rank results for each columns except 'stock__ticker' and return
    as dict format
    {
        col_name: seperated_result,
        col_name: seperated_result, ...
    }
    """
    seperated_results = {}
    ascending = True if sorting_method == "Ascending" else False
    for col in results.columns:
        if col == "stock__ticker":
            continue
        result = results[["stock__ticker", col]].dropna()
        result = result[result[col] != 0]
        seperated_results[col] = result[["stock__ticker", col]].sort_values(
            by=col, ascending=ascending, key=lambda x: pd.to_numeric(x, errors="coerce")
        )

    return seperated_results


def get_performance(
    result_subset: dict, pos_hold: int
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Calculate performance and split it to top and bottom stocks.
    """
    # Calculate performance
    for date, df in result_subset.items():
        # Get ticker list
        ticker_list = df["stock__ticker"].tolist()

        # Get start date and end date
        start_date = dt.datetime.strptime(date, "%Y-%m-%d").replace(
            tzinfo=dt.timezone.utc
        )
        last_day = monthrange(start_date.year, start_date.month)[-1]
        end_date = start_date.replace(day=last_day)

        # Query database by ticker_list and date
        query_res = CandleStick.objects.filter(
            stock__ticker__in=ticker_list,
            date__gte=start_date,
            date__lte=end_date,
            open__gt=0,
            close__gt=0,
        ).order_by("-date")

        # Calculate performance
        if query_res.count() == 0:
            # Set performance to 0 if no data found
            performance = df.copy()
            performance[f"performance ({date})"] = 0
            performance.drop(columns=date, inplace=True)
            performance.reset_index(drop=True, inplace=True)
        else:
            # Create candlesticks
            df_prices = pd.DataFrame(
                list(query_res.values("stock__ticker", "date", "open", "close"))
            )

            # Calculate performance
            performance = (
                df_prices.groupby("stock__ticker")
                .apply(
                    lambda group: round(
                        (group.iloc[0]["close"] / group.iloc[-1]["open"] - 1) * 100, 2
                    )
                )
                .reset_index(name=f"performance ({date})")
            )

        # Merge result
        df = df.merge(performance, on="stock__ticker")
        result_subset[date] = df

    # Combine results
    top_stocks = pd.DataFrame()
    bottom_stocks = pd.DataFrame()
    for date, result in result_subset.items():
        half_rows_num = min(pos_hold, len(result) // 2)
        top_stocks.reset_index(inplace=True, drop=True)
        bottom_stocks.reset_index(inplace=True, drop=True)

        # Add top stocks
        result_top_stocks = result.head(half_rows_num).reset_index(drop=True)
        top_stocks = pd.concat([top_stocks, result_top_stocks], axis=1)

        # Add bottom stocks
        result_bottom_stocks = result.tail(half_rows_num).reset_index(drop=True)
        bottom_stocks = pd.concat([bottom_stocks, result_bottom_stocks], axis=1)

    return top_stocks, bottom_stocks


def get_average_performance(df: pd.DataFrame):
    """
    Add row "Average" for all 'performance' columns.
    """
    perf_cols = [col for col in df.columns if "performance" in col]
    df.loc["Average"] = df[perf_cols].mean().astype(float).round(2)

    return df


def get_mdd(series: pd.Series) -> float:
    "Get maxmimum drawdown"
    series.dropna(inplace=True)
    highest = 0
    mdd = 0
    for i in series:
        highest = max(i, highest)
        if highest != i:
            mdd = max(highest - i, mdd)

    return round(mdd, 2)


def get_risk_to_return_ratio(mdd: float, series: pd.Series) -> float:
    """Total return divided by max drawdown"""
    series.dropna(inplace=True)
    return round(series.iloc[-1] / mdd, 2)


# -----------------------------------------------------------------------------
# | Functions fetched from front end                                          |
# -----------------------------------------------------------------------------
@require_POST
@login_required
def alter_my_strategy(request):
    """Add/ Delete LongShortEquity from the database."""
    # Get request content
    res_content = json.loads(request.body)

    # Parse string to list
    market_cap = res_content["market_cap"].replace("'", '"')
    market_cap_list = json.loads(market_cap)

    try:
        # Create params for database operation and JsonResponse
        if res_content["action"] == "add":
            db_operation = LongShortEquity.objects.update_or_create
            status = "Created"
            status_code = 201
            message = f"Strategy < {res_content['sector']} > Added"
            message_type = "success"
        elif res_content["action"] == "delete":
            db_operation = LongShortEquity.objects.filter
            status = "OK"
            status_code = 200
            message = f"Strategy < {res_content['sector']} > Deleted"
            message_type = "warning"
        else:
            raise

        # Database operation
        res = db_operation(
            user=request.user,
            name="LongShort Equity",
            market_cap=market_cap_list,
            position_side_per_sector=int(res_content["pos_hold"]),
            min_stock_price=int(res_content["min_stock_price"]),
            sort_ascending=res_content["sorting_method"].lower() == "ascending",
            sector=res_content["sector"],
            formula=res_content["formula"],
        )

        if res_content["action"] == "delete":
            res.delete()

        return JsonResponse(
            {
                "status": status,
                "message": message,
                "message_type": message_type,
            },
            status=status_code,
        )

    except Exception as e:
        return JsonResponse(
            {
                "status": "bad request",
                "message": "Error editing My Strategy, please try again later.",
                "message_type": "error",
            },
            status=400,
        )


@require_POST
@login_required
def export_csv(request) -> HttpResponse:
    """
    Get request.POST["table_data"], then calcualte execute position, and
    create BasketTrader csv. Return HttpResponse with BasketTrader csv.
    """
    # Get user uploaded portfolio
    file = None
    if request.FILES.get("file"):
        file = request.FILES["file"]
    try:
        df_portfolio = pd.read_csv(file)

        # Replace the position to 0 if there is Exit Price
        if "Exit Price" in df_portfolio.columns:
            df_portfolio.loc[df_portfolio["Exit Price"].notna(), "Position"] = 0

        # Extract columns: Financial Instrument, Position
        df_portfolio = df_portfolio[["Financial Instrument", "Position"]]

        # Get ticker
        df_portfolio["Financial Instrument"] = (
            df_portfolio["Financial Instrument"].str.split(" ").str[0]
        )

        # Replace K/k, M/m, to 000, 000,000 in column "Position"
        replace_position = {
            "K": 1000,
            "k": 1000,
            "M": 1000000,
            "m": 1000000,
            "'": "",
            ",": "",
        }
        df_portfolio["Position"].fillna(0, inplace=True)
        df_portfolio["Position"] = (
            df_portfolio["Position"].replace(replace_position, regex=True).astype(int)
        )

        # Rename columns
        df_portfolio.rename(
            columns={"Financial Instrument": "Ticker", "Position": "Existing Position"},
            inplace=True,
        )
    except Exception as e:
        logging.warning(f"Error: {e}")
        df_portfolio = pd.DataFrame(columns=["Ticker", "Existing Position"])

    # Get long and short data from "table_data"
    data = json.loads(request.POST["table_data"])

    # Get amount from user input
    amount = abs(int(request.POST["amount"]))

    # Create DataFrame for long and short stocks with columns:
    # Amount(USD), Prev Close and Expected Position
    df_long = get_expected_position(data["long_table"], amount // 2)
    df_short = get_expected_position(data["short_table"], amount // 2)
    df_short["Expected Position"] = -df_short["Expected Position"]

    # Combine long and short data
    df_execute = pd.concat([df_long, df_short], ignore_index=True)

    # Merge user uploaded portfolio, or blank dataframe to df_execute
    df_execute = pd.merge(df_execute, df_portfolio, on="Ticker", how="outer")

    # Calculate "Execute Position"
    df_execute["Existing Position"] = (
        df_execute["Existing Position"].infer_objects(copy=False).fillna(0)
    )
    df_execute["Expected Position"] = (
        df_execute["Expected Position"].infer_objects(copy=False).fillna(0)
    )
    df_execute["Execute Position"] = (
        df_execute["Expected Position"].astype(float) - df_execute["Existing Position"]
    )

    # Format column: Execute Position
    df_execute["Execute Position"] = df_execute["Execute Position"].round(2)

    # Extract columns: Ticker, Execute Position
    df_execute = df_execute[["Ticker", "Execute Position"]]

    # Drop rows with "Execute Position" = 0
    df_execute = df_execute[df_execute["Execute Position"] != 0]

    # Create basket trader dataframe
    basket_trader_cols = [
        "Action",
        "Quantity",
        "Symbol",
        "SecType",
        "Exchange",
        "Currency",
        "TimeInForce",
        "OrderType",
        "BasketTag",
        "Account",
        "OrderRef",
        "LmtPrice",
        "UsePriceMgmtAlgo",
        "OutsideRth",
    ]
    basket_tag = "LONG/SHORT"
    df_basket_trader = pd.DataFrame(columns=basket_trader_cols)
    df_basket_trader["Symbol"] = df_execute["Ticker"]
    df_basket_trader["Quantity"] = df_execute["Execute Position"]
    df_basket_trader["Action"] = np.where(
        df_basket_trader["Quantity"] >= 0, "BUY", "SELL"
    )
    df_basket_trader["SecType"] = "STK"
    df_basket_trader["Exchange"] = "SMART/NASDAQ/NYSE/ARCA"
    df_basket_trader["Currency"] = "USD"
    df_basket_trader["TimeInForce"] = "GTC"
    df_basket_trader["OrderType"] = "LMT"
    df_basket_trader["BasketTag"] = basket_tag
    df_basket_trader["Account"] = ""
    df_basket_trader["OrderRef"] = basket_tag
    df_basket_trader["LmtPrice"] = 0
    df_basket_trader["UsePriceMgmtAlgo"] = "TRUE"
    df_basket_trader["OutsideRth"] = "FALSE"

    # Create HttpResponse
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="basket_trader.csv"'
    writer = csv.writer(response)
    writer.writerow(basket_trader_cols)
    for index, row in df_basket_trader.iterrows():
        writer.writerow(row.tolist())

    return response


@require_POST
@login_required
def get_expected_position(l_tables: list, amount: int) -> pd.DataFrame:
    """
    Convert frontend data to dataframe, and calculate expected position for the latest period.
    Params:
        l_table: [
            [[Apr 2024,               May, 2025,              ...],   # [0][0]
             [Ticker, Value, Perf(%), TIcker, Value, Perf(%), ...],   # [0][1]
             [AAPL,   0.00,  0.00,    GOOGL,  0.00,  0.00,    ... ],  # [0][2]
             [NVDA,   0.00,  0.00,    META,  0.00,  0.00,    ... ],   # [0][3]
             ...],
            [[...]], # [1]
            ...
        ]
        amount: "Total Amount" from user input
    """

    def search_date_string(string: str) -> bool:
        """Return true if string is the format of %b %Y."""
        pattern = r"^[A-Za-z]{3} \d{4}$"
        match = re.match(pattern, string)

        return bool(match)

    # Create columns list from l_tables[0][1]
    columns = []
    for col in l_tables[0][1]:
        # Replace the column 'Value' to date string
        columns.append(col) if col != "Value" else columns.append(l_tables[0][0].pop(0))

    # Create DataFrame for l_tables
    df = pd.DataFrame(columns=columns)
    for table in l_tables:
        # Exclude the first 2 rows, they are column names
        df = pd.concat([df, pd.DataFrame(columns=columns, data=table[2:])])

    # Extract the last 3 columns (the latest re-balancing period)
    df = df.iloc[:, -3:]

    # Remove empty rows
    df = df[df["Ticker"] != ""]

    # Assign amount for each stock (average amount for long and short stocks)
    df["Amount(USD)"] = amount // len(df)

    # Get date string from df.columns
    date_str = None
    for col in df.columns:
        if search_date_string(col):
            date_str = col
            break

    if not date_str:
        logging.error("No date string found in the dataframe. Please check.")
        return

    # Get previous close for each stock
    date = dt.datetime.strptime(date_str, "%b %Y").replace(tzinfo=dt.timezone.utc)
    query_res = CandleStick.objects.filter(
        stock__ticker__in=df["Ticker"].tolist(), date__lt=date
    ).order_by("-date")
    df_prev_close = pd.DataFrame(
        query_res.values(
            "stock__ticker",
            "close",
        )
    ).drop_duplicates(subset="stock__ticker")

    # Rename columns
    df_prev_close.rename(
        columns={"stock__ticker": "Ticker", "close": "Prev Close"},
        inplace=True,
    )

    # Merge prev_close to the main dataframe
    df = df.merge(df_prev_close, on="Ticker")

    # Assign position for each stock
    df["Expected Position"] = df["Amount(USD)"] / df["Prev Close"]

    return df


@require_POST
@login_required
def search_method(request):
    """
    Search data names in Income Statement, Balance Sheet and Cash Flow, by "search_text".
    Return JsonResponse with a list of data name.
    """
    search_str = json.loads(request.body).get("search_text")
    if search_str.strip() == "":
        return JsonResponse({"result": []})

    fields_income_statement = [
        separate_words(field.name)
        for field in IncomeStatement._meta.get_fields()
        if field.concrete
        and field.name
        not in ("id", "stock", "FileDate", "StartDate", "EndDate", "FiscalPeriod")
    ]
    fields_balancesheet = [
        separate_words(field.name)
        for field in BalanceSheet._meta.get_fields()
        if field.concrete
        and field.name
        not in ("id", "stock", "FileDate", "StartDate", "EndDate", "FiscalPeriod")
    ]
    fields_cashflow = [
        separate_words(field.name)
        for field in CashFlow._meta.get_fields()
        if field.concrete
        and field.name
        not in ("id", "stock", "FileDate", "StartDate", "EndDate", "FiscalPeriod")
    ]
    all_fields = fields_income_statement + fields_balancesheet + fields_cashflow
    results = [method for method in all_fields if search_str.lower() in method.lower()]

    return JsonResponse({"result": list(set(sorted(results)))})


@require_POST
@login_required
def update_stock_numbers(request):
    """
    Get number of stock by "market-cap", "sectors".
    """
    # Get params from frontend
    data = json.loads(request.body)
    selected_market_cap = data.get("market_cap")
    selected_sectors = data.get("sectors")
    if "All" in selected_sectors:
        selected_sectors.remove("All")

    # Get US stocks by market_cap and sectors
    try:
        stocks = get_us_stocks(selected_market_cap, selected_sectors)
    except Exception as e:
        logging.warning(
            f"Error fetching US stocks for {selected_market_cap} and {selected_sectors}. ({e})"
        )
        return JsonResponse({"status": 404})

    result = {}

    # Update result by sector
    for sector in sectors:
        result[sector] = len(stocks[stocks["sector"] == sector])
    result["All"] = sum(result.values())

    # Update result by market cap
    for mc in market_cap:
        if "Mega" in mc:
            result[mc] = len(stocks[stocks["market_cap"] >= market_cap[mc]])
        else:
            result[mc] = len(
                stocks[
                    (stocks["market_cap"] >= market_cap[mc][0])
                    & (stocks["market_cap"] < market_cap[mc][-1])
                ]
            )

    return JsonResponse({"result": result})
