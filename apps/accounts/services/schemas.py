from drf_yasg import openapi

# Tags
AUTH_TAG = "Authentication"
USER_TAG = "User Profile"
BIZ_TAG = "Business Profile"

# Common Responses
error_response = openapi.Response(
    description="Error response",
    examples={
        "application/json": {"error": "Detailed error message", "code": "error_code"}
    },
)

# Registration Schema
register_schema = {
    "operation_summary": "Register a new User and Business",
    "operation_description": "Creates a new user, a business entity, and sends a verification OTP to the user's email.",
    "tags": [AUTH_TAG],
    "responses": {
        201: openapi.Response(
            description="User registered successfully",
            examples={
                "application/json": {
                    "user": {
                        "id": "550e8400-e29b-41d4-a716-446655440000",
                        "name": "Arif Hussain",
                        "email": "arif@example.com",
                        "phone": "+8801700000000",
                        "business": "b1234567-e29b-41d4-a716-446655440000",
                        "is_verified": False,
                    },
                    "message": "Registration successful. Please verify your email.",
                }
            },
        ),
        400: error_response,
    },
}

# Login Schema
login_schema = {
    "operation_summary": "User Login",
    "operation_description": "Authenticates a user and sets JWT tokens in HttpOnly cookies. Requires email verification.",
    "tags": [AUTH_TAG],
    "request_body": openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=["email", "password"],
        properties={
            "email": openapi.Schema(
                type=openapi.TYPE_STRING, format="email", example="arif@example.com"
            ),
            "password": openapi.Schema(type=openapi.TYPE_STRING, example="password123"),
        },
    ),
    "responses": {
        200: openapi.Response(
            description="Login successful",
            examples={
                "application/json": {
                    "user": {
                        "id": "uuid",
                        "name": "Arif Hussain",
                        "email": "arif@example.com",
                        "is_verified": True,
                    },
                    "message": "Login successful",
                }
            },
        ),
        401: error_response,
        403: openapi.Response(description="Email not verified"),
    },
}

# Verify Email Schema
verify_email_schema = {
    "operation_summary": "Verify Email",
    "operation_description": "Verifies the user's account using the 6-digit OTP sent to their email.",
    "tags": [AUTH_TAG],
    "request_body": openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=["email", "otp"],
        properties={
            "email": openapi.Schema(
                type=openapi.TYPE_STRING, format="email", example="arif@example.com"
            ),
            "otp": openapi.Schema(type=openapi.TYPE_STRING, example="123456"),
        },
    ),
    "responses": {
        200: openapi.Response(
            description="Email verified successfully",
            examples={"application/json": {"message": "Email verified successfully!"}},
        ),
        400: error_response,
    },
}

# Resend OTP Schema
resend_otp_schema = {
    "operation_summary": "Resend OTP",
    "operation_description": "Resends a new OTP to the user's email for either verification or password reset.",
    "tags": [AUTH_TAG],
    "request_body": openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=["email"],
        properties={
            "email": openapi.Schema(
                type=openapi.TYPE_STRING, format="email", example="arif@example.com"
            ),
            "type": openapi.Schema(
                type=openapi.TYPE_STRING,
                description="Type of OTP: email_verify or password_reset",
                example="email_verify",
            ),
        },
    ),
    "responses": {
        200: openapi.Response(
            description="OTP sent successfully",
            examples={"application/json": {"message": "OTP sent successfully!"}},
        ),
        400: error_response,
        404: error_response,
        429: openapi.Response(
            description="Too Many Requests",
            examples={
                "application/json": {
                    "error": "Please wait 30 seconds before requesting another OTP.",
                    "wait_time": 30,
                }
            },
        ),
    },
}

# Forgot Password Schema
forgot_password_schema = {
    "operation_summary": "Forgot Password Request",
    "operation_description": "Generates a password reset OTP and sends it to the user's registered email.",
    "tags": [AUTH_TAG],
    "request_body": openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=["email"],
        properties={
            "email": openapi.Schema(
                type=openapi.TYPE_STRING, format="email", example="arif@example.com"
            )
        },
    ),
    "responses": {
        200: openapi.Response(
            description="OTP sent",
            examples={
                "application/json": {
                    "message": "If an account exists with this email, a reset code has been sent."
                }
            },
        )
    },
}

# Reset Password Schema
reset_password_schema = {
    "operation_summary": "Reset Password",
    "operation_description": "Resets the user's password using the provided OTP.",
    "tags": [AUTH_TAG],
    "request_body": openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=["email", "otp", "new_password"],
        properties={
            "email": openapi.Schema(
                type=openapi.TYPE_STRING, format="email", example="arif@example.com"
            ),
            "otp": openapi.Schema(type=openapi.TYPE_STRING, example="123456"),
            "new_password": openapi.Schema(
                type=openapi.TYPE_STRING, min_length=8, example="new_secret_pass"
            ),
        },
    ),
    "responses": {
        200: openapi.Response(
            description="Password reset successful",
            examples={"application/json": {"message": "Password reset successful!"}},
        ),
        400: error_response,
    },
}

# Logout Schema
logout_schema = {
    "operation_summary": "User Logout",
    "operation_description": "Clears authentication cookies and logs out the user.",
    "tags": [AUTH_TAG],
    "responses": {
        200: openapi.Response(
            description="Logout successful",
            examples={"application/json": {"message": "Logout successful"}},
        )
    },
}

# User Profile Schema
user_profile_schema = {
    "operation_summary": "Get/Update User Profile",
    "operation_description": "Retrieves or updates the authenticated user's profile information. Email cannot be updated.",
    "tags": [USER_TAG],
    "responses": {
        200: openapi.Response(
            description="User profile data",
            examples={
                "application/json": {
                    "id": "uuid",
                    "name": "Arif Hussain",
                    "email": "arif@example.com",
                    "phone": "+8801700000000",
                    "profile_image": None,
                    "business": "uuid",
                    "is_verified": True,
                }
            },
        )
    },
}

# Change Password Schema
change_password_schema = {
    "operation_summary": "Change Password",
    "operation_description": "Allows an authenticated user to change their password by providing the old password and a new one.",
    "tags": [USER_TAG],
    "request_body": openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=["old_password", "new_password", "confirm_password"],
        properties={
            "old_password": openapi.Schema(
                type=openapi.TYPE_STRING, example="old_secret_123"
            ),
            "new_password": openapi.Schema(
                type=openapi.TYPE_STRING, min_length=8, example="new_secret_456"
            ),
            "confirm_password": openapi.Schema(
                type=openapi.TYPE_STRING, example="new_secret_456"
            ),
        },
    ),
    "responses": {
        200: openapi.Response(
            description="Password changed successfully",
            examples={
                "application/json": {"message": "Password updated successfully!"}
            },
        ),
        400: error_response,
    },
}

# Business Profile Schema
business_profile_schema = {
    "operation_summary": "Get/Update Business Profile",
    "operation_description": "Retrieves or updates all business information including hours, off days, and contact details.",
    "tags": [BIZ_TAG],
    "responses": {
        200: openapi.Response(
            description="Business profile data",
            examples={
                "application/json": {
                    "id": "uuid",
                    "name": "Fire AI",
                    "description": "AI Voice Agent Solutions",
                    "address": "Dhaka, Bangladesh",
                    "open_time": "09:00:00",
                    "close_time": "18:00:00",
                    "off_days": ["friday", "saturday"],
                    "human_agent_phone": "+8801700000000",
                    "is_active": True,
                    "created_at": "2026-05-07T04:00:00Z",
                    "updated_at": "2026-05-07T04:00:00Z",
                }
            },
        )
    },
}
