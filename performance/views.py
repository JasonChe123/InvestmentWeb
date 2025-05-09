import datetime as dt
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.urls import reverse
from django.views.decorators.http import require_POST, require_GET
import json
import logging
from manage_database.models import Stock, CandleStick
import numpy as np
import pandas as pd
from .models import Portfolio
from typing import Tuple


import pdb


@login_required
@require_GET
def home(request):
    # Get user's portfolio
    portfolio = get_portfolio(request)
    if not portfolio:
        return redirect("add_portfolio")

    # Consolidate data
    grouped_portfolio = {}
    # {
    #  'group_name': {'created_on': ''},
    #                 'data': [
    #                 {'financial_instrument': '',
    #                  'position': 0,
    #                  'avg_price': 0,
    #                  'last_price': 0,
    #                  'performance_percentage': 0
    #                  }, ...]
    #                },
    # 'group_name': {'created_on': '', 'data': [{...}, {...}, ...]}
    # }
    for p in portfolio:
        # Create group
        if p.group_name not in grouped_portfolio:
            grouped_portfolio[p.group_name] = {
                "created_on": p.created_at,
                "data": [],
            }

        # Append data
        grouped_portfolio[p.group_name]["data"].append(
            {
                "financial_instrument": p.financial_instrument,
                "position": p.position,
                "avg_price": p.avg_price,
                "last_price": p.last_price,
                # "exit_price": p.exit_price,
            }
        )

    # Prepare context
    context = {}
    processed_portfolio = []

    for group_name, data in grouped_portfolio.items():
        # Create dataframe
        df_portfolio = pd.DataFrame(data["data"])

        # Set open prices as average prices
        df_portfolio = set_default_average_prices(df_portfolio, data["created_on"])

        # Data cleaning
        df_long_position, df_short_position, mean_positive, mean_negative = (
            data_cleaning(df_portfolio)
        )

        # Append to processed_portfolio
        processed_portfolio.append(
            {
                "group_name": group_name,
                "created": dt.datetime.strftime(data["created_on"], "%d %b %Y"),
                "last_update": None,
                "positive": {
                    "df": df_long_position,
                    "no_of_stocks": len(df_long_position),
                    "initial_cost": int(df_long_position["Cost"].sum()),
                    "mean_performance": mean_positive,
                    "profit": round(df_long_position["Profit"].sum(), 2),
                },
                "negative": {
                    "df": df_short_position,
                    "no_of_stocks": len(df_short_position),
                    "initial_cost": int(abs(df_short_position["Cost"].sum())),
                    "mean_performance": mean_negative,
                    "profit": round(df_short_position["Profit"].sum(), 2),
                },
                "total_performance": get_total_performance(
                    df_long_position, df_short_position
                ),
            }
        )

    context["portfolio"] = processed_portfolio

    return render(request, "performance/index.html", context)


@login_required
def add_portfolio(request):
    """Handle events from 'add portfolio' page."""
    if request.method == "GET":
        return render(request, "performance/add_portfolio.html")
    elif request.method == "POST":
        return save_portfolio(request, request.POST.get("portfolio_name"))


@login_required
@require_POST
def check_portfolio_name(request):
    """Ajax request to check the existence of portfolio name in database"""
    group_name = request.POST.get("portfolio_name", "")
    exists = Portfolio.objects.filter(user=request.user, group_name=group_name).exists()

    return JsonResponse({"exists": exists})


@login_required
@require_POST
def delete_portfolio(request):
    "Post request from frontend, to delete data from database."
    try:
        data = json.loads(request.body)
        group_name = data.get("portfolio_name")

        # Validate group name
        if not group_name:
            return JsonResponse(
                {"status": "error", "message": "Portfolio name is required"}, status=400
            )

        # Delete the group
        deleted_count, _ = Portfolio.objects.filter(
            user=request.user, group_name=group_name
        ).delete()

        # Success deleting
        if deleted_count > 0:
            messages.success(request, f"Portfolio '{group_name}' deleted successfully.")

            return JsonResponse(
                {
                    "status": "success",
                    "message": f"Portfolio '{group_name}' deleted successfully.",
                    "redirect_url": reverse("performance"),
                }
            )

        # Fail deleting
        else:
            return JsonResponse(
                {
                    "status": "error",
                    "message": f"No portfolio found with name '{group_name}'",
                },
                status=404,
            )

    except json.JSONDecodeError:
        return JsonResponse(
            {"status": "error", "message": "Invalid JSON data"}, status=400
        )

    except Exception as e:
        logging.error(f"Error deleting performance: {str(e)}")

        return JsonResponse(
            {
                "status": "error",
                "message": "An error occurred while deleting the portfolio",
            },
            status=500,
        )


@login_required
@require_POST
def edit_portfolio(request):
    """Edit portfolio name or position information from an existing portfolio."""
    # Get params
    group_name = request.POST.get("portfolio_name")
    new_group_name = request.POST.get("new_portfolio_name")
    file = request.FILES.get("portfolio_file")

    try:
        with transaction.atomic():
            if new_group_name and new_group_name.strip():
                if new_group_name.strip() == group_name:
                    messages.info(
                        request,
                        f"The new portfolio name '{new_group_name}' is the same as the current one.",
                    )
                else:
                    # Update portfolio name
                    Portfolio.objects.filter(
                        user=request.user, group_name=group_name
                    ).update(group_name=new_group_name)

                    # Success message
                    messages.success(
                        request,
                        f"The portfolio '{group_name}' was renamed to '{new_group_name}'.",
                    )
                    group_name = new_group_name

            if file:
                save_portfolio(request, group_name)

        return JsonResponse({"status": "success"})

    except Exception as e:
        logging.error(f"Error editing portfolio: {str(e)}")

        # Warning message
        messages.warning(request, "Error editing portfolio. Please check the file.")

        return JsonResponse({"status": "error"})


@login_required
@require_POST
def save_portfolio(request, group_name: str):
    """Save portfolio to database. Triggered by post request from 'add_portfolio()'."""
    try:
        # Get user uploaded portfolio
        error_message, portfolio = get_upload_portfolio(request)
        if error_message:
            messages.warning(request, error_message)
            return redirect("add_portfolio")

        # Data cleaning
        long_position, short_position, _, _ = data_cleaning(portfolio)

        # Save portfolio
        with transaction.atomic():
            save_portfolio_data(request.user, group_name, long_position, short_position)

        # Success messages
        messages.success(request, "Portfolio saved successfully.")

        return redirect("performance")

    except Exception as e:
        logging.error(f"Error saving performance: {str(e)}")

        # Warning message
        messages.warning(request, "Error saving portfolio. Please check the file.")

        return redirect("performance")


def data_cleaning(df: pd.DataFrame):
    """
    1. Rename column names
    2. Change datatype
    3. Divide data into long and short position
    4. Calculate performance and mean performance
    """
    # Rename column names
    rename_columns = {
        "financial_instrument": "Ticker",
        "Financial Instrument": "Ticker",
        "position": "Position",
        "avg_price": "Average Price",
        "Avg Price": "Average Price",
        "last_price": "Last Price",
        "Last": "Last Price",
        "performance_percentage": "Perf (%)",
    }
    df = df.rename(columns=rename_columns)

    # Change datatype
    df["Position"] = df["Position"].astype(float)
    df["Average Price"] = df["Average Price"].astype(float)
    df["Last Price"] = df["Ticker"].apply(get_last_close).astype(float)

    # Divide data into long and short position
    df = df.sort_values("Position", ascending=True)
    df_long = df.where(df["Position"] >= 0).dropna(subset=["Position"])
    df_short = df.where(df["Position"] < 0).dropna(subset=["Position"])

    # Sort by ticker
    df_long.sort_values("Ticker", ascending=True, inplace=True)
    df_short.sort_values("Ticker", ascending=True, inplace=True)

    # Calculate performance
    for df in [df_long, df_short]:
        df["Perf (%)"] = 0
        if df.empty:
            continue

        df["Perf (%)"] = (
            (df["Last Price"] - df["Average Price"]) / df["Average Price"] * 100
        )
        df["Perf (%)"] = df["Perf (%)"].round(2)

    # Reverse performance for short position
    df_short["Perf (%)"] = -df_short["Perf (%)"]

    # Calculate mean performance percentage
    mean_long = get_mean_performance(df_long)
    mean_short = -get_mean_performance(df_short)

    # Sort performance
    df_long = df_long.sort_values("Perf (%)", ascending=False)
    df_short = df_short.sort_values("Perf (%)", ascending=False)

    return df_long, df_short, mean_long, mean_short


def get_last_close(ticker: str) -> float:
    """Get the most updated closing price"""
    # Get stock
    stock = Stock.objects.filter(ticker=ticker.strip())
    if not stock:
        logging.warning(f"[ {ticker} ] No stock data found.")
        return None

    # Get candlesticks
    today = dt.datetime.today()
    candlesticks = CandleStick.objects.filter(
        stock=stock.first(),
        date__gte=today - dt.timedelta(days=30),
        date__lte=today,
        close__isnull=False,
    )
    if not candlesticks:
        logging.warning(f"[ {ticker} ] No candlestick data found.")
        return None

    value = candlesticks.last().close

    return round(value, 2) if value else None


def get_mean_performance(portfolio: pd.DataFrame) -> float:
    """Get mean performance and create columns: 'Cost' and 'Profit'"""
    portfolio["Cost"] = portfolio["Position"] * portfolio["Average Price"]
    portfolio["Profit"] = (
        portfolio["Last Price"] - portfolio["Average Price"]
    ) * portfolio["Position"]
    mean = portfolio["Profit"].sum() / portfolio["Cost"].sum() * 100

    return round(mean, 2)


def get_portfolio(request) -> pd.DataFrame:
    """Get portfolio objects."""
    portfolio = Portfolio.objects.filter(user=request.user).order_by("group_name")
    return portfolio


def get_total_performance(long_position: pd.DataFrame, short_position: pd.DataFrame):
    """Calculate total performance"""
    long_position.fillna(0, inplace=True)
    short_position.fillna(0, inplace=True)

    init_cost_positive = int(long_position["Cost"].sum())
    init_cost_negative = int(abs(short_position["Cost"].sum()))

    ttl_performance = round(
        (long_position["Profit"].sum() + short_position["Profit"].sum())
        / max(init_cost_positive, init_cost_negative)
        * 100,
        2,
    )

    return ttl_performance


def get_upload_portfolio(request) -> Tuple[str, pd.DataFrame]:
    """Get user uploaded portfolio and auto-formatting for number and symbol."""
    uploaded_file = request.FILES.get("portfolio_file")

    # Handling file reading error
    try:
        df = pd.read_csv(uploaded_file)
    except Exception as e:
        logging.warning(f"Error reading csv: {e}")
        message = "Something wrong, check the file."

        return message, None

    # Drop invalid rows
    df = df.dropna(subset=["Financial Instrument", "Position", "Avg Price"])

    # Validate column names
    if not {"Financial Instrument", "Position", "Avg Price"}.issubset(df.columns):
        message = "The file must contain 'Financial Instrument', 'Position' and 'Avg Price' columns."
        return message, None

    # Turn K, M to a number, delete thousand seperators and '
    replace_format = {
        "K": 1000,
        "M": 1000000,
        "k": 1000,
        "m": 1000000,
        "'": "",
        ",": "",
    }
    df["Position"] = df["Position"].replace(replace_format, regex=True)
    df["Avg Price"] = df["Avg Price"].replace(replace_format, regex=True)

    # Validate data type
    try:
        df["Position"] = df["Position"].astype(float)
        df["Avg Price"] = df["Avg Price"].astype(float)
    except ValueError:
        message = "Invalid data in Position/ Avg Price/ Exit Price columns, please check the file."
        return message, None

    # Validate average price
    if 0 in df["Avg Price"].tolist():
        message = "The average price cannot be zero."
        return message, None

    # Extract ticker (the first letter set of Financial Instrument)
    df["Financial Instrument"] = df["Financial Instrument"].str.split(" ").str[0]

    return "", df[["Financial Instrument", "Position", "Avg Price"]]


def save_portfolio_data(user, group_name, portfolio_positive, portfolio_negative):
    """Save portfolio data to database."""
    Portfolio.objects.filter(user=user, group_name=group_name).delete()
    data = []
    for df in [portfolio_positive, portfolio_negative]:
        for _, row in df.iterrows():
            data.append(
                Portfolio(
                    user=user,
                    group_name=group_name,
                    financial_instrument=row["Ticker"],
                    position=row["Position"],
                    avg_price=row["Average Price"],
                    last_price=row["Last Price"],
                )
            )

    Portfolio.objects.bulk_create(data)


def set_default_average_prices(
    df_portfolio: pd.DataFrame, ref_date: dt.datetime
) -> pd.DataFrame:
    """
    Set average prices of df_portfolio as the open prices of ref_date.
    """
    df = df_portfolio.copy()
    ref_date = ref_date.replace(hour=0, minute=0, second=0, microsecond=0)

    # Get stock list
    stock_list = df["financial_instrument"].tolist()

    # Get candlesticks data
    res = CandleStick.objects.filter(
        stock__ticker__in=stock_list,
        date__gte=ref_date
    ).order_by("date")

    # Create candlesticks dataframe
    df_candlesticks = pd.DataFrame(
        res.values(
            "stock__ticker",
            "date",
            "open",
        )
    ).drop_duplicates(subset="stock__ticker")

    # Rename columns to match df_portfolio
    df_candlesticks.rename(
        columns={"stock__ticker": "financial_instrument", "open": "avg_price"},
        inplace=True,
    )

    # Drop 'avg_price' column in df_portfolio
    df.drop(columns=["avg_price"], inplace=True)

    # Merge df_portfolio and df_candlesticks
    df = pd.merge(
        df,
        df_candlesticks[["financial_instrument", "avg_price"]],
        on="financial_instrument",
        how="left",
    )

    return df
