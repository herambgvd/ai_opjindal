import logging
from datetime import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from django.utils import timezone

from ..forms import DailyAnalysisForm, ComparativeAnalysisForm, ComprehensiveAnalysisForm
from ..models import Region
from ..utils import TablePartitioningManager

logger = logging.getLogger('cross_counting.views')


@login_required(login_url="account_login")
def daily_analysis(request):
    form = DailyAnalysisForm(request.GET or None)
    analysis_data = None
    
    if form.is_valid():
        try:
            region = form.cleaned_data['region']
            date = form.cleaned_data['date']
            
            analysis_data = TablePartitioningManager.get_daily_analysis_data(
                region.id, date
            )
            analysis_data['region'] = region
            analysis_data['date'] = date
            
            logger.info(f"Daily analysis generated for region {region.name} on {date}")
            
        except Exception as e:
            logger.error(f"Error generating daily analysis: {e}")
            messages.error(request, "An error occurred while generating the analysis.")
    
    context = {
        'form': form,
        'analysis_data': analysis_data,
        'title': 'Daily Analysis'
    }
    return render(request, 'cross_counting/analysis/daily.html', context)


@login_required(login_url="account_login")
def comparative_analysis(request):
    form = ComparativeAnalysisForm(request.GET or None)
    analysis_data = None
    
    if form.is_valid():
        try:
            region = form.cleaned_data['region']
            base_date = form.cleaned_data['base_date']
            compare_date = form.cleaned_data['compare_date']
            
            analysis_data = TablePartitioningManager.get_comparative_analysis_data(
                region.id, base_date, compare_date
            )
            analysis_data['region'] = region
            
            logger.info(f"Comparative analysis generated for region {region.name}")
            
        except Exception as e:
            logger.error(f"Error generating comparative analysis: {e}")
            messages.error(request, "An error occurred while generating the analysis.")
    
    context = {
        'form': form,
        'analysis_data': analysis_data,
        'title': 'Comparative Analysis'
    }
    return render(request, 'cross_counting/analysis/comparative.html', context)


@login_required(login_url="account_login")
def comprehensive_analysis(request):
    form = ComprehensiveAnalysisForm(request.GET or None)
    analysis_data = None
    
    if form.is_valid():
        try:
            region = form.cleaned_data['region']
            from_date = form.cleaned_data['from_date']
            to_date = form.cleaned_data['to_date']
            
            analysis_data = TablePartitioningManager.get_comprehensive_analysis_data(
                region.id, from_date, to_date
            )
            analysis_data['region'] = region
            
            logger.info(f"Comprehensive analysis generated for region {region.name}")
            
        except Exception as e:
            logger.error(f"Error generating comprehensive analysis: {e}")
            messages.error(request, "An error occurred while generating the analysis.")
    
    context = {
        'form': form,
        'analysis_data': analysis_data,
        'title': 'Comprehensive Analysis'
    }
    return render(request, 'cross_counting/analysis/comprehensive.html', context)
