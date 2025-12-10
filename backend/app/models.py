import uuid
from datetime import datetime
from enum import Enum
from typing import List, Optional

from sqlmodel import Field, Relationship, SQLModel


class UserRole(str, Enum):
    super_admin = "super_admin"
    manager = "manager"
    player = "player"


class MatchStatus(str, Enum):
    pending = "pending"
    approved = "approved"


class User(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    email: str = Field(unique=True, index=True)
    full_name: str
    role: UserRole = Field(default=UserRole.player)
    league_id: Optional[uuid.UUID] = Field(default=None, foreign_key="league.id")

    league: Optional["League"] = Relationship(back_populates="players")


class League(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str
    manager_id: uuid.UUID = Field(foreign_key="user.id")
    logo_url: Optional[str] = None
    points_for_win: int = 3
    points_for_loss: int = 0

    manager: User = Relationship()
    players: List[User] = Relationship(back_populates="league")
    matches: List["Match"] = Relationship(back_populates="league")


class Match(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    league_id: uuid.UUID = Field(foreign_key="league.id")
    date: datetime = Field(default_factory=datetime.utcnow)
    status: MatchStatus
    submitted_by: uuid.UUID = Field(foreign_key="user.id")

    summary_text: Optional[str] = None

    league: League = Relationship(back_populates="matches")
    submitter: User = Relationship()
    participants: List["MatchParticipant"] = Relationship(back_populates="match")
    score: Optional["Score"] = Relationship(back_populates="match")


class MatchParticipant(SQLModel, table=True):
    match_id: uuid.UUID = Field(foreign_key="match.id", primary_key=True)
    player_id: uuid.UUID = Field(foreign_key="user.id", primary_key=True)
    team: str  # "A" or "B"

    match: Match = Relationship(back_populates="participants")
    player: User = Relationship()


class Score(SQLModel, table=True):
    match_id: uuid.UUID = Field(foreign_key="match.id", primary_key=True)
    set_1_home: int
    set_1_away: int
    set_2_home: int
    set_2_away: int
    set_3_home: Optional[int] = None
    set_3_away: Optional[int] = None

    match: Match = Relationship(back_populates="score")
