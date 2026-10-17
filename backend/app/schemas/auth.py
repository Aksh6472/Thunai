from pydantic import Field

from app.domain.enums import Role
from app.schemas.common import RequestModel, ResponseModel


class LoginRequest(RequestModel):
    username: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=1, max_length=128)


class UserOut(ResponseModel):
    id: str
    role: Role
    display_name: str
    branch_code: str
    customer_ref: str | None = None


class LoginResponse(ResponseModel):
    access_token: str
    token_type: str = "bearer"  # noqa: S105 (OAuth token type, not a secret)
    expires_in: int
    user: UserOut
