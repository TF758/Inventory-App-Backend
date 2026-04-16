

from django.urls import path

from analytics.api.viewsets.health import AssetHealthView, HealthOverviewView, ReturnHealthOverviewView, SecurityHealthView, SessionHealthView, SiteStructureHealthView, UserHealthView


urlpatterns = [
    # Aggregated dashboard payload
    path("health-overview/", HealthOverviewView.as_view(), name="admin_health_overview"),

    # Individual health domains used to assess application status -  
    #can be be used for targetted assessment of specific area or used in dashboards.
    path("sites/", SiteStructureHealthView.as_view(), name="admin_health_sites"),
    path("users/", UserHealthView.as_view(), name="admin_health_users"),
    path("sessions/", SessionHealthView.as_view(), name="admin_health_sessions"),
    path("security/", SecurityHealthView.as_view(), name="admin_health_security"),
    path("assets/", AssetHealthView.as_view(), name="admin_health_assets"),
    path("returns/", ReturnHealthOverviewView.as_view(), name="admin_health_returns"),
]
