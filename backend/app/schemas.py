from pydantic import BaseModel, HttpUrl, root_validator
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

    @root_validator(pre=True)
    def build_settings(cls, values):
        if 'settings' not in values:
            win_points = values.get('points_for_win')
            loss_points = values.get('points_for_loss')
            if win_points is not None and loss_points is not None:
                values['settings'] = LeagueSettings(points_for_win=win_points, points_for_loss=loss_points)
        return values

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
