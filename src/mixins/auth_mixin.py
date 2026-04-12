class AuthMixin:

    def __init__(self):
        self._user_id: str = "anonymous"
        self._user_role: str = "user"

    def set_auth_context(self, user_id: str, role: str = "user") -> None:
        self._user_id = user_id
        self._user_role = role

    def get_user_id(self) -> str:
        return self._user_id

    def is_admin(self) -> bool:
        return self._user_role == "admin"

    def get_auth_context(self) -> dict:
        return {
            "user_id": self._user_id,
            "role": self._user_role,
        }
