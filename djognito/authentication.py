import os
from django.contrib.auth.models import User
from djognito.jwt_utils import verify_jwt
from rest_framework import authentication
from rest_framework import exceptions
import logging
import traceback

logger = logging.getLogger(__name__)


class BaseCognitoAuthentication(authentication.BaseAuthentication):
    def attach_attributes(self, user, request):
        pass

    def authenticate(self, request):
        access_token_id = os.environ.get('ACCESS_TOKEN_KEY_NAME', None)
        logger.debug(f'Using {access_token_id} as access token key name.')
        if access_token_id is None:
            logger.warning(
                'No Access Token Key specified. Kindly set ACCESS_TOKEN_KEY_NAME environment variable.')
        try:
            access_token = request.COOKIES.get('accessToken', '')
            claims = verify_jwt(access_token)
            if claims:
                username = claims['username']
                user = User(username=username)
                self.attach_attributes(user, request)
                logger.debug(f'Login Successful for {username}')
            else:
                raise exceptions.AuthenticationFailed('No such user')
        except Exception:
            logger.error(traceback.format_exc())
            return (None, None)
        return (user, None)
