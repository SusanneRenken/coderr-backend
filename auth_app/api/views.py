"""Views providing registration, login and profile listing/updating.

Only comments and docstrings are added here. The view logic is unchanged.
"""

from rest_framework import status, generics
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.throttling import ScopedRateThrottle
from auth_app.models import Profile
from .serializers import (
    RegistrationSerializer,
    ProfileSerializer,
    ProfileBusinessSerializer,
    ProfileCustomerSerializer,
)
from .permissions import IsOwnerProfile


class RegistrationView(APIView):
    """Public endpoint to register a new user and profile.

    POST: expects the RegistrationSerializer payload. Returns a token on
    success. A scoped rate throttle is applied to mitigate automated abuse.
    """

    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth_registration"

    def post(self, request):
        serializer = RegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.save()

        token, _ = Token.objects.get_or_create(user=user)

        return Response(
            {
                "token": token.key,
                "username": user.username,
                "email": user.email,
                "user_id": user.id,
            },
            status=status.HTTP_201_CREATED,
        )


class LoginView(ObtainAuthToken):
    """Token login view that returns token + basic user info on success."""

    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth_login"

    def post(self, request):
        serializer = self.serializer_class(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        token, _ = Token.objects.get_or_create(user=user)
        return Response({
            'token': token.key,
            'username': user.username,
            'email': user.email,
            'user_id': user.id
        })


class ProfileDetailView(generics.RetrieveUpdateAPIView):
    """Retrieve or partially update a Profile.

    Permissions are enforced by IsOwnerProfile which allows safe methods for
    everyone but restricts PATCH to the profile owner.
    """

    queryset = Profile.objects.all()
    serializer_class = ProfileSerializer
    permission_classes = [IsOwnerProfile]
    http_method_names = ["get", "patch", "head", "options"]


class ProfileBusinessView(generics.ListAPIView):
    """List profiles with type='business'."""

    serializer_class = ProfileBusinessSerializer

    def get_queryset(self):
        return Profile.objects.filter(type="business")


class ProfileCustomerView(generics.ListAPIView):
    """List profiles with type='customer'."""

    serializer_class = ProfileCustomerSerializer

    def get_queryset(self):
        return Profile.objects.filter(type="customer")