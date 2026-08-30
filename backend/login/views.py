from django.shortcuts import render, redirect
from .forms import UserRegistrationForm
from django.contrib.auth import authenticate, login as auth_login, logout, update_session_auth_hash
from django.conf import settings
import secrets
import json
import logging
from datetime import timedelta, timezone as dt_timezone
from django.http import JsonResponse
from django.core.mail import send_mail
from django.views.decorators.http import require_http_methods, require_POST, require_GET
from django.views.decorators.csrf import ensure_csrf_cookie
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.password_validation import validate_password
from django.core.cache import cache
from django.core.exceptions import ValidationError as DjangoValidationError
from .models import User
from aivle_big.decorators import login_required
from aivle_big.exceptions import ValidationError, InternalServerError, UnauthorizedError, InvalidRequestError, DuplicateResourceError
from django.db import DatabaseError, IntegrityError
from django.utils import timezone
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes
from hashlib import sha256

logger = logging.getLogger(__name__)

VERIFICATION_CODE_TTL = timedelta(minutes=10)
VERIFICATION_RESEND_COOLDOWN = timedelta(seconds=60)
GENERIC_RECOVERY_MESSAGE = '요청이 접수되었습니다. 계정이 존재하면 안내 메일이 발송됩니다.'
RATE_LIMIT_WINDOW = 15 * 60
PASSWORD_RESET_RATE_LIMIT = 5
LOGIN_FAILURE_RATE_LIMIT = 10
VERIFICATION_FAILURE_LIMIT = 5


def _client_ip(request):
    return request.META.get('REMOTE_ADDR', 'unknown')


def _rate_limit_key(prefix, value):
    digest = sha256(value.encode('utf-8')).hexdigest()
    return f'login:{prefix}:{digest}'


def _allow_request(key, limit, timeout=RATE_LIMIT_WINDOW):
    count = cache.get(key, 0)
    if count >= limit:
        return False
    cache.set(key, count + 1, timeout)
    return True

@ensure_csrf_cookie
def signup(request):
    if request.method == 'GET':
        return render(request, 'signup.html')
    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
            # Email is an identifier; keep it canonical so signup/login/reset
            # behave consistently regardless of user input casing or spaces.
            if 'email' in data and isinstance(data['email'], str):
                data['email'] = data['email'].strip().lower()
            form = UserRegistrationForm(data)
            submitted_verification_code = data.get('verification_code')
            session_verification_code = request.session.get('verification_code')
            session_verification_email = request.session.get('verification_email')
            sent_at = request.session.get('verification_code_sent_at')
            if sent_at is None:
                session_verification_code = None
            else:
                try:
                    sent_time = timezone.datetime.fromtimestamp(float(sent_at), tz=dt_timezone.utc)
                    if timezone.now() - sent_time > VERIFICATION_CODE_TTL:
                        session_verification_code = None
                except (TypeError, ValueError, OverflowError):
                    session_verification_code = None

            if (
                submitted_verification_code != session_verification_code
                or data.get('email') != session_verification_email
            ):
                failures = request.session.get('verification_code_failures', 0) + 1
                if failures >= VERIFICATION_FAILURE_LIMIT:
                    request.session.pop('verification_code', None)
                    request.session.pop('verification_email', None)
                    request.session.pop('verification_code_sent_at', None)
                    request.session.pop('verification_code_failures', None)
                    return JsonResponse({'status': 'error', 'message': 'Verification code expired. Request a new code.'}, status=429)
                request.session['verification_code_failures'] = failures
                return JsonResponse({'status': 'error', 'message': 'Invalid verification code.'}, status=400)

            if form.is_valid():
                user = form.save()
                request.session.pop('verification_code', None)
                request.session.pop('verification_email', None)
                request.session.pop('verification_code_sent_at', None)
                request.session.pop('verification_code_failures', None)
                auth_login(request, user)
                return JsonResponse({'status': 'success', 'message': 'User registered and logged in.'})
            else:
                raise ValidationError("Form validation failed")
        except json.JSONDecodeError:
            raise ValidationError("Invalid JSON format")
        except (ValidationError, DuplicateResourceError):
            raise
        except IntegrityError:
            raise DuplicateResourceError("A user with similar details already exists.")
        except Exception as e:
            logger.error(f"Signup error: {str(e)}")
            raise InternalServerError("An error occurred during user registration")
    else:
        raise InvalidRequestError("Only GET and POST methods are allowed")


@require_GET
def check_username(request):
    try:
        username = request.GET.get('username', None)
        if username is None:
            raise ValidationError("Username parameter is missing")
        is_taken = User.objects.filter(username=username).exists()
        return JsonResponse({'is_taken': is_taken})
    except DatabaseError as e:
        logger.error(f"Database error during username check: {str(e)}")
        raise InternalServerError("Failed to check if username is taken")

@require_http_methods(["GET", "POST"])
@ensure_csrf_cookie
def login(request):
    if request.method == 'GET':
        return render(request, 'login.html')
    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
            email = data.get('email')
            password = data.get('password')
            normalized_email = (email or '').strip().lower()
            login_key = _rate_limit_key('login-failure', f'{normalized_email}:{_client_ip(request)}')
            if cache.get(login_key, 0) >= LOGIN_FAILURE_RATE_LIMIT:
                return JsonResponse({'status': 'error', 'message': 'Login temporarily unavailable.'}, status=429)

            if not email or not password:
                raise ValidationError("Email and password are required")

            email = normalized_email
            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                raise UnauthorizedError("존재하지 않는 이메일입니다.")

            user = authenticate(request, email=email, password=password)
            if user:
                cache.delete(login_key)
                auth_login(request, user)
                response = JsonResponse({
                    'status': 'success',
                    'message': 'User authenticated and logged in.',
                    'username': user.username,
                    'user_id': user.id,
                    'is_authenticated': user.is_authenticated
                })
                response.set_cookie('sessionid', request.session.session_key)
                return response
            else:
                raise UnauthorizedError("비밀번호가 일치하지 않습니다.")

        except json.JSONDecodeError:
            raise ValidationError("Invalid JSON format")
        except UnauthorizedError as e:
            _allow_request(login_key, LOGIN_FAILURE_RATE_LIMIT + 1)
            logger.error(f"Authentication error: {str(e)}")
            if cache.get(login_key, 0) > LOGIN_FAILURE_RATE_LIMIT:
                return JsonResponse({'status': 'error', 'message': 'Login temporarily unavailable.'}, status=429)
            return JsonResponse({'status': 'error', 'message': 'Invalid email or password.'}, status=403)
        except ValidationError as e:
            logger.error(f"Validation error: {str(e)}")
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
        except Exception as e:
            logger.error(f"Login error: {str(e)}")
            raise InternalServerError("An error occurred during login")
    else:
        raise InvalidRequestError("Method not allowed")

@ensure_csrf_cookie
@require_POST
def send_verification_email(request):
    try:
        data = json.loads(request.body)
        email = (data.get('email') or '').strip().lower()
        if not email:
            return JsonResponse({'error': 'Email field is required'}, status=400)
        now = timezone.now()
        sent_at = request.session.get('verification_code_sent_at')
        if sent_at is not None:
            try:
                if now - timezone.datetime.fromtimestamp(float(sent_at), tz=dt_timezone.utc) < VERIFICATION_RESEND_COOLDOWN:
                    return JsonResponse({'message': GENERIC_RECOVERY_MESSAGE})
            except (TypeError, ValueError, OverflowError):
                pass
        if User.objects.filter(email=email).exists():
            return JsonResponse({'message': GENERIC_RECOVERY_MESSAGE})
        verification_code = f'{secrets.randbelow(10000):04d}'
        send_mail(
            'Your Verification Code', '', settings.DEFAULT_FROM_EMAIL, [email],
            fail_silently=False,
            html_message=f'<p>Your verification code is:</p><p>{verification_code}</p>',
        )
        request.session['verification_code'] = verification_code
        request.session['verification_email'] = email
        request.session['verification_code_sent_at'] = now.timestamp()
        return JsonResponse({'message': GENERIC_RECOVERY_MESSAGE})
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON format'}, status=400)
    except Exception:
        logger.error('Verification email delivery failed', exc_info=True)
        return JsonResponse({'error': 'Verification email is temporarily unavailable'}, status=503)


@ensure_csrf_cookie
@require_POST
def password_reset_request(request):
    try:
        data = json.loads(request.body)
        email = (data.get('email') or '').strip().lower()
        if not email:
            return JsonResponse({'error': 'Email is required'}, status=400)
        reset_key = _rate_limit_key('password-reset', f'{email}:{_client_ip(request)}')
        if not _allow_request(reset_key, PASSWORD_RESET_RATE_LIMIT):
            return JsonResponse({'message': GENERIC_RECOVERY_MESSAGE}, status=429)
        user = User.objects.filter(email=email).first()
        if user is not None:
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            frontend_base = getattr(settings, 'FRONTEND_BASE_URL', 'http://localhost:3000').rstrip('/')
            reset_link = f'{frontend_base}/password-reset-confirm?uid={uid}&token={token}'
            send_mail(
                'Password reset',
                f'Use this link to reset your password: {reset_link}',
                settings.DEFAULT_FROM_EMAIL,
                [email],
                fail_silently=False,
            )
        return JsonResponse({'message': GENERIC_RECOVERY_MESSAGE})
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON format'}, status=400)
    except Exception:
        logger.error('Password reset email delivery failed', exc_info=True)
        return JsonResponse({'error': 'Password reset is temporarily unavailable'}, status=503)


@ensure_csrf_cookie
@require_POST
def password_reset(request):
    try:
        data = json.loads(request.body)
        email = data.get('email')
        uid = data.get('uid')
        token = data.get('token')
        new_password = data.get('new_password')
        if not uid or not token or not new_password:
            return JsonResponse({'error': 'uid, token, and new password are required'}, status=400)
        try:
            user_id = urlsafe_base64_decode(uid).decode()
            user = User.objects.get(pk=user_id)
        except (TypeError, ValueError, UnicodeDecodeError, User.DoesNotExist):
            return JsonResponse({'error': 'Invalid password reset request'}, status=400)
        if not default_token_generator.check_token(user, token):
            return JsonResponse({'error': 'Invalid password reset request'}, status=400)
        try:
            validate_password(new_password, user)
        except DjangoValidationError:
            return JsonResponse({'error': 'Password does not meet security requirements'}, status=400)
        user.set_password(new_password)
        user.save(update_fields=['password'])
        return JsonResponse({'status': 'success', 'message': 'Password reset successfully'})
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON format'}, status=400)
    except Exception:
        logger.error('Password reset confirmation failed', exc_info=True)
        return JsonResponse({'error': 'Password reset confirmation failed'}, status=400)


@require_GET
def password_reset_page(request):
    frontend_base = getattr(settings, 'FRONTEND_BASE_URL', 'http://localhost:3000').rstrip('/')
    return redirect(f'{frontend_base}/password_reset')

def logout_view(request):
    try:
        if request.method == 'POST':
            logout(request)
            return JsonResponse({'status': 'success', 'message': 'User logged out successfully'})
        else:
            raise InvalidRequestError("Method not allowed")
    except InvalidRequestError as e:
        return JsonResponse({
            'status': 'error',
            'message': e.message,
            'code': e.error_code,
            'status_code': e.status_code
        }, status=e.status_code)
    except UnauthorizedError as e:
        return JsonResponse({
            'status': 'error',
            'message': e.message,
            'code': e.error_code,
            'status_code': e.status_code
        }, status=e.status_code)
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': "Unexpected error occurred",
            'code': 2000,
            'status_code': 500
        }, status=500)
        

@ensure_csrf_cookie
def auth_check(request):
    return JsonResponse({
        'is_authenticated': request.user.is_authenticated,
        'username': request.user.username,
    })

@login_required
def change_password(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            old_password = data.get('old_password')
            new_password1 = data.get('new_password1')
            new_password2 = data.get('new_password2')

            if not request.user.check_password(old_password):
                return JsonResponse({'status': 'error', 'message': "현재 비밀번호가 일치하지 않습니다."}, status=400)

            if new_password1 == old_password:
                return JsonResponse({'status': 'error', 'message': "새 비밀번호는 기존 비밀번호와 달라야 합니다."}, status=400)
            
            if new_password1 != new_password2:
                return JsonResponse({'status': 'error', 'message': "새 비밀번호와 새 비밀번호 확인이 일치하지 않습니다."}, status=400)
            
            form = PasswordChangeForm(user=request.user, data=data)
            if form.is_valid():
                user = form.save()
                update_session_auth_hash(request, user)
                logout(request)
                return JsonResponse({'status': 'success', 'message': 'Password changed successfully'})
            else:
                return JsonResponse({'status': 'error', 'message': "Form validation failed", 'details': form.errors}, status=400)
        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': "Invalid JSON format"}, status=400)
        except ValidationError as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
        except Exception as e:
            logger.error(f"Error changing password: {str(e)}")
            return JsonResponse({'status': 'error', 'message': "Failed to change password"}, status=500)
    else:
        return JsonResponse({'status': 'error', 'message': "POST method only allowed"}, status=405)

@login_required
def delete_account(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            password = data.get('password')

            if not password:
                return JsonResponse({'status': 'error', 'message': '비밀번호를 입력해주세요.'}, status=400)

            user = request.user

            if not user.check_password(password):
                return JsonResponse({'status': 'error', 'message': '비밀번호가 일치하지 않습니다.'}, status=400)

            logout(request)
            user.delete()
            return JsonResponse({'status': 'success', 'message': 'Account deleted successfully'})
        except Exception as e:
            logger.error(f"Error deleting account: {str(e)}")
            return JsonResponse({'status': 'error', 'message': 'Failed to delete account'}, status=500)
    else:
        return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)

    
@login_required
def change_username(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            new_username = data.get('new_username')
            if not new_username:
                return JsonResponse({'status': 'error', 'message': 'New username is required', 'code': 1000, 'status_code': 400}, status=400)

            user = request.user
            if User.objects.filter(username=new_username).exists():
                return JsonResponse({'status': 'error', 'message': '이미 사용중인 이름입니다.', 'code': 2000, 'status_code': 400}, status=400)

            user.username = new_username
            user.save()
            return JsonResponse({'status': 'success', 'message': 'Username changed successfully'})
        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': 'Invalid JSON format', 'code': 1001, 'status_code': 400}, status=400)
        except Exception as e:
            logger.error(f"Error changing username: {str(e)}")
            return JsonResponse({'status': 'error', 'message': 'Failed to change username', 'code': 2001, 'status_code': 500}, status=500)
    else:
        return JsonResponse({'status': 'error', 'message': 'POST method only allowed', 'code': 1002, 'status_code': 405}, status=405)
