"""
URL configuration for inventory project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('core.api_urls')),
    path('analytics/', include('analytics.urls.analytics_url')),
    path('assets/', include('assets.urls.asset_urls')),
    path('assignments/', include('assignments.urls.assignment_urls')),
    path('reports/', include('reporting.urls.report_urls')),   
    path('sites/', include('sites.urls.site_urls')),   
    path('imports/', include('data_import.import_urls')),
    path('users/', include('users.urls.user_and_self_urls')),
    path('roles/', include('users.urls.role_urls')),

]
