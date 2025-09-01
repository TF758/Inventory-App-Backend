from rest_framework_simplejwt.views import TokenObtainPairView
from ..serializers.general import CustomTokenObtainPairSerializer, LogoutSerializer
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.generics import GenericAPIView

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.user

        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        response = Response({
            "access": access_token,
            "public_id": user.public_id,
            "fname": user.fname,
            "lname": user.lname,
        })

        # set refresh token as HttpOnly cookie
        response.set_cookie(
            key="refresh",
            value=str(refresh),
            httponly=False,
            secure=True,  # True in production with HTTPS
            samesite="None",
        )
        return response


class CookieTokenRefreshView(TokenRefreshView):
    def post(self, request, *args, **kwargs):
        # Read refresh token from cookie
        refresh_token = request.COOKIES.get("refresh")
        if not refresh_token:
            return Response({"detail": "Refresh token not found"}, status=status.HTTP_401_UNAUTHORIZED)

        # Call parent with token in request.data
        request.data["refresh"] = refresh_token
        response = super().post(request, *args, **kwargs)
        return response
    

class LogoutAPIView(GenericAPIView):
    serializer_class = LogoutSerializer


    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            {"detail": "Successfully logged out."},
            status=status.HTTP_200_OK
        )