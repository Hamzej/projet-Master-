"""
backend/core/auth_views.py - AUTHENTIFICATION JWT
Authentification JWT + Login/Logout/Register
À CRÉER dans : backend/core/auth_views.py
"""

from rest_framework import status, views
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
import logging

logger = logging.getLogger(__name__)


class LoginView(views.APIView):
    """
    Login endpoint - Returns JWT tokens
    
    POST /auth/login/
    {
        "username": "admin",
        "password": "password123"
    }
    
    Response:
    {
        "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
        "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc...",
        "user": {
            "id": 1,
            "username": "admin",
            "email": "admin@example.com"
        }
    }
    """
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            username = request.data.get('username')
            password = request.data.get('password')

            if not username or not password:
                logger.warning("❌ [LOGIN] Champs manquants: username ou password")
                return Response(
                    {'error': 'Username and password required'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Authenticate user
            user = authenticate(username=username, password=password)

            if user is None:
                logger.warning(f"❌ [LOGIN] Identifiants invalides pour: {username}")
                return Response(
                    {'error': 'Invalid credentials'},
                    status=status.HTTP_401_UNAUTHORIZED
                )

            # Generate tokens
            refresh = RefreshToken.for_user(user)
            logger.info(f"✅ [LOGIN] Connexion réussie: {username}")

            return Response({
                'access': str(refresh.access_token),
                'refresh': str(refresh),
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'first_name': user.first_name
                }
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"❌ [LOGIN] Error: {e}")
            return Response(
                {'error': 'Login failed'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class LogoutView(views.APIView):
    """
    Logout endpoint - Blacklist refresh token
    
    POST /auth/logout/
    {
        "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
    }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get('refresh')

            if not refresh_token:
                logger.warning("❌ [LOGOUT] Refresh token manquant")
                return Response(
                    {'error': 'Refresh token required'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            token = RefreshToken(refresh_token)
            token.blacklist()
            logger.info(f"✅ [LOGOUT] Déconnexion réussie: {request.user.username}")

            return Response(
                {'message': 'Logout successful'},
                status=status.HTTP_200_OK
            )

        except Exception as e:
            logger.error(f"❌ [LOGOUT] Error: {e}")
            return Response(
                {'error': 'Logout failed'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class RegisterView(views.APIView):
    """
    Register new user
    
    POST /auth/register/
    {
        "username": "newuser",
        "email": "user@example.com",
        "password": "password123",
        "password_confirm": "password123",
        "first_name": "John"
    }
    """
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            username = request.data.get('username')
            email = request.data.get('email')
            password = request.data.get('password')
            password_confirm = request.data.get('password_confirm')
            first_name = request.data.get('first_name', '')

            # Validation
            if not all([username, email, password, password_confirm]):
                logger.warning("❌ [REGISTER] Champs manquants")
                return Response(
                    {'error': 'All fields required'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if password != password_confirm:
                logger.warning("❌ [REGISTER] Les mots de passe ne correspondent pas")
                return Response(
                    {'error': 'Passwords do not match'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if len(password) < 8:
                logger.warning("��� [REGISTER] Mot de passe trop court")
                return Response(
                    {'error': 'Password must be at least 8 characters'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Check if user exists
            if User.objects.filter(username=username).exists():
                logger.warning(f"❌ [REGISTER] Username déjà utilisé: {username}")
                return Response(
                    {'error': 'Username already exists'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if User.objects.filter(email=email).exists():
                logger.warning(f"❌ [REGISTER] Email déjà utilisé: {email}")
                return Response(
                    {'error': 'Email already exists'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Create user
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name
            )

            # Generate tokens
            refresh = RefreshToken.for_user(user)
            logger.info(f"✅ [REGISTER] Inscription réussie: {username}")

            return Response({
                'access': str(refresh.access_token),
                'refresh': str(refresh),
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'first_name': user.first_name
                }
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.error(f"❌ [REGISTER] Error: {e}")
            return Response(
                {'error': 'Registration failed'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class RefreshTokenView(views.APIView):
    """
    Refresh access token
    
    POST /auth/refresh/
    {
        "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
    }
    """
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            refresh_token = request.data.get('refresh')

            if not refresh_token:
                logger.warning("❌ [REFRESH] Refresh token manquant")
                return Response(
                    {'error': 'Refresh token required'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            token = RefreshToken(refresh_token)
            logger.info("✅ [REFRESH] Token rafraîchi")

            return Response({
                'access': str(token.access_token),
                'refresh': str(token)
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"❌ [REFRESH] Error: {e}")
            return Response(
                {'error': 'Invalid refresh token'},
                status=status.HTTP_401_UNAUTHORIZED
            )


class MeView(views.APIView):
    """
    Get current user info
    
    GET /auth/me/
    
    Response:
    {
        "id": 1,
        "username": "admin",
        "email": "admin@example.com",
        "first_name": "John"
    }
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        logger.info(f"✅ [ME] Fetching user info: {request.user.username}")
        return Response({
            'id': request.user.id,
            'username': request.user.username,
            'email': request.user.email,
            'first_name': request.user.first_name
        })