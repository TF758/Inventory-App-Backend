from django.urls import path, include
from inventory_metrics.views import *

urlpatterns = [

    path('user-summary/', user_summary_report, name='user-summary-report'),




]