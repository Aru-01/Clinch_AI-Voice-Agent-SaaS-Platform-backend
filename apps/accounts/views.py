from rest_framework import status, generics
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate, get_user_model
from django.conf import settings
from django.utils import timezone
from drf_yasg.utils import swagger_auto_schema

from apps.accounts.serializers import (
    RegisterSerializer, UserSerializer, BusinessSerializer, VerifyEmailSerializer,
    ForgotPasswordSerializer, ResetPasswordSerializer, ChangePasswordSerializer
)
from apps.accounts.models import OTPCode, Business

# Services Imports
from apps.accounts.services.utils import (
    generate_otp, send_otp_email, 
    check_otp_rate_limit, update_otp_rate_limit, reset_otp_rate_limit
)
from apps.accounts.services.permissions import IsVerifiedUser
from apps.accounts.services.schemas import (
    register_schema, login_schema, verify_email_schema, resend_otp_schema,
    forgot_password_schema, reset_password_schema, logout_schema,
    user_profile_schema, business_profile_schema, change_password_schema
)

User = get_user_model()

def set_auth_cookies(response, user):
    refresh = RefreshToken.for_user(user)
    access_token = str(refresh.access_token)
    refresh_token = str(refresh)

    response.set_cookie(
        key=settings.SIMPLE_JWT['AUTH_COOKIE'],
        value=access_token,
        expires=settings.SIMPLE_JWT['ACCESS_TOKEN_LIFETIME'],
        secure=settings.SIMPLE_JWT['AUTH_COOKIE_SECURE'],
        httponly=settings.SIMPLE_JWT['AUTH_COOKIE_HTTP_ONLY'],
        samesite=settings.SIMPLE_JWT['AUTH_COOKIE_SAMESITE'],
        path=settings.SIMPLE_JWT['AUTH_COOKIE_PATH'],
    )
    response.set_cookie(
        key=settings.SIMPLE_JWT['AUTH_COOKIE_REFRESH'],
        value=refresh_token,
        expires=settings.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME'],
        secure=settings.SIMPLE_JWT['AUTH_COOKIE_SECURE'],
        httponly=settings.SIMPLE_JWT['AUTH_COOKIE_HTTP_ONLY'],
        samesite=settings.SIMPLE_JWT['AUTH_COOKIE_SAMESITE'],
        path=settings.SIMPLE_JWT['AUTH_COOKIE_PATH'],
    )
    return response

class RegisterView(generics.CreateAPIView):
    permission_classes = [AllowAny]
    serializer_class = RegisterSerializer

    @swagger_auto_schema(**register_schema)
    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        # Clean expired OTPs
        OTPCode.clean_expired()
        
        # Send Verification OTP
        otp = generate_otp(user, OTPCode.OTPType.EMAIL_VERIFY)
        send_otp_email(user, otp, OTPCode.OTPType.EMAIL_VERIFY)
        update_otp_rate_limit(user)
        
        response = Response(
            {
                "user": UserSerializer(user).data, 
                "message": "Registration successful. Please verify your email."
            },
            status=status.HTTP_201_CREATED
        )
        return set_auth_cookies(response, user)

class VerifyEmailView(APIView):
    permission_classes = [AllowAny]
    serializer_class = VerifyEmailSerializer

    @swagger_auto_schema(**verify_email_schema)
    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        email = serializer.validated_data['email']
        otp = serializer.validated_data['otp']
        
        # Clean expired OTPs
        OTPCode.clean_expired()
        
        user = User.objects.filter(email=email).first()
        if not user:
            return Response({"error": "User not found", "code": "user_not_found"}, status=status.HTTP_404_NOT_FOUND)
        
        otp_obj = OTPCode.objects.filter(
            user=user, 
            code=otp, 
            type=OTPCode.OTPType.EMAIL_VERIFY,
            expires_at__gt=timezone.now()
        ).first()
        
        if not otp_obj:
            return Response({"error": "Invalid or expired OTP", "code": "invalid_otp"}, status=status.HTTP_400_BAD_REQUEST)
        
        user.is_verified = True
        user.save()
        
        # Delete the used OTP instead of marking it
        otp_obj.delete()
        
        # Reset rate limit on success
        reset_otp_rate_limit(user)
        
        return Response({"message": "Email verified successfully!"})

class ResendOTPView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(**resend_otp_schema)
    def post(self, request):
        email = request.data.get('email')
        otp_type = request.data.get('type', OTPCode.OTPType.EMAIL_VERIFY)
        
        # Clean expired OTPs
        OTPCode.clean_expired()
        
        user = User.objects.filter(email=email).first()
        if not user:
            return Response({"error": "User not found", "code": "user_not_found"}, status=status.HTTP_404_NOT_FOUND)
        
        # Rate Limit Check
        allowed, wait_time = check_otp_rate_limit(user)
        if not allowed:
            return Response(
                {
                    "error": f"Please wait {wait_time} seconds before requesting another OTP.",
                    "code": "rate_limit_exceeded",
                    "wait_time": wait_time
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS
            )
        
        otp = generate_otp(user, otp_type)
        send_otp_email(user, otp, otp_type)
        update_otp_rate_limit(user)
        
        return Response({"message": "OTP sent successfully!"})

class LoginView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(**login_schema)
    def post(self, request):
        email = request.data.get("email")
        password = request.data.get("password")
        user = authenticate(email=email, password=password)

        if user:
            if not user.is_verified:
                return Response(
                    {"error": "Email not verified", "code": "email_not_verified"}, 
                    status=status.HTTP_403_FORBIDDEN
                )
            
            response = Response({"user": UserSerializer(user).data, "message": "Login successful"})
            return set_auth_cookies(response, user)
        
        return Response({"error": "Invalid Credentials", "code": "invalid_credentials"}, status=status.HTTP_401_UNAUTHORIZED)

class ForgotPasswordView(APIView):
    permission_classes = [AllowAny]
    serializer_class = ForgotPasswordSerializer

    @swagger_auto_schema(**forgot_password_schema)
    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Clean expired OTPs
        OTPCode.clean_expired()
        
        email = serializer.validated_data['email']
        user = User.objects.filter(email=email).first()
        
        if user:
            # Check rate limit
            allowed, wait_time = check_otp_rate_limit(user)
            if not allowed:
                return Response(
                    {"error": f"Please wait {wait_time} seconds.", "wait_time": wait_time},
                    status=status.HTTP_429_TOO_MANY_REQUESTS
                )
            
            otp = generate_otp(user, OTPCode.OTPType.PASSWORD_RESET)
            send_otp_email(user, otp, OTPCode.OTPType.PASSWORD_RESET)
            update_otp_rate_limit(user)
        
        return Response({"message": "If an account exists with this email, a reset code has been sent."})

class ResetPasswordView(APIView):
    permission_classes = [AllowAny]
    serializer_class = ResetPasswordSerializer

    @swagger_auto_schema(**reset_password_schema)
    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Clean expired OTPs
        OTPCode.clean_expired()
        
        email = serializer.validated_data['email']
        otp = serializer.validated_data['otp']
        new_password = serializer.validated_data['new_password']
        
        user = User.objects.filter(email=email).first()
        if not user:
            return Response({"error": "Invalid request", "code": "invalid_request"}, status=status.HTTP_400_BAD_REQUEST)
        
        otp_obj = OTPCode.objects.filter(
            user=user, 
            code=otp, 
            type=OTPCode.OTPType.PASSWORD_RESET,
            expires_at__gt=timezone.now()
        ).first()
        
        if not otp_obj:
            return Response({"error": "Invalid or expired OTP", "code": "invalid_otp"}, status=status.HTTP_400_BAD_REQUEST)
        
        user.set_password(new_password)
        user.save()
        
        # Delete used OTP
        otp_obj.delete()
        
        # Reset rate limit on success
        reset_otp_rate_limit(user)
        
        return Response({"message": "Password reset successful!"})

class LogoutView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(**logout_schema)
    def post(self, request):
        response = Response({"message": "Logout successful"})
        response.delete_cookie(settings.SIMPLE_JWT['AUTH_COOKIE'])
        response.delete_cookie(settings.SIMPLE_JWT['AUTH_COOKIE_REFRESH'])
        return response

class ChangePasswordView(APIView):
    permission_classes = [IsVerifiedUser]
    serializer_class = ChangePasswordSerializer

    @swagger_auto_schema(**change_password_schema)
    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = request.user
        if not user.check_password(serializer.validated_data['old_password']):
            return Response({"error": "Invalid old password."}, status=status.HTTP_400_BAD_REQUEST)
        
        user.set_password(serializer.validated_data['new_password'])
        user.save()
        
        return Response({"message": "Password updated successfully!"})

class UserProfileView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsVerifiedUser]
    serializer_class = UserSerializer

    @swagger_auto_schema(**user_profile_schema)
    def get(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)

    @swagger_auto_schema(**user_profile_schema)
    def patch(self, request, *args, **kwargs):
        return self.partial_update(request, *args, **kwargs)

    @swagger_auto_schema(**user_profile_schema)
    def put(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)

    def get_object(self):
        return self.request.user

class BusinessProfileView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsVerifiedUser]
    serializer_class = BusinessSerializer

    @swagger_auto_schema(**business_profile_schema)
    def get(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)

    @swagger_auto_schema(**business_profile_schema)
    def patch(self, request, *args, **kwargs):
        return self.partial_update(request, *args, **kwargs)

    @swagger_auto_schema(**business_profile_schema)
    def put(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)

    def get_object(self):
        return self.request.user.business
