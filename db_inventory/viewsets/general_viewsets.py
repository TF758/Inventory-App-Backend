from rest_framework_simplejwt.views import TokenObtainPairView
from ..serializers.general import CustomTokenObtainPairSerializer, RoleSwitchSerializer, RoleListSerializer,  RoleReadSerializer, RoleWriteSerializer, SessionTokenLoginViewSerializer
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.generics import GenericAPIView, ListAPIView
from rest_framework_simplejwt.tokens import RefreshToken, TokenError
from rest_framework.permissions import IsAuthenticated
from ..models import RoleAssignment, User, UserSession
from rest_framework import viewsets
from django.utils import timezone
from datetime import timedelta
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework.views import APIView

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.user

        # Generate refresh token using serializer's get_token
        refresh = self.get_serializer_class().get_token(user)

        # Access token from refresh
        access_token = str(refresh.access_token)

        # Build response from serializer validated data
        response_data = serializer.validated_data.copy()
        response_data.pop("refresh", None)  # remove refresh from JSON
        response_data.pop("user_id", None)  # remove user_id if present
        response_data["access"] = access_token

        # Set refresh token as HttpOnly cookie
        response = Response(response_data, status=status.HTTP_200_OK)
        response.set_cookie(
            key="refresh",
            value=str(refresh),
            httponly=True,
            secure=True,
            samesite="None",
            path="/",
        )
       
        return response
    

class SessionTokenLoginView(TokenObtainPairView):
    serializer_class = SessionTokenLoginViewSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        # Authenticate user via serializer
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.user

        #Access token (JWT)
        access_token = str(AccessToken.for_user(user))

        # Opaque refresh token
        import secrets
        raw_refresh = secrets.token_urlsafe(64)
        hashed_refresh = UserSession.hash_token(raw_refresh)

       # Save session first
        session = UserSession.objects.create(
            user=user,
            refresh_token_hash=hashed_refresh,
            expires_at=timezone.localtime(timezone.now()) + timedelta(days=1),
            ip_address=request.META.get("REMOTE_ADDR"),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
        )

        # Access token (JWT) bound to session
        access_token_obj = AccessToken.for_user(user)
        access_token_obj["session_id"] = str(session.id)
        access_token = str(access_token_obj)

        # Build response including metadata
        response_data = {
            "access": access_token,
            "public_id": str(user.public_id),
            "role_id": user.active_role.public_id if user.active_role else None,
        }

        # Set refresh token as HttpOnly cookie
        response = Response(response_data, status=200)
        response.set_cookie(
            key="refresh",
            value=raw_refresh,
            httponly=True,
            secure=True,
            samesite="None",
            path="/",
        )

        return response

class RefreshAPIView(APIView):
    permission_classes = [AllowAny]          
    authentication_classes = []              

    def post(self, request):
        raw_refresh = request.COOKIES.get("refresh")
        if not raw_refresh:
            return Response({"detail": "No refresh token found."}, status=status.HTTP_400_BAD_REQUEST)

        hashed_refresh = UserSession.hash_token(raw_refresh)

        try:
            session = UserSession.objects.get(
                refresh_token_hash=hashed_refresh,
                status=UserSession.Status.ACTIVE,
                expires_at__gt=timezone.now()
            )
        except UserSession.DoesNotExist:
            return Response({"detail": "Invalid or expired session."}, status=status.HTTP_401_UNAUTHORIZED)

        # Issue new access token
        user = session.user
        access_token = AccessToken.for_user(user)
        access_token["public_id"] = str(user.public_id)
        access_token["session_id"] = str(session.id)
        access_token["role_id"] = user.active_role.public_id if user.active_role else None

        # Optionally rotate refresh token
        import secrets
        new_raw_refresh = secrets.token_urlsafe(64)
        session.refresh_token_hash = UserSession.hash_token(new_raw_refresh)
        session.expires_at = timezone.now() + timedelta(days=7)  # reset expiry
        session.save(update_fields=["refresh_token_hash", "expires_at"])

        response = Response(
            {
                "access": str(access_token),
                "public_id": str(user.public_id),
                "role_id": user.active_role.public_id if user.active_role else None,
            },
            status=status.HTTP_200_OK
        )
        # Set new refresh token in HttpOnly cookie
        response.set_cookie(
            key="refresh",
            value=new_raw_refresh,
            httponly=True,
            secure=True,
            samesite="None",
            path="/",
        )
        return response

class CookieTokenRefreshView(TokenRefreshView):
    def post(self, request, *args, **kwargs):
        # Copy refresh token from cookie into request.data
        if 'refresh' in request.COOKIES:
            request.data['refresh'] = request.COOKIES['refresh']

        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except Exception as e:
            # Clear cookie if refresh fails
            response = Response({"detail": "Refresh token expired or invalid."}, status=401)
            response.delete_cookie('refresh', path='/')
            return response

        data = serializer.validated_data
        response = Response(data)
        return response


class LogoutAPIView(APIView):
    permission_classes = [AllowAny]          
    authentication_classes = []              

    def post(self, request):
        # Get refresh token from HttpOnly cookie
        raw_refresh = request.COOKIES.get("refresh")
        if not raw_refresh:
            return Response({"detail": "No refresh token found."}, status=status.HTTP_400_BAD_REQUEST)

        # Find the session in DB
        hashed_refresh = UserSession.hash_token(raw_refresh)
        try:
            session = UserSession.objects.get(refresh_token_hash=hashed_refresh)
            session.status = UserSession.Status.REVOKED
            session.save(update_fields=["status"])
        except UserSession.DoesNotExist:
            # Token not found or already revoked/expired
            return Response({"detail": "Invalid or expired session."}, status=status.HTTP_400_BAD_REQUEST)

        # Delete cookie
        response = Response({"detail": "Successfully logged out."}, status=status.HTTP_200_OK)
        response.delete_cookie("refresh", path="/")
        return response


# class LogoutAPIView(GenericAPIView):

#     permission_classes = [AllowAny]          
#     authentication_classes = []              

#     def post(self, request):
#         refresh_token = request.COOKIES.get("refresh")

#         if refresh_token is None:
#             return Response({"detail": "No refresh token found."}, status=400)

#         try:
#             token = RefreshToken(refresh_token)
#             token.blacklist()
#         except TokenError:
#             return Response({"detail": "Token is expired or invalid."}, status=400)

#         response = Response({"detail": "Successfully logged out."}, status=200)
#         response.delete_cookie("refresh", path="/")
#         return response
    


class MyRoleList(ListAPIView):
    serializer_class = RoleReadSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return self.request.user.role_assignments.all()

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data) 

class RoleDetailView(viewsets.ModelViewSet):
    queryset = RoleAssignment.objects.all()
    permission_classes = [IsAuthenticated]

    lookup_field = 'public_id'


    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return RoleWriteSerializer
        return RoleReadSerializer



class UserRoleListView(ListAPIView):

    """Returns a list of all the roles for a given user using thier public id"""
    queryset = RoleAssignment.objects.all().order_by('role')
    lookup_field = 'public_id'
    serializer_class = RoleReadSerializer


    def get_queryset(self):
        public_id = self.kwargs.get('public_id')
        try:
            user = User.objects.get(public_id=public_id)
        except User.DoesNotExist:
            return RoleAssignment.objects.none()
        return RoleAssignment.objects.filter(user=user)


# 2️⃣ Switch active role
class RoleSwitchView(GenericAPIView):
    serializer_class = RoleSwitchSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        # Get validated RoleAssignment instance
        role = serializer.validated_data['role_id']

        # Generate new tokens
        refresh = CustomTokenObtainPairSerializer.get_token(request.user)
        refresh["active_role_id"] = role.id
        refresh["public_id"] = str(request.user.public_id)
        refresh["fname"] = request.user.fname
        refresh["lname"] = request.user.lname

        access_token = str(refresh.access_token)

        # Build response
        roles = request.user.role_assignments.all()
        response_data = {
            "access": access_token,
            "active_role_id": role.id,
            "public_id": str(request.user.public_id),
            "fname": request.user.fname,
            "lname": request.user.lname,
            "roles": [
                {
                    "id": r.id,
                    "role": r.role,
                    "department": r.department_id,
                    "location": r.location_id,
                    "room": r.room_id,
                }
                for r in roles
            ]
        }

        # Set refresh token as HttpOnly cookie
        response = Response(response_data, status=status.HTTP_200_OK)
        response.set_cookie(
            key="refresh",
            value=str(refresh),
            httponly=True,
            secure=True,
            samesite="None",
        )

        return response