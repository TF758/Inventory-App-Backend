from django.urls import path, include
from inventory_metrics.views import *

urlpatterns = [

    path('user-summary/', user_summary_report, name='user-summary-report'),
    path('site-assets/', site_asset_report, name='site-asset-report'),




]