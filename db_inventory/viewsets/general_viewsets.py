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
                httponly=False,
                secure=True, 
                samesite="None",
            )
        
        print("refresh cookie set")
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