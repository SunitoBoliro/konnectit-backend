import logging

from fastapi import Query, HTTPException
from jose import jwt, JWTError
from starlette import status

from auth import SECRET_KEY, ALGORITHM


async def validate_token_endpoint(token: str = Query(...)):
    try:
        # Decode the token using the secret key and algorithm
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        logging.debug(f"Token payload: {payload}")
        return {"isValid": True}  # If no exception is raised, the token is valid
    except JWTError:
        logging.error("Invalid token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )
