from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import get_user_model
from analytics.services.health import get_asset_health, get_return_health, get_security_health, get_session_health, get_site_structure_health, get_user_health


User = get_user_model()


class HealthOverviewView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({
            "structure": get_site_structure_health(),
            "users": get_user_health(),
            "assets": get_asset_health(),
            "sessions": get_session_health(),
            "security": get_security_health(),
            "returns": get_return_health(),
        })
    
class SiteStructureHealthView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(get_site_structure_health())

class UserHealthView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(get_user_health())
    
class SessionHealthView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(get_session_health())
    

class SecurityHealthView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(get_security_health())


class AssetHealthView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(get_asset_health())

class ReturnHealthOverviewView(APIView):
    """
    Health signals for return request workflow.

    Highlights:
    - backlog (pending requests/items)
    - delays (old unprocessed requests)
    - quality issues (denials, partials)
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(get_return_health())