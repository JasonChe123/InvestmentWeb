from django.shortcuts import render
from django.contrib import messages


def home(request):
    return render(request, 'frontpage/index.html')
