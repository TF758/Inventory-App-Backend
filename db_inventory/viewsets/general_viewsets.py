from rest_framework_simplejwt.views import TokenObtainPairView
from ..serializers.general import CustomTokenObtainPairSerializer, RoleSwitchSerializer, RoleListSerializer,  UserRoleReadSerializer, UserRoleWriteSerializer
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.generics import GenericAPIView, ListAPIView
from rest_framework_simplejwt.tokens import RefreshToken, TokenError
from rest_framework.permissions import IsAuthenticated
from ..models import RoleAssignment, User



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



class LogoutAPIView(GenericAPIView):

    permission_classes = [AllowAny]          
    authentication_classes = []              

    def post(self, request):
        refresh_token = request.COOKIES.get("refresh")

        if refresh_token is None:
            return Response({"detail": "No refresh token found."}, status=400)

        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
        except TokenError:
            return Response({"detail": "Token is expired or invalid."}, status=400)

        response = Response({"detail": "Successfully logged out."}, status=200)
        response.delete_cookie("refresh", path="/")
        return response
    


class RoleListView(ListAPIView):
    serializer_class = UserRoleReadSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return self.request.user.role_assignments.all()

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data) 


class UserRoleListView(ListAPIView):

    """Returns a list of all the roles for a given user using thier public id"""
    queryset = RoleAssignment.objects.all().order_by('role')
    lookup_field = 'public_id'
    serializer_class = UserRoleReadSerializer


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