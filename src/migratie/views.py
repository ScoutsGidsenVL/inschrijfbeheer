from django.shortcuts import render
from django.http import HttpResponse
from .models import EvenementStatus

def index(request):
    stat = EvenementStatus(
        beschrijving='testing1,2'
    )
    stat.save()
    return HttpResponse("Hello, world. You're at the polls index.")