from pydantic import BaseModel, HttpUrl, model_validator
import uuid

class LeagueCreate(BaseModel):
    name: str
    points_for_win: int = 3
    points_for_loss: int = 0

class LeagueSettings(BaseModel):
    points_for_win: int
    points_for_loss: int

class LeagueRead(BaseModel):
    id: uuid.UUID
    name: str
    manager_id: uuid.UUID
    settings: LeagueSettings | None = None

    class Config:
        orm_mode = True

    @model_validator(mode='before')
    @classmethod
    def build_settings(cls, data):
        if isinstance(data, dict) and 'settings' not in data:
            win_points = data.get('points_for_win')
            loss_points = data.get('points_for_loss')
            if win_points is not None and loss_points is not None:
                data['settings'] = {'points_for_win': win_points, 'points_for_loss': loss_points}
        return data

class UserRead(BaseModel):
    id: uuid.UUID
    full_name: str
    role: str
    league_id: uuid.UUID | None

    class Config:
        orm_mode = True

class InviteLinkResponse(BaseModel):
    url: HttpUrl

class JoinLeagueRequest(BaseModel):
    invite_code: str


class ScoreInput(BaseModel):
    set_1_home: int
    set_1_away: int
    set_2_home: int
    set_2_away: int
    set_3_home: int | None = None
    set_3_away: int | None = None

class MatchCreate(BaseModel):
    league_id: uuid.UUID
    team_a_players: list[uuid.UUID]
    team_b_players: list[uuid.UUID]
    scores: ScoreInput

    @model_validator(mode='after')
    def check_players(self):
        team_a = self.team_a_players
        team_b = self.team_b_players

        if not team_a or not team_b:
            return self

        if len(team_a) != 2 or len(set(team_a)) != 2:
            raise ValueError("Team A must have exactly 2 unique players")

        if len(team_b) != 2 or len(set(team_b)) != 2:
            raise ValueError("Team B must have exactly 2 unique players")

        if len(set(team_a + team_b)) != 4:
            raise ValueError("All 4 players must be distinct")

        return self
