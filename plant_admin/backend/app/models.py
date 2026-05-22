"""仅类型定义（无 ORM），数据行使用 dict / Pydantic 校验。"""

from dataclasses import dataclass


@dataclass
class PlantAdminUser:
    id: int
    username: str
    password_hash: str
    role: str
    is_active: bool
