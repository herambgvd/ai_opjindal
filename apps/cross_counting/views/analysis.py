import logging
import csv
import json
import uuid
from datetime import datetime, date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from django.core.serializers.json import DjangoJSONEncoder

from ..forms import DailyAnalysisForm, ComparativeAnalysisForm, ComprehensiveAnalysisForm
from ..models import Region
from ..utils import TablePartitioningManager

logger = logging.getLogger('cross_counting.views')


class CustomJSONEncoder(DjangoJSONEncoder):
    """
    Custom JSON encoder that handles UUID objects and other Django model fields
    """

    def default(self, obj):
        if isinstance(obj, uuid.UUID):
            return str(obj)
        elif isinstance(obj, (datetime, date)):
            return obj.isoformat()
        return super().default(obj)


def serialize_for_json(data):
    """
    Convert data to JSON string using custom encoder, then parse back to ensure clean data
    """
    json_string = json.dumps(data, cls=CustomJSONEncoder)
    return json.loads(json_string)


@login_required(login_url="account_login")
def daily_analysis(request):
    form = DailyAnalysisForm(request.GET or None)
    analysis_data = None

    if form.is_valid():
        try:
            region = form.cleaned_data['region']
            date = form.cleaned_data['date']

            raw_analysis_data = TablePartitioningManager.get_daily_analysis_data(
                region.id, date
            )

            # Serialize the data properly for JavaScript consumption
            analysis_data = serialize_for_json(raw_analysis_data)
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

            raw_analysis_data = TablePartitioningManager.get_comparative_analysis_data(
                region.id, base_date, compare_date
            )

            # Serialize the data properly for JavaScript consumption
            analysis_data = serialize_for_json(raw_analysis_data)
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

            raw_analysis_data = TablePartitioningManager.get_comprehensive_analysis_data(
                region.id, from_date, to_date
            )

            # Serialize the data properly for JavaScript consumption
            analysis_data = serialize_for_json(raw_analysis_data)
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


@login_required(login_url="account_login")
def daily_analysis_csv(request):
    form = DailyAnalysisForm(request.GET or None)

    if not form.is_valid():
        messages.error(request, "Invalid form data for CSV export.")
        return redirect('cross_counting:daily_analysis')

    try:
        region = form.cleaned_data['region']
        date = form.cleaned_data['date']

        analysis_data = TablePartitioningManager.get_daily_analysis_data(
            region.id, date
        )

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="daily_analysis_{region.name}_{date}.csv"'

        writer = csv.writer(response)
        writer.writerow(['Daily Analysis Report'])
        writer.writerow(['Region', region.name])
        writer.writerow(['Date', date])
        writer.writerow([])

        writer.writerow(['Summary'])
        writer.writerow(['Total Peak In', analysis_data['summary']['total_peak_in']])
        writer.writerow(['Total Peak Out', analysis_data['summary']['total_peak_out']])
        writer.writerow(['Total Peak Count', analysis_data['summary']['total_peak_total']])
        writer.writerow(['Active Cameras', analysis_data['summary']['active_cameras']])
        writer.writerow([])

        writer.writerow(['Camera-wise Peak Counts'])
        writer.writerow(['Camera Name', 'Peak In', 'Peak Out', 'Peak Total'])
        for camera in analysis_data['cameras']:
            writer.writerow([
                camera['camera_name'],
                camera['peak_in'],
                camera['peak_out'],
                camera['peak_total']
            ])

        logger.info(f"Daily analysis CSV exported for region {region.name} on {date}")
        return response

    except Exception as e:
        logger.error(f"Error exporting daily analysis CSV: {e}")
        messages.error(request, "An error occurred while exporting the CSV.")
        return redirect('cross_counting:daily_analysis')


@login_required(login_url="account_login")
def comparative_analysis_csv(request):
    form = ComparativeAnalysisForm(request.GET or None)

    if not form.is_valid():
        messages.error(request, "Invalid form data for CSV export.")
        return redirect('cross_counting:comparative_analysis')

    try:
        region = form.cleaned_data['region']
        base_date = form.cleaned_data['base_date']
        compare_date = form.cleaned_data['compare_date']

        analysis_data = TablePartitioningManager.get_comparative_analysis_data(
            region.id, base_date, compare_date
        )

        response = HttpResponse(content_type='text/csv')
        response[
            'Content-Disposition'] = f'attachment; filename="comparative_analysis_{region.name}_{base_date}_vs_{compare_date}.csv"'

        writer = csv.writer(response)
        writer.writerow(['Comparative Analysis Report'])
        writer.writerow(['Region', region.name])
        writer.writerow(['Base Date', base_date])
        writer.writerow(['Compare Date', compare_date])
        writer.writerow([])

        writer.writerow(['Camera-wise Comparison'])
        writer.writerow(
            ['Camera Name', 'Base In', 'Base Out', 'Base Total', 'Compare In', 'Compare Out', 'Compare Total',
             'Diff In', 'Diff Out', 'Diff Total'])
        for camera in analysis_data['comparison']:
            writer.writerow([
                camera['camera_name'],
                camera['base_in'],
                camera['base_out'],
                camera['base_total'],
                camera['compare_in'],
                camera['compare_out'],
                camera['compare_total'],
                camera['diff_in'],
                camera['diff_out'],
                camera['diff_total']
            ])

        logger.info(f"Comparative analysis CSV exported for region {region.name}")
        return response

    except Exception as e:
        logger.error(f"Error exporting comparative analysis CSV: {e}")
        messages.error(request, "An error occurred while exporting the CSV.")
        return redirect('cross_counting:comparative_analysis')


@login_required(login_url="account_login")
def comprehensive_analysis_csv(request):
    form = ComprehensiveAnalysisForm(request.GET or None)

    if not form.is_valid():
        messages.error(request, "Invalid form data for CSV export.")
        return redirect('cross_counting:comprehensive_analysis')

    try:
        region = form.cleaned_data['region']
        from_date = form.cleaned_data['from_date']
        to_date = form.cleaned_data['to_date']

        analysis_data = TablePartitioningManager.get_comprehensive_analysis_data(
            region.id, from_date, to_date
        )

        response = HttpResponse(content_type='text/csv')
        response[
            'Content-Disposition'] = f'attachment; filename="comprehensive_analysis_{region.name}_{from_date}_to_{to_date}.csv"'

        writer = csv.writer(response)
        writer.writerow(['Comprehensive Analysis Report'])
        writer.writerow(['Region', region.name])
        writer.writerow(['From Date', from_date])
        writer.writerow(['To Date', to_date])
        writer.writerow(['Total Days', analysis_data['total_days']])
        writer.writerow([])

        writer.writerow(['Daily Trends by Camera'])
        for camera_trend in analysis_data['daily_trends']:
            writer.writerow([])
            writer.writerow(['Camera', camera_trend['camera_name']])
            writer.writerow(['Date', 'Peak In', 'Peak Out', 'Peak Total'])
            for daily_data in camera_trend['daily_data']:
                writer.writerow([
                    daily_data['date'],
                    daily_data['peak_in_count'],
                    daily_data['peak_out_count'],
                    daily_data['peak_total_count']
                ])

        logger.info(f"Comprehensive analysis CSV exported for region {region.name}")
        return response

    except Exception as e:
        logger.error(f"Error exporting comprehensive analysis CSV: {e}")
        messages.error(request, "An error occurred while exporting the CSV.")
        return redirect('cross_counting:comprehensive_analysis')