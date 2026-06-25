from fastapi import Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from jose import jwt, JWTError

from backend.app.db.dependencies import get_db
from backend.app.models.user import User
from backend.app.auth.utils import (
    SECRET_KEY,
    ALGORITHM
)
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/auth/login"
)


def _extract_token(request: Request, token: str | None) -> str:
    if token:
        return token

    auth_header = request.headers.get("authorization")
    if auth_header:
        parts = auth_header.split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            return parts[1]
        if len(parts) == 2 and parts[0].lower() == "token":
            return parts[1]

    x_token = request.headers.get("x-access-token")
    if x_token:
        return x_token

    return request.query_params.get("token", "")


def get_current_user(
    request: Request,
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token = _extract_token(request, token)
    if not token:
        raise credentials_exception

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")

        if email is None:
            raise credentials_exception

    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.email == email).first()

    if user is None:
        raise credentials_exception

    return user