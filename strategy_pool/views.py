from django.shortcuts import render


def home(request):
    strategies = [
        {"name": "Momentum Strategy", "description": "A strategy that buys assets with strong recent performance and sells those with weak performance.", "coming_soon": False},
        {"name": "Mean Reversion Strategy", "description": "A strategy that capitalizes on the tendency of prices to revert to their historical averages.", "coming_soon": True},
        {"name": "Arbitrage Strategy", "description": "A strategy that exploits price differences between markets or instruments.", "coming_soon": False},
        {"name": "Trend Following Strategy", "description": "A strategy that identifies and follows the direction of market trends.", "coming_soon": True},
        {"name": "Pairs Trading Strategy", "description": "A strategy that trades two correlated assets to profit from their relative price movements.", "coming_soon": False},
    ]

    context = {
        'strategies': strategies,
    }

    return render(request, 'strategy_pool/index.html', context)