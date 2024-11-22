import datetime as dt
from calendar import monthrange
from django.contrib import messages
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render
from django.views import View
import json
import logging
import numpy as np
import pandas as pd
import re
from typing import Tuple
from .models import Stock, FinancialReport, BalanceSheet, CashFlow, CandleStick

market_cap = {
    'Mega (>$200B)': 200_000_000_000,
    'Large ($10B-$200B)': range(10_000_000_000, 20_000_000_001),
    'Medium ($2B-$10B)': range(2_000_000_000, 10_000_000_001),
    'Small ($300M-$2B)': range(300_000_000, 2_000_000_001),
    'Micro ($50M-$300M)': range(50_000_000, 300_000_001),
    'Nano (<$50M)': range(0, 50_000_001),
}


class DashboardView(View):
    def get(self, request):
        return render(request, 'long_short/index.html')


class BackTestView(View):
    def __init__(self):
        super().__init__()

        # Initialize parameter: market cap
        self.market_cap = market_cap

        # # Initialize parameter: fundamental data
        self.financials_data = [separate_words(field.name) for field in FinancialReport._meta.get_fields() if
                                field.concrete and field.name not in ('id', 'stock', 'date')]
        self.balance_sheet_data = [separate_words(field.name) for field in BalanceSheet._meta.get_fields() if
                                   field.concrete and field.name not in ('id', 'stock', 'date')]
        self.cash_flow_data = [separate_words(field.name) for field in CashFlow._meta.get_fields() if
                               field.concrete and field.name not in ('id', 'stock', 'date')]

        # # Initialize other parameters
        self.ipo_years = [5, 4, 3, 2, 1]
        self.sectors = ['Basic Materials', 'Technology', 'Industrials', 'Health Care', 'Energy',
                        'Consumer Discretionary', 'Real Estate', 'Miscellaneous', 'Telecommunications',
                        'Consumer Staples', 'Utilities', 'Finance']
        self.sectors.sort()
        self.backtest_years = [1.5, 1]
        self.pos_hold = [50, 40, 30, 20, 10]
        self.re_balancing_months = [
            'Jan, Apr, Jul, Oct',
            'Feb, May, Aug, Nov',
            'Mar, Jun, Sep, Dec',
        ]

        # Setup html context
        self.html_context = {
            'methods_financial': self.financials_data,
            'methods_balance_sheet': self.balance_sheet_data,
            'methods_cash_flow': self.cash_flow_data,
            'market_cap': self.market_cap.keys(),
            'ipo_years': self.ipo_years,
            'sectors': self.sectors,
            'backtest_years': self.backtest_years,
            'pos_hold': self.pos_hold,
        }

    def get(self, request):
        # Default parameters
        self.html_context['selected_market_cap'] = list(self.market_cap.keys())[:3]
        self.html_context['selected_ipo_years'] = 1
        self.html_context['selected_backtest_years'] = 1.5
        self.html_context['selected_pos_hold'] = 30
        self.html_context['selected_ranking_method'] = 'Descending'

        return render(request, 'long_short/backtest.html', self.html_context)

    def post(self, request):
        # Get user's parameters
        market_cap = request.POST.getlist('market_cap')
        method = request.POST.get('selected_method').rstrip("+-*/")
        ipo_years = int(request.POST.get('ipo_years'))
        sector = request.POST.get('sectors')
        backtest_years = float(request.POST.get('backtest_years'))
        pos_hold = int(request.POST.get('pos_hold'))
        ranking_method = request.POST.get('ranking_method')

        # Add to context
        self.html_context['selected_market_cap'] = market_cap
        self.html_context['selected_method'] = method
        self.html_context['selected_ipo_years'] = ipo_years
        self.html_context['selected_sectors'] = sector
        self.html_context['selected_backtest_years'] = backtest_years
        self.html_context['selected_pos_hold'] = pos_hold
        self.html_context['selected_ranking_method'] = ranking_method

        # Check input validity
        if not market_cap:
            messages.warning(request, 'Please select Market Cap.')
            return render(request, 'long_short/backtest.html', self.html_context)
        if not method:
            messages.warning(request, 'Please select Method.')
            return render(request, 'long_short/backtest.html', self.html_context)
        if method.count('(') != method.count(')'):
            messages.warning(request, 'Your method is not valid, please check.')
            return render(request, 'long_short/backtest.html', self.html_context)

        # Get US stocks
        df_us_stocks = get_us_stocks(market_cap, ipo_years, [sector, ])
        if len(df_us_stocks) == 0:
            messages.warning(request, 'No stocks found, please adjust your filter.')
            return render(request, 'long_short/backtest.html', self.html_context)

        # Get re-balancing dates
        l_re_balancing_dates = get_re_balancing_dates(self.re_balancing_months[2], backtest_years)

        # Get result by method chose
        results = get_result_from_method(
            method, df_us_stocks, l_re_balancing_dates,
            self.financials_data, self.balance_sheet_data, self.cash_flow_data
        )

        # Ranking and split results
        result_subset = rank_and_split(results, ranking_method)

        # Get performance for each re-balancing date
        df_top, df_bottom = get_performance(result_subset, method, pos_hold)
        if df_top.empty or df_bottom.empty:
            messages.warning(request, "No financial data available, please adjust your filter.")

        # Add average performance to the top stocks, and bottom stocks
        get_average_performance(df_top)
        get_average_performance(df_bottom)

        # Calculate total performance for long and short stocks
        total_performance_long = df_top.iloc[-1].sum(skipna=True)
        total_performance_short = df_bottom.iloc[-1].sum(skipna=True)

        # Format dataframe
        for df in (df_top, df_bottom):
            df.rename(columns={'Performance': 'Perf(%)'}, inplace=True)
            df.replace(np.nan, "", inplace=True)

        # Round to 2 decimals
        df_top = df_top.map(lambda x: round(x, 2) if isinstance(x, (int, float)) else x)
        df_bottom = df_bottom.map(lambda x: round(x, 2) if isinstance(x, (int, float)) else x)

        # Rename column names from 'result-%b %y' to '%m/%y-%m/%y'
        rename_cols = {}
        for col in df_top.columns:
            if 'result-' in col:
                from_date = extract_date_suffix(col)
                to_month = from_date.month + 2
                if to_month > 12:
                    to_date = from_date.replace(year=from_date.year + 1, month=to_month - 12)
                else:
                    to_date = from_date.replace(month=to_month)
                rename_cols[col] = f'{from_date.strftime("%m/%y")} - {to_date.strftime("%m/%y")}'
        df_top.rename(columns=rename_cols, inplace=True)
        df_bottom.rename(columns=rename_cols, inplace=True)

        # Change unit
        def divide_columns(df, divisor, column_contains):
            # Select columns that match the pattern
            cols = df.columns[df.columns.str.contains(column_contains)]

            # Divide the selected columns by the divisor
            df[cols] = df[cols].map(
                lambda x: round(x / divisor, 2) if isinstance(x, (int, float)) and not np.isnan(x) else x
            )

            return df

        max_value = max(pd.to_numeric(df_top.loc[0], errors='coerce').dropna())
        for df in (df_top, df_bottom):
            if max_value > 1_000_000_000:
                divide_columns(df, 1_000_000_000, '-')
            elif max_value > 1_000_000:
                divide_columns(df, 1_000_000, '-')
            elif max_value > 1_000:
                divide_columns(df, 1_000, '-')

        # Set html context
        self.html_context['df_top'] = df_top
        self.html_context['df_bottom'] = df_bottom
        self.html_context['long_total'] = round(total_performance_long, 2)
        self.html_context['short_total'] = round(total_performance_short, 2)

        return render(request, 'long_short/backtest.html', self.html_context)


def separate_words(string: str) -> str:
    """
    To separate words, e.g. from 'ResearchAndDevelopment' to 'Research And Development'
    """
    return re.sub(r"(?<![A-Z])(?=[A-Z])", " ", string).strip()


def get_us_stocks(selected_market_cap: list, min_ipo_years: int, sectors: list) -> pd.DataFrame:
    """
    Return us stocks based on selected market cap, min ipo years, and sectors.
    """
    market_cap_str = list(market_cap.keys())
    market_cap_value = list(market_cap.values())

    # Get selected market cap
    mega = market_cap_str[0] in selected_market_cap
    large = market_cap_str[1] in selected_market_cap
    medium = market_cap_str[2] in selected_market_cap
    small = market_cap_str[3] in selected_market_cap
    micro = market_cap_str[4] in selected_market_cap
    nano = market_cap_str[5] in selected_market_cap

    # Define query
    mega_q = Q(market_cap__gte=market_cap_value[0]) if mega else Q()
    large_q = Q(market_cap__range=[market_cap_value[1][0], market_cap_value[1][-1]]) if large else Q()
    medium_q = Q(market_cap__range=[market_cap_value[2][0], market_cap_value[2][-1]]) if medium else Q()
    small_q = Q(market_cap__range=[market_cap_value[3][0], market_cap_value[3][-1]]) if small else Q()
    micro_q = Q(market_cap__range=[market_cap_value[4][0], market_cap_value[4][-1]]) if micro else Q()
    nano_q = Q(market_cap__range=[market_cap_value[5][0], market_cap_value[5][-1]]) if nano else Q()

    # Query database
    results = Stock.objects.filter(
        (mega_q | large_q | medium_q | small_q | micro_q | nano_q),
        ipo_year__lte=dt.datetime.today().year - min_ipo_years,
        sector__in=sectors
    )

    # Convert to dataframe
    results = pd.DataFrame(results.values())
    results.rename(columns={'ticker': 'Ticker'}, inplace=True)

    return results


def get_re_balancing_dates(re_balancing_months: str, backtest_years: float = 1) -> list:
    # Convert string to a list: 'Jan, Apr, Jul, Nov' -> ['Jan', ' Apr', ' Jul', ' Nov']
    re_balancing_months = re_balancing_months.split(',')

    # Convert string to int: ['Jan', ' Apr', ' Jul', ' Nov'] -> [1, 4, 7, 11]
    for i, d in enumerate(re_balancing_months):
        re_balancing_months[i] = dt.datetime.strptime(d.strip(), '%b').month

    # Get first re-balancing date: (today minus backtest_year)
    backtest_from = dt.datetime.now() - dt.timedelta(days=365 * backtest_years)

    # Define backtest_from
    if backtest_from.month > re_balancing_months[-1]:
        backtest_from = backtest_from.replace(month=re_balancing_months[-1], day=1).date()
    else:
        for month in re_balancing_months:
            if backtest_from.month <= month:
                backtest_from = backtest_from.replace(month=month, day=1).date()
                break

    # Re-order re-balancing month. E.g. if re-balancing month is November, the selected months will be [2, 5, 8, 11], then change the order to [11, 2, 5, 8]
    new_re_balancing_months = []
    for i, v in enumerate(re_balancing_months):
        if backtest_from.month == v:
            new_re_balancing_months = re_balancing_months[i:] + re_balancing_months[:i]
            break

    # Get a list of re-balancing date
    re_balancing_dates = []
    while backtest_from.year <= dt.datetime.now().year:
        for m in new_re_balancing_months:
            if backtest_from > dt.date.today():
                break
            re_balancing_dates.append(backtest_from.replace(month=m))
            if m == re_balancing_months[-1]:
                backtest_from = backtest_from.replace(year=backtest_from.year + 1)

    return re_balancing_dates


def get_result_from_method(formula: str,
                           us_stocks: pd.DataFrame,
                           re_balancing_dates: list,
                           financials_data: list,  # ['Basic EPS', 'EPS', ...]
                           balance_sheet_data: list,
                           cash_flow_data: list) -> pd.DataFrame:
    # Extract data name from method
    datas = re.findall(r'\w+(?:\s+\w+)*', formula)

    # Setup columns and Initialize result
    result = us_stocks[['Ticker']].copy()

    # Loop through re-balancing dates
    for date in re_balancing_dates:
        # Get report date (1 month before the re-balancing date)
        report_date = date.replace(month=date.month - 2, day=monthrange(date.year, date.month - 2)[-1])

        # Initialize data columns
        for data in datas:
            result[data] = np.nan

        # Loop through stocks
        for index, row in result.iterrows():
            stock = Stock.objects.get(ticker=row['Ticker'])

            # Loop through methods
            for data in datas:
                # Data name aligns with the database
                data_db = data.replace(' ', '').strip()

                if data in financials_data:
                    report = FinancialReport.objects.filter(stock=stock, date=report_date)
                    if not report: continue
                elif data in balance_sheet_data:
                    report = BalanceSheet.objects.filter(stock=stock, date=report_date)
                    if not report: continue
                elif data in cash_flow_data:
                    report = CashFlow.objects.filter(stock=stock, date=report_date)
                    if not report: continue
                else:
                    continue

                # Set data
                value = getattr(report.first(), data_db)
                if value:
                    result.loc[index, data] = float(value)
                else:
                    result.loc[index, data] = np.nan

        # Calculate result
        result_col_name = f'result-{dt.date.strftime(date, "%b %y")}'
        result = apply_formula(result, formula, result_col_name)

        # Delete data columns
        result.drop(columns=datas, inplace=True)

    return result


def apply_formula(df: pd.DataFrame, formula: str, result_col_name: str) -> pd.DataFrame:
    # Replace columns names
    for col in df.columns:
        formula = formula.replace(col, f'df["{col}"]')

    # Evaluate
    df[result_col_name] = eval(formula)

    return df


def search_method(request):
    """
    Search the method in Income Statement, Balance Sheet and Cash Flow, and return to the front-end.
    :param request: Request
    :return: {result: [method1, method2, ...]}
    """
    if request.method == 'POST':
        search_str = json.loads(request.body).get('search_text')
        if search_str.strip() == '':
            return JsonResponse({'result': []})

        fields_financials = [separate_words(field.name) for field in FinancialReport._meta.get_fields() if
                             field.concrete and field.name not in ('id', 'stock', 'date')]
        fields_balancesheet = [separate_words(field.name) for field in BalanceSheet._meta.get_fields() if
                               field.concrete and field.name not in ('id', 'stock', 'date')]
        fields_cashflow = [separate_words(field.name) for field in CashFlow._meta.get_fields() if
                           field.concrete and field.name not in ('id', 'stock', 'date')]
        all_fields = fields_financials + fields_balancesheet + fields_cashflow
        results = [method for method in all_fields if search_str.lower() in method.lower()]

        return JsonResponse({'result': results})


def rank_and_split(results: pd.DataFrame, ranking_method: str) -> dict:
    result_subset = {}
    result_cols = [col for col in results.columns if col.startswith('result')]
    ascending = True if ranking_method == 'Ascending' else False
    for col in result_cols:
        result = results[['Ticker', col]]
        result_subset[col] = result.sort_values(by=col, ascending=ascending)
        result_subset[col].dropna(inplace=True, subset=[col])

    return result_subset


def get_performance(result_subset: dict, method: str, pos_hold: int) -> Tuple[pd.DataFrame, pd.DataFrame]:
    # Setup from_month
    this_month = f"result-{dt.date.strftime(dt.date.today(), '%b %y')}"
    l_from_months = list(result_subset.keys())
    l_to_months = l_from_months[1:] + [this_month]

    # Loop through all periods
    for from_month, to_month in zip(l_from_months, l_to_months):
        # Initialize dataframe
        df = result_subset[from_month]
        df['Performance'] = np.nan

        # Format start_date and end_date: result-May 23 -> 2023-05-01
        start_date = extract_date_suffix(from_month).replace(tzinfo=dt.timezone.utc)
        end_date = extract_date_suffix(to_month).replace(tzinfo=dt.timezone.utc)
        # In case of today == from_month
        if start_date == end_date:
            end_date = dt.datetime.today().replace(tzinfo=dt.timezone.utc)

        # Extract top and bottom stocks
        half_rows_num = min(pos_hold, len(df) // 2)
        df = pd.concat([df.head(half_rows_num), df.tail(half_rows_num)])

        # Get performance change for each symbol
        for i, row in df.iterrows():
            stock = Stock.objects.get(ticker=row['Ticker'])
            candlesticks = CandleStick.objects.filter(stock=stock, date__gte=start_date, date__lte=end_date)
            if not candlesticks:
                continue

            # Candlestick data may too far away from re-balancing date
            candlestick_start_date = candlesticks.first().date
            candlestick_end_date = candlesticks.last().date
            if candlestick_start_date > start_date + dt.timedelta(days=30) or \
                    candlestick_end_date < end_date - dt.timedelta(days=30):
                logging.warning(f"[ {row['Ticker']} ] Candlestick data is too far away.")
                continue

            # Calculate performance
            price_from = float(candlesticks.first().open)
            price_to = float(candlesticks.last().adj_close)
            df.at[i, 'Performance'] = (price_to / price_from - 1) * 100

        # Add result to subset
        result_subset[from_month] = df

    # Combine results
    df_top = pd.DataFrame()
    df_bottom = pd.DataFrame()
    for key, result in result_subset.items():
        result.dropna(inplace=True)
        half_rows_num = min(pos_hold, len(result) // 2)

        # Add top stocks
        df_top_new = result.head(half_rows_num)
        df_top_new.reset_index(inplace=True, drop=True)
        df_top.reset_index(inplace=True, drop=True)
        df_top = pd.concat([df_top, df_top_new], axis=1)

        # Add bottom stocks
        df_bottom_new = result.tail(half_rows_num)
        df_bottom_new.reset_index(inplace=True, drop=True)
        df_bottom.reset_index(inplace=True, drop=True)
        df_bottom = pd.concat([df_bottom, df_bottom_new], axis=1)

    return df_top, df_bottom


def get_average_performance(df: pd.DataFrame):
    # Save original columns first, then deal with duplicate columns
    original_cols = df.columns.copy()

    # Rename all columns
    df.columns = [f'col_{i}' for i in range(len(df.columns))]

    # Add mean row
    mean_row = df.select_dtypes(include=[np.number]).mean()
    df.loc['Average'] = mean_row

    # Restore original columns
    df.columns = original_cols

    # Remove values in the mean row except all performance columns
    non_performance_cols = [col for col in df.columns if col != 'Performance' and col != 'Ticker']
    df.loc['Average', non_performance_cols] = np.nan


def extract_date_suffix(date_str: str) -> dt.datetime | None:
    date_pattern = re.compile(r'-(\w+ \d{2})$')
    match = date_pattern.search(date_str)

    return dt.datetime.strptime(match.group(1), '%b %y') if match else None
