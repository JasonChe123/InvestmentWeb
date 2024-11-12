from django.shortcuts import render
from django.views import View


class FrontPageView(View):
    def get(self, request):
        return render(request, 'frontpage/index.html')
