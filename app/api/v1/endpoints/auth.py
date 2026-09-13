from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm

from app.api.deps import AuthServiceDep
from app.core.security import create_access_token
from app.schemas.auth import TokenRead

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenRead)
async def login(
    form: Annotated[OAuth2PasswordRequestForm, Depends()], auth: AuthServiceDep
) -> TokenRead:
    """`form.username` carries the email — OAuth2's password-grant field names
    are fixed by the spec, not by our domain. Raises InvalidCredentialsError
    (-> 401) for both "no such user" and "wrong password", on purpose.
    """
    user = await auth.authenticate(form.username, form.password)
    token = create_access_token(subject=user.email)
    return TokenRead(access_token=token)
