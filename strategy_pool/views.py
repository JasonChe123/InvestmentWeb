from django.shortcuts import render


def home(request):
    strategies = [
        {
            "name": "Long-Short Equity Strategy",
            "description": "A strategy that comprised of taking long positions anticipated to rise in share price, paired with short-selling to mitigate downside risk.",
            "link": "longshort-backtest",
            "coming_soon": False,
        },
        # todo: Strategies coming soon
        # {
        #     "name": "Momentum Strategy",
        #     "description": "A strategy that buys assets with strong recent performance and sells those with weak performance.",
        #     "link": "",
        #     "coming_soon": True,
        # },
        # {
        #     "name": "Mean Reversion Strategy",
        #     "description": "A strategy that capitalizes on the tendency of prices to revert to their historical averages.",
        #     "link": "",
        #     "coming_soon": True,
        # },
        # {
        #     "name": "Arbitrage Strategy",
        #     "description": "A strategy that exploits price differences between markets or instruments.",
        #     "link": "",
        #     "coming_soon": True,
        # },
        # {
        #     "name": "Trend Following Strategy",
        #     "description": "A strategy that identifies and follows the direction of market trends.",
        #     "link": "",
        #     "coming_soon": True,
        # },
        # {
        #     "name": "Pairs Trading Strategy",
        #     "description": "A strategy that trades two correlated assets to profit from their relative price movements.",
        #     "link": "",
        #     "coming_soon": True,
        # },
    ]

    context = {
        "strategies": strategies,
    }

    return render(request, "strategy_pool/index.html", context)
