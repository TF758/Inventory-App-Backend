from rest_framework_simplejwt.views import TokenObtainPairView
from ..serializers.general import CustomTokenObtainPairSerializer, LogoutSerializer
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.generics import GenericAPIView
from rest_framework_simplejwt.tokens import RefreshToken, TokenError
from django.contrib.auth import authenticate

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
        },  status=status.HTTP_200_OK)

        # set refresh token as HttpOnly cookie
        response.set_cookie(
                key="refresh",
                value=str(refresh),
                httponly=True,
                secure=True,        # set True in production (HTTPS)
                samesite="None",  # adjust if you need cross-site
                max_age=refresh.lifetime.total_seconds()
            )
        return response


class CookieTokenRefreshView(TokenRefreshView):
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)

        # If refresh failed → clear cookie
        if response.status_code != 200:
            res = Response({"detail": "Refresh token expired."}, status=status.HTTP_401_UNAUTHORIZED)
            res.delete_cookie("refresh")
            return res

        return response
    

class LogoutAPIView(GenericAPIView):
    def post(self, request):
        refresh_token = request.COOKIES.get('refresh')
        if refresh_token is None:
            return Response({"detail": "No refresh token found."}, status=400)

        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
        except TokenError:
            return Response({"detail": "Token is expired or invalid."}, status=400)

        # clear the cookie
        response = Response({"detail": "Successfully logged out."}, status=200)
        response.delete_cookie('refresh')
        return response