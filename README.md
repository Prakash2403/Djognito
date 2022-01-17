# Djognito

A DRF Authentication module for verifying JWT Token issued by AWS Cognito.

## Problem Statement

I wasn't able to find a DRF Authentication Module which simply allows you to 
  * Verify a JWT
  * Attach a `user` object to request if verification is successful
    * **Assumption**: `user` object only requires `username` attribute to be instantiated. Other attributes can be later added using `attach_attribute` hook provided.

Every solution I came across does a lookup on `User` model in database, thus defeating the _statelessness_ of JWT.

## My usecase

I have engineered the frontend to send relevant tokens using `cookies`. I just wanted to

*  Verify the  `JWT` stored in `${ACCESS_TOKEN_KEY}` cookie.
*  Attach a `user` object to my `request` if verification succeeds.
*  Avoid any DB lookups.
*  Attach permissions to user depending on some of the JWT fields(`cognito:groups` in my case).


## Solution̦̦

### TL;DR version

Created a DRF Authentication Module which simply looks at the cookies and verifies the user. If user verification succeeds, 
a `user` object is created and attached to `request` object. Rest of the code can use `request.user` to access the created user. 

## A detailed view

The authentication module picks up the JWT stored in cookie named `${ACCESS_TOKEN_KEY}`, verifies it, and creates a user if the verification succeeds. It only uses `username` to instantiate the `user` object. 

**Note:** It is expected that `username` is present in your `JWT` as a claim. If you're using AWS Cognito, then your JWT will contain a `username` attribute.

The following assignment operation happens
```
from django.contrib.auth.models import User
user = User(username=username) # Username is created using username claim present in your JWT
```

Then, the created `user` object and the `request` is passed to `attach_attribute` hook, which attaches necessary permissions (or attributes) to your user object. The `user` object is modified in-place. Finally, if everything succeeds, the `user` object is returned by the `authenticate` method, which in-turn attaches it to `request` object. Now, you can use `request.user` object anywhere in your downstream application.

Note that this module is designed to avoid DB lookups at all. 

## How to use this module

### Common

Kindly ensure that following environment variables are set:

```
ACCESS_TOKEN_KEY= #  Points to the cookie key containing access token issued by AWS Cognito
AWS_COGNITO_APP_CLIENT_ID= # Your Cognito App client ID
AWS_COGNITO_REGION= # Region in which your Cognito Server exists
AWS_COGNITO_USER_POOL_ID= # Your Cognito User pool ID 
```

### Case 1: You only want to authenticate using JWT

Ensure that environment variables described in [common](#common) sections are set

Add  `djognito.authentication.BaseCognitoAuthentication` to `DEFAULT_AUTHENTICATION_CLASSES` in `settings.py`. Finally, your `REST_FRAMEWORK` dict should look like

```
REST_FRAMEWORK = {
    ....
    'DEFAULT_AUTHENTICATION_CLASSES': (
        "djognito.authentication.BaseCognitoAuthentication",
        ....
    ),
    ....
}
```

### Case 2: You want to authenticate using JWT and attach attributes/permissions

Ensure that environment variables described in [common](#common) sections are set

1. Create a class inheriting `BaseCognitoAuthentication` and override the `attach_attributes` method.
2. Add that class in your `DEFAULT_AUTHENTICATION_CLASSES` list.

The following example attaches an attribute called `groups` to user object. The downstream code can use `request.user.groups` anywhere to access the groups to which user belongs.

This example assumes that every user is part of at least one AWS Cognito group.

```python
from djognito.authentication import BaseCognitoAuthentication
from djognito.jwt_utils import verify_jwt
from rest_framework import authentication
from rest_framework import exceptions
import logging

logger = logging.getLogger(__name__)


class CognitoAuthentication(BaseCognitoAuthentication):
    def attach_attributes(self, user, request):
        access_token = request.COOKIES.get('accessToken', '')
        claims = verify_jwt(access_token)
        user.groups = claims['cognito:groups']
        if len(claims['cognito:groups']) > 1:
            logger.warning(
                f'User {claims["username"]} belongs to multiple group: {claims["cognito: groups"]}.')
```

Assuming that the filename is `authentication.py` and `PYTHONPATH` is able to locate it, add `authentication.CognitoAuthentication` to your `DEFAULT_AUTHENTICATION_CLASSES`. Finally, your `REST_FRAMEWORK` dict should look like
```
REST_FRAMEWORK = {
    ....
    'DEFAULT_AUTHENTICATION_CLASSES': (
        "authentication.CognitoAuthentication",
        ....
    ),
    ....
}
```

You can read more about the flow of control [here](#a-detailed-view)

## Appendix

### Pre-requisites

#### JWT

One of the primary usecase of JWT is stateless authentication. It allows you to assert the authenticity of a given user without performing a database lookup. There are two major advantages of this:

* Performance boost: database lookup may significantly increase your latency
* Separation of Resources: The whole application can be divided into two distinct set of resources: `AuthServer` and `ResourceServer`. This has following benefits: 
  * One can have a separate team/workforce to ensure that `Auth` server meets standard compliances (`HIPAA`, `FedRAMP` etc).
  * `ResourcesServer` and `AuthServer` can scale independently.

#### AWS Cognito

AWS Cognito can act as a `AuthServer` for systems relying on Stateless Authentication. It uses `JWT` standard for issuing tokens and takes care of user management (sign-up, sign-in, account verification, MFA, etc). You can read more about AWS Cognito [here](https://aws.amazon.com/cognito/)
