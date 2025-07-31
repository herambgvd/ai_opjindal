import logging

from django.contrib.auth.decorators import login_required
from django.shortcuts import render

logger = logging.getLogger('cross_counting.views')


@login_required(login_url="account_login")
def region_list(request):
    context = {}
    return render(request, 'cross_counting/region/main.html', context)


@login_required(login_url="account_login")
def region_create(request):
    context = {}
    return render(request, 'cross_counting/region/region_create.html', context)


@login_required(login_url="account_login")
def region_update(request, region_id):
    context = {}
    return render(request, 'cross_counting/region/region_update.html', context)


@login_required(login_url="account_login")
def region_delete(request, region_id):
    return render(request, 'cross_counting/region/region_delete_conf.html', context)
