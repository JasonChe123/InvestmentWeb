from calendar import monthrange
from concurrent.futures.thread import ThreadPoolExecutor
import csv
import datetime as dt
from django.contrib import messages
from django.db.models import Q
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render
from django.template.context_processors import csrf
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


class BackTestView(View):
    def __init__(self):
        super().__init__()
        self.long_total = 0
        self.short_total = 0
        self.longshort_annualized = 0

        # Initialize parameter: market cap
        self.market_cap = market_cap

        # # Initialize parameter: fundamental data
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

        # # Initialize other parameters
        self.backtest_years = [i for i in range(1, 5)]
        self.pos_hold = [50, 40, 30, 20, 10]
        self.min_stock_price = [1, 2, 3, 4, 5, 10]
        self.sectors = {k: 0 for k in sectors}

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
        # Get user's parameters
        market_cap = request.POST.getlist("market-cap")
        method = request.POST.get("selected-method").rstrip("+-*/")
        sectors = [s for s in self.sectors if request.POST.get(s)]
        backtest_years = int(request.POST.get("backtest_years"))
        pos_hold = int(request.POST.get("pos_hold"))
        min_stock_price = float(request.POST.get("min_stock_price"))
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
            self.html_context["data"], key=lambda d: d["sector"]
        )

        # Add chart data
        chart_data = self.add_chart_data()
        chart_data.iloc[:, 1:] = chart_data.iloc[:, 1:].astype(float).round(2)
        chart_data["date"] = chart_data["date"].apply(
            lambda value: dt.datetime.strftime(value, "%d-%b-%Y")
        )
        chart_data.ffill(inplace=True)
        chart_data_clean = chart_data.copy()
        chart_data_clean.fillna(0, inplace=True)
        self.html_context["chart_data"] = json.dumps(chart_data_clean.to_dict(orient="list"))

        # Get performance indicator (mdd, risk / return ratio)
        for col in chart_data.columns:
            # Only consider Total columns
            if "_total" in col.lower():
                mdd = get_mdd(chart_data[col])
                rtr = get_risk_to_return_ratio(mdd, chart_data[col])

                # Set html context
                for i in self.html_context["data"]:
                    if i["sector"] == col.replace("_Total", ""):
                        i["mdd"] = mdd
                        i["rtr"] = rtr

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
            self.html_context["sp500_rtr"] = get_risk_to_return_ratio(mdd, chart_data["S&P_500"])

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
        # Get US stocks
        df_us_stocks = get_us_stocks(market_cap, sector)
        if len(df_us_stocks) == 0 and not messages.get_messages(request):
            messages.warning(request, "No stocks found, please adjust your filter.")
            return

        # Get re-balancing dates
        l_re_balancing_dates = get_re_balancing_dates(backtest_years)

        # Get result by method chose
        results = get_result_from_method(
            method,
            df_us_stocks["Ticker"].tolist(),
            min_stock_price,
            l_re_balancing_dates,
            self.income_statement,
            self.balance_sheet_data,
            self.cash_flow_data,
        )

        # Ranking and split results
        result_subset = ranking(results, sorting_method, min_stock_price)

        # Get performance for each re-balancing date
        df_top, df_bottom = get_performance(result_subset, pos_hold)
        if df_top.empty or df_bottom.empty:
            messages.warning(
                request,
                f"No financial data available for {sector}, please adjust your filter.",
            )
            return

        # Add average performance to the top stocks, and bottom stocks
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

        # Total for all sectors
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

    def add_chart_data(self):
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
                    logging.error(f"Invalid columns: {columns}. Please Check!")
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

                # Combine to df_all
                df_all = pd.concat(
                    [df_all if not df_all.empty else None, df_temp], axis=0
                )

            return df_all.reset_index(drop=True)

        # Init dataframe
        df_total = pd.DataFrame(columns=["date"])

        # Loop through each sector
        for data in self.html_context["data"]:
            # Get all tickers
            tickers_top = set(data["df_top"]["Ticker"].values.flatten())
            tickers_bottom = set(data["df_bottom"]["Ticker"].values.flatten())
            tickers = tickers_top.union(tickers_bottom)

            # Get all dates
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

            # Get candlesticks
            res = CandleStick.objects.filter(
                stock__ticker__in=tickers,
                date__gte=start_date,
                date__lte=end_date,
            ).values("date", "stock__ticker", "open", "close")
            df_candlesticks = pd.DataFrame(res)

            # Get combined performance
            df_top = get_combine_performance(
                data["df_top"],
                df_candlesticks,
                matching_columns,
                f"{data['sector']}_Long",
            )
            df_bottom = get_combine_performance(
                data["df_bottom"],
                df_candlesticks,
                matching_columns,
                f"{data['sector']}_Short",
            )
            df_bottom[f"{data['sector']}_Short"] = -df_bottom[f"{data['sector']}_Short"]

            # Merge to df_total
            df_total = df_total.merge(df_top, on="date", how="outer")
            df_total = df_total.merge(df_bottom, on="date", how="outer")
            df_total[f"{data['sector']}_Total"] = (
                df_top[f"{data['sector']}_Long"] + df_bottom[f"{data['sector']}_Short"]
            )

        # Add S&P500 to df_total
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


def get_us_stocks(
    market_cap_filter: list = [],
    sector_filter: str | list = None,
) -> pd.DataFrame:
    """
    Return us stocks based on selected market cap, min ipo years, and sectors.
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

    # Setup query
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
    if sector_filter:
        if isinstance(sector_filter, str):
            sector_q = Q(sector=sector_filter)
        elif isinstance(sector_filter, list):
            sector_q = Q(sector__in=sector_filter)
        else:
            sector_q = Q()
    else:
        sector_q = Q()

    # Query database
    results = Stock.objects.filter(
        (mega_q | large_q | medium_q | small_q | micro_q | nano_q),
        sector_q,
        ticker__regex=r"^[a-zA-Z]{1,4}$",
    )

    # Convert to dataframe
    results = pd.DataFrame(results.values())
    results.rename(columns={"ticker": "Ticker"}, inplace=True)

    return results


def get_re_balancing_dates(backtest_years: int = 1) -> list:
    """
    Get a list of re-balancing dates for backtesting.
    """
    l_months = []
    month = dt.datetime.now(tz=dt.timezone.utc).replace(
        day=1, hour=0, minute=0, second=0, microsecond=0
    )
    l_months.append(month)
    for i in range(1, backtest_years * 12):
        if month.month == 1:
            month = month.replace(year=month.year - 1, month=12)
        else:
            month = month.replace(month=month.month - 1)
        l_months.append(month)

    l_months.reverse()

    return l_months


def get_result_from_method(
    formula: str,
    stock_list: list,
    min_stock_price: float,
    re_balancing_dates: list,
    income_statement_data: list,  # ['Basic EPS', 'EPS', ...]
    balance_sheet_data: list,
    cash_flow_data: list,
) -> pd.DataFrame:
    """
    Calculate the result of a given formula for US stocks based on financial data and re-balancing dates.

    ticker  date1   date2   date3
    AAPL    0.52    0.51    0.1
    NVDA    0.22    0.11    0.1
    ...
    pd.DataFrame()

    """
    # Extract data names from method
    datas = re.findall(r"\w+(?:\s+\w+)*", formula)
    datas = [data.replace(" ", "").strip() for data in datas]

    # Format data names - E.g. from 'Basic EPS' to 'BasicEPS'
    income_statement_data = [
        data.replace(" ", "").strip() for data in income_statement_data
    ]
    balance_sheet_data = [data.replace(" ", "").strip() for data in balance_sheet_data]
    cash_flow_data = [data.replace(" ", "").strip() for data in cash_flow_data]
    formula = formula.replace(" ", "").strip()

    # Validate report data
    income_statement_data = set(datas).intersection(
        set([field.name for field in IncomeStatement._meta.get_fields()])
    )
    balance_sheet_data = set(datas).intersection(
        set([field.name for field in BalanceSheet._meta.get_fields()])
    )
    cash_flow_data = set(datas).intersection(
        set([field.name for field in CashFlow._meta.get_fields()])
    )

    # Calculate result for each re-balancing date
    result_df = pd.DataFrame(
        columns=[
            "stock__ticker",
        ],
        data=stock_list,
    )
    for date in re_balancing_dates:
        # Min stock price filter
        res = CandleStick.objects.filter(
            stock__ticker__in=stock_list,
            close__gte=min_stock_price,
            date__lt=date,
            date__gte=date - dt.timedelta(days=30),
        ).values_list("stock__id", flat=True)
        valid_stock_ids = list(set(res))

        # Read data with dataframe
        report_df = pd.DataFrame(columns=["stock__ticker"])
        if income_statement_data:
            report_df = merge_report(
                IncomeStatement,
                report_df,
                valid_stock_ids,
                date,
                list(income_statement_data),
            )

        if balance_sheet_data:
            report_df = merge_report(
                BalanceSheet, report_df, valid_stock_ids, date, list(balance_sheet_data)
            )

        if cash_flow_data:
            report_df = merge_report(
                CashFlow, report_df, valid_stock_ids, date, list(cash_flow_data)
            )

        # Calculate by formula
        column_name = dt.datetime.strftime(date, "%Y-%m-%d")
        report_df = report_df.replace(np.nan, 0)
        values = apply_formula(report_df, formula, column_name)
        result_df = result_df.merge(
            values[["stock__ticker", column_name]], how="left", on="stock__ticker"
        )

    return result_df.replace(np.nan, 0).replace(np.inf, 0).replace(-np.inf, 0)


def merge_report(
    model: Tuple[IncomeStatement | BalanceSheet | CashFlow],
    report: pd.DataFrame,
    valid_stock_ids: list,
    date: dt.datetime,
    report_data: list,
) -> pd.DataFrame:
    query_res = model.objects.filter(
        stock__id__in=valid_stock_ids,
        FileDate__lt=date,
        FileDate__gt=date - dt.timedelta(days=365),
        **{f"{data}__isnull": False for data in report_data},
    ).order_by("-FileDate")
    df = pd.DataFrame(
        query_res.values(
            "stock__ticker",
            "FileDate",
            *[data for data in report_data],
        )
    ).drop_duplicates(subset="stock__ticker")
    result = report.merge(
        df[["stock__ticker"] + report_data], on=["stock__ticker"], how="outer"
    )

    return result


def apply_formula(df: pd.DataFrame, formula: str, result_col_name: str) -> pd.DataFrame:
    # Replace columns names
    for col in df.columns:
        formula = formula.replace(col, f'df["{col}"]')

    # Evaluate
    df[result_col_name] = eval(formula).round(2)

    return df


def ranking(results: pd.DataFrame, sorting_method: str, min_stock_price: float) -> dict:
    seperated_results = {}
    ascending = True if sorting_method == "Ascending" else False
    for col in results.columns:
        if col == "stock__ticker":
            continue
        result = results[["stock__ticker", col]].dropna()
        result = result[result[col] != 0]
        seperated_results[col] = result[["stock__ticker", col]].sort_values(
            by=col, ascending=ascending
        )

    return seperated_results


def get_performance(
    result_subset: dict, pos_hold: int
) -> Tuple[pd.DataFrame, pd.DataFrame]:

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

        # Query database
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

            # Calculation
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
    """Total return divide by max drawdown"""
    series.dropna(inplace=True)
    return round(series.iloc[-1] / mdd, 2)


# Functions fetched from front end --------------------------------------------
@require_POST
def search_method(request):
    """
    Search the method in Income Statement, Balance Sheet and Cash Flow, and return to the front-end.
    :param request: Request
    :return: {result: [method1, method2, ...]}
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
def update_stock_numbers(request):
    # Get params from frontend
    data = json.loads(request.body)
    selected_market_cap = data.get("market_cap")
    selected_sectors = data.get("sectors")
    if "All" in selected_sectors:
        selected_sectors.remove("All")

    # Get US stocks
    stocks = get_us_stocks(
        market_cap_filter=selected_market_cap, sector_filter=selected_sectors
    )

    result = {}

    # Update stocks by sector
    for sector in sectors:
        result[sector] = len(stocks[stocks["sector"] == sector])
    result["All"] = sum(result.values())

    # Update stocks by market cap
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


def export_csv(request):
    """
    Fetched from front end.
    """
    # Get existing portfolio
    file = None
    if request.FILES.get("file"):
        file = request.FILES["file"]
    try:
        df_portfolio = pd.read_csv(file)

        # Replace the position to 0 if there is Exit Price
        if "Exit Price" in df_portfolio.columns:
            df_portfolio.loc[df_portfolio["Exit Price"].notna(), "Position"] = 0

        df_portfolio = df_portfolio[["Financial Instrument", "Position"]]
        df_portfolio["Financial Instrument"] = (
            df_portfolio["Financial Instrument"].str.split(" ").str[0]
        )
        replace_position = {"K": 1000, "M": 1000000, "'": "", ",": ""}
        df_portfolio["Position"] = df_portfolio["Position"].replace(np.nan, 0)
        df_portfolio["Position"] = (
            df_portfolio["Position"].replace(replace_position, regex=True).astype(int)
        )
        df_portfolio.rename(
            columns={"Financial Instrument": "Ticker", "Position": "Existing Position"},
            inplace=True,
        )
    except Exception as e:
        logging.warning(f"Error: {e}")
        df_portfolio = pd.DataFrame(columns=["Ticker", "Existing Position"])

    # Get top and bottom stocks from backtest results
    data = json.loads(request.POST["table_data"])

    # Convert to dataframe for top stocks
    amount = abs(int(request.POST["amount"]))
    df_top_stocks = convert_backtest_table_to_dataframe(data["long_table"], amount)
    df_bottom_stocks = convert_backtest_table_to_dataframe(data["short_table"], amount)
    df_bottom_stocks["Expected Position"] = -df_bottom_stocks["Expected Position"]

    # Calculate execute position (to close the unnecessary positions from existing positions)
    df_execute = pd.concat([df_top_stocks, df_bottom_stocks], ignore_index=True)
    df_execute = pd.merge(df_execute, df_portfolio, on="Ticker", how="outer")
    df_execute["Existing Position"] = (
        df_execute["Existing Position"].infer_objects(copy=False).fillna(0)
    )
    df_execute["Expected Position"] = (
        df_execute["Expected Position"].infer_objects(copy=False).fillna(0)
    )
    df_execute["Execute Position"] = (
        df_execute["Expected Position"].astype(float) - df_execute["Existing Position"]
    )
    df_execute["Execute Position"] = df_execute["Execute Position"].round(2)
    df_execute = df_execute[["Ticker", "Execute Position"]]
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

    # Write csv response
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="basket_trader.csv"'
    writer = csv.writer(response)
    writer.writerow(basket_trader_cols)
    for index, row in df_basket_trader.iterrows():
        writer.writerow(row.tolist())

    return response


def convert_backtest_table_to_dataframe(tables: list, amount: int) -> pd.DataFrame:
    # loop through the first table and the second level of columns
    columns = []
    for col in tables[0][1]:
        # Replace the column 'Value' to the first level of columns of the first table (date string)
        columns.append(col) if col != "Value" else columns.append(tables[0][0].pop(0))

    # Append to dataframe
    df = pd.DataFrame(columns=columns)
    for table in tables:
        # Exclude the first 2 rows, they are column names
        df = pd.concat([df, pd.DataFrame(columns=columns, data=table[2:])])

    # Extract the last 3 columns (the latest re-balancing period)
    df = df.iloc[:, -3:]

    # Remove empty rows
    df = df[df["Ticker"] != ""]

    # Assign amount for each stock
    df["Amount(USD)"] = amount // 2 // len(df)

    # Get date string from df.columns
    def search_date_string(string: str) -> bool:
        pattern = r"^[A-Za-z]{3} \d{4}$"
        match = re.match(pattern, string)
        return bool(match)

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

    # Add it to the main dataframe
    df = df.merge(df_prev_close, on="Ticker")

    # Assign position for each stock
    df["Expected Position"] = df["Amount(USD)"] / df["Prev Close"]

    return df


# todo: peer review