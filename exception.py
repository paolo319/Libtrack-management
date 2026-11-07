from fastapi import HTTPException, status


def conflict(message: str):
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail={"message": message}
    )


def unauthorized(message: str):
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"message": message}
    )