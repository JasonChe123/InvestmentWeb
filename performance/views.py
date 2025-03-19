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

        # Append datac
        grouped_portfolio[p.group_name]["data"].append(
            {
                "financial_instrument": p.financial_instrument,
                "position": p.position,
                "avg_price": p.avg_price,
                "last_price": p.last_price,
                "exit_price": p.exit_price,
            }
        )

    # Prepare context
    context = {}
    processed_portfolio = []

    for group_name, data in grouped_portfolio.items():
        df_portfolio = pd.DataFrame(data["data"])

        # # Set average prices
        df_portfolio = set_default_average_prices(df_portfolio, data["created_on"])
        # todo: to be deleted
        # if request.GET.get("default_open_prices") == "Open Prices":
        #     df_portfolio = set_default_average_prices(df_portfolio, data["created_on"])
        #     context = {"default_prices": "Open Prices"}
        # else:
        #     context = {"default_prices": "Dealt Prices"}

        df_positive, df_negative, mean_positive, mean_negative = data_cleaning(
            df_portfolio
        )
        df_negative["Cost"] = abs(df_negative["Cost"])
        init_cost_positive = int(df_positive["Cost"].sum())
        init_cost_negative = int(df_negative["Cost"].sum())
        df_positive = df_positive.replace(np.nan, 0)
        df_negative = df_negative.replace(np.nan, 0)
        df_positive["Exit Price"].replace(0, "", inplace=True)
        df_negative["Exit Price"].replace(0, "", inplace=True)
        # total_performance = round((df_positive['Profit'].sum() + df_negative['Profit'].sum()) /
        #                           (init_cost_positive + init_cost_negative) * 100, 2)
        total_performance = round(
            (df_positive["Profit"].sum() + df_negative["Profit"].sum())
            / max(init_cost_positive, init_cost_negative)
            * 100,
            2,
        )

        # Append to processed portfolio
        processed_portfolio.append(
            {
                "group_name": group_name,
                "created": dt.datetime.strftime(data["created_on"], "%d %b %Y"),
                "last_update": None,
                "positive": {
                    "df": df_positive,
                    "no_of_stocks": len(df_positive),
                    "initial_cost": init_cost_positive,
                    "mean_performance": mean_positive,
                    "profit": round(df_positive["Profit"].sum(), 2),
                },
                "negative": {
                    "df": df_negative,
                    "no_of_stocks": len(df_negative),
                    "initial_cost": init_cost_negative,
                    "mean_performance": mean_negative,
                    "profit": round(df_negative["Profit"].sum(), 2),
                },
                "total_performance": total_performance,
            }
        )

    context["portfolio"] = processed_portfolio

    return render(request, "performance/index.html", context)


@login_required
def add_portfolio(request):
    if request.method == "GET":
        return render(request, "performance/add_portfolio.html")
    elif request.method == "POST":
        return save_portfolio(request)


@login_required
@require_POST
def check_portfolio_name(request):
    portfolio_name = request.POST.get("portfolio_name", "")
    exists = Portfolio.objects.filter(
        user=request.user, group_name=portfolio_name
    ).exists()
    return JsonResponse({"exists": exists})


@login_required
@require_POST
def save_portfolio(request):
    try:
        error_message, portfolio = get_upload_portfolio(request)
        if error_message:
            messages.warning(request, error_message)
            return redirect("add_portfolio")
        portfolio_name = request.POST.get("portfolio_name")
        portfolio_positive, portfolio_negative, _, _ = data_cleaning(portfolio)

        with transaction.atomic():
            # Delete existing data for this user's portfolio
            Portfolio.objects.filter(
                user=request.user, group_name=portfolio_name
            ).delete()

            # Save new records
            performance_data = []
            for df in [portfolio_positive, portfolio_negative]:
                for _, row in df.iterrows():
                    if pd.notna(row["Exit Price"]):
                        performance_data.append(
                            Portfolio(
                                user=request.user,
                                group_name=portfolio_name,
                                financial_instrument=row["Ticker"],
                                position=row["Position"],
                                avg_price=row["Average Price"],
                                last_price=row["Last Price"],
                                exit_price=row["Exit Price"],
                            )
                        )
                    else:
                        performance_data.append(
                            Portfolio(
                                user=request.user,
                                group_name=portfolio_name,
                                financial_instrument=row["Ticker"],
                                position=row["Position"],
                                avg_price=row["Average Price"],
                                last_price=row["Last Price"],
                            )
                        )
            Portfolio.objects.bulk_create(performance_data)

        # Django messages
        messages.success(request, "Portfolio saved successfully.")

        return redirect("performance")
    except Exception as e:
        logging.error(f"Error saving performance: {str(e)}")
        messages.warning(request, "Error saving portfolio. Please check the file.")

        return redirect("performance")


@login_required
@require_POST
def edit_portfolio(request):
    # Get params
    portfolio_name = request.POST.get("portfolio_name")
    new_portfolio_name = request.POST.get("new_portfolio_name")
    file = request.FILES.get("portfolio_file")

    try:
        with transaction.atomic():
            if new_portfolio_name and new_portfolio_name.strip():
                if new_portfolio_name.strip() == portfolio_name:
                    messages.info(
                        request,
                        f"The new portfolio name '{new_portfolio_name}' is the same as the current one.",
                    )
                else:
                    # Update portfolio name
                    Portfolio.objects.filter(
                        user=request.user, group_name=portfolio_name
                    ).update(group_name=new_portfolio_name)
                    messages.success(
                        request,
                        f"The portfolio '{portfolio_name}' was renamed to '{new_portfolio_name}'.",
                    )
                    portfolio_name = new_portfolio_name

            if file:
                error_message, portfolio = get_upload_portfolio(request)
                if error_message:
                    messages.warning(request, error_message)
                    return JsonResponse({"status": "error"})

                portfolio_positive, portfolio_negative, _, _ = data_cleaning(portfolio)

                # Delete existing data for this user's portfolio
                Portfolio.objects.filter(
                    user=request.user, group_name=portfolio_name
                ).delete()

                # Save new records
                performance_data = []
                for df in [portfolio_positive, portfolio_negative]:
                    for _, row in df.iterrows():
                        if pd.notna(row["Exit Price"]):
                            performance_data.append(
                                Portfolio(
                                    user=request.user,
                                    group_name=portfolio_name,
                                    financial_instrument=row["Ticker"],
                                    position=row["Position"],
                                    avg_price=row["Average Price"],
                                    last_price=row["Last Price"],
                                    exit_price=row["Exit Price"],
                                )
                            )
                        else:
                            performance_data.append(
                                Portfolio(
                                    user=request.user,
                                    group_name=portfolio_name,
                                    financial_instrument=row["Ticker"],
                                    position=row["Position"],
                                    avg_price=row["Average Price"],
                                    last_price=row["Last Price"],
                                )
                            )

                Portfolio.objects.bulk_create(performance_data)
                messages.success(
                    request, f"Portfolio '{portfolio_name}' updated successfully."
                )

            return JsonResponse({"status": "success"})
    except Exception as e:
        logging.error(f"Error editing portfolio: {str(e)}")
        messages.warning(request, "Error editing portfolio. Please check the file.")
        return JsonResponse({"status": "error"})


@login_required
@require_POST
def delete_portfolio(request):
    try:
        data = json.loads(request.body)
        portfolio_name = data.get("portfolio_name")

        if not portfolio_name:
            return JsonResponse(
                {"status": "error", "message": "Portfolio name is required"}, status=400
            )

        # Delete the portfolio
        deleted_count, _ = Portfolio.objects.filter(
            user=request.user, group_name=portfolio_name
        ).delete()

        if deleted_count > 0:
            messages.success(
                request, f"Portfolio '{portfolio_name}' deleted successfully."
            )
            return JsonResponse(
                {
                    "status": "success",
                    "message": f"Portfolio '{portfolio_name}' deleted successfully.",
                    "redirect_url": reverse("performance"),
                }
            )
        else:
            return JsonResponse(
                {
                    "status": "error",
                    "message": f"No portfolio found with name '{portfolio_name}'",
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


def get_portfolio(request) -> pd.DataFrame:
    portfolio = Portfolio.objects.filter(user=request.user).order_by("group_name")
    return portfolio


def get_upload_portfolio(request) -> Tuple[str, pd.DataFrame]:
    uploaded_file = request.FILES.get("portfolio_file")
    # Empty file
    try:
        df = pd.read_csv(uploaded_file)
    except Exception as e:
        logging.warning(f"Error reading csv: {e}")
        message = "Something wrong, check the file."
        return message, None

    # Invalid rows
    df = df.dropna(subset=["Financial Instrument", "Position", "Avg Price"])

    # Invalid columns
    if not {"Financial Instrument", "Position", "Avg Price"}.issubset(df.columns):
        message = "The file must contain 'Financial Instrument', 'Position' and 'Avg Price' columns."
        return message, None

    if "Exit Price" not in df.columns:
        df["Exit Price"] = np.nan

    # Invalid data
    replace_format = {"K": 1000, "M": 1000000, "'": "", ",": ""}
    df["Position"] = df["Position"].replace(replace_format, regex=True)
    df["Avg Price"] = df["Avg Price"].replace(replace_format, regex=True)
    df["Exit Price"] = df["Exit Price"].replace(replace_format, regex=True)
    try:
        df["Position"] = df["Position"].astype(float)
        df["Avg Price"] = df["Avg Price"].astype(float)
        df["Exit Price"] = df["Exit Price"].astype(float)
    except ValueError:
        message = "Invalid data in Position/ Avg Price/ Exit Price columns, please check the file."
        return message, None

    # Invalid average price
    if 0 in df["Avg Price"].tolist():
        message = "The average price cannot be zero."
        return message, None

    # Extract ticker
    df["Financial Instrument"] = df["Financial Instrument"].str.split(" ").str[0]

    return "", df[["Financial Instrument", "Position", "Avg Price", "Exit Price"]]


def data_cleaning(df: pd.DataFrame):
    rename_columns = {
        "financial_instrument": "Ticker",
        "Financial Instrument": "Ticker",
        "position": "Position",
        "avg_price": "Average Price",
        "Avg Price": "Average Price",
        "last_price": "Last Price",
        "Last": "Last Price",
        "exit_price": "Exit Price",
        "performance_percentage": "Perf (%)",
    }
    df = df.rename(columns=rename_columns)
    df["Position"] = df["Position"].astype(float)
    df["Average Price"] = df["Average Price"].astype(float)
    df["Last Price"] = df["Ticker"].apply(get_last_close).astype(float)
    if "Exit Price" not in df.columns:
        df["Exit Price"] = None
    else:
        df["Exit Price"] = df["Exit Price"].astype(float)

    # Split into positive positions and negative positions
    df = df.sort_values("Position", ascending=True)
    df_positive = df.where(df["Position"] >= 0).dropna(subset=["Position"])
    df_negative = df.where(df["Position"] < 0).dropna(subset=["Position"])

    # Sort by ticker
    df_positive = df_positive.sort_values("Ticker", ascending=True)
    df_negative = df_negative.sort_values("Ticker", ascending=True)

    # Calculate performance percentage
    for df in [df_positive, df_negative]:
        df["Perf (%)"] = 0
        if df.empty:
            continue

        df["Perf (%)"] = np.where(
            pd.notnull(df["Exit Price"])
            & pd.to_numeric(df["Exit Price"], errors="coerce").notnull(),
            (df["Exit Price"] - df["Average Price"]) / df["Average Price"] * 100,
            (df["Last Price"] - df["Average Price"]) / df["Average Price"] * 100,
        )
        # df['Perf (%)'] = (df['Last Price'] - df['Average Price']) / df['Average Price'] * 100
        df["Perf (%)"] = df["Perf (%)"].round(2)

    df_negative["Perf (%)"] = -df_negative["Perf (%)"]

    # Calculate mean performance percentage
    mean_positive = get_mean_performance(df_positive)
    mean_negative = -get_mean_performance(df_negative)

    # Sort performance
    df_positive = df_positive.sort_values("Perf (%)", ascending=False)
    df_negative = df_negative.sort_values("Perf (%)", ascending=False)

    return df_positive, df_negative, mean_positive, mean_negative


def get_last_close(ticker: str) -> float:
    today = dt.datetime.today().replace(tzinfo=dt.timezone.utc)
    stock = Stock.objects.filter(ticker=ticker.strip())
    if not stock:
        logging.warning(f"[ {ticker} ] No stock data found.")
        return None

    stock = stock.first()
    candlesticks = CandleStick.objects.filter(
        stock=stock, 
        date__gte=today - dt.timedelta(days=30), 
        date__lte=today,
        close__isnull=False
    )
    if not candlesticks:
        logging.warning(f"[ {ticker} ] No candlestick data found.")
        return None

    value = candlesticks.last().close
    
    return round(value, 2) if value else None


def get_mean_performance(portfolio: pd.DataFrame) -> float:
    """It will create columns: 'Cost' and 'Profit'"""
    portfolio["Cost"] = portfolio["Position"] * portfolio["Average Price"]
    portfolio["Profit"] = np.where(
        pd.notnull(portfolio["Exit Price"])
        & pd.to_numeric(portfolio["Exit Price"], errors="coerce").notnull(),
        (portfolio["Exit Price"] - portfolio["Average Price"]) * portfolio["Position"],
        (portfolio["Last Price"] - portfolio["Average Price"]) * portfolio["Position"],
    )
    # portfolio['Profit'] = portfolio['Last Price'] * portfolio['Position'] - portfolio['Cost']
    mean = portfolio["Profit"].sum() / portfolio["Cost"].sum() * 100

    return round(mean, 2)


def set_default_average_prices(
    df_portfolio: pd.DataFrame, ref_date: dt.datetime
) -> pd.DataFrame:
    """
    Set average prices of df_portfolio as the open prices of ref_date.
    """
    df = df_portfolio.copy()
    stock_list = df["financial_instrument"].tolist()

    # Get candlesticks data
    query_res = CandleStick.objects.filter(
        stock__ticker__in=stock_list, date__lte=ref_date
    ).order_by("-date")

    # Create candlesticks dataframe
    df_candlesticks = pd.DataFrame(
        query_res.values(
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
