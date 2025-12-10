from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from app.database import get_session
from app.models import League, User, UserRole
from app.schemas import LeagueCreate, LeagueRead, InviteLinkResponse, UserRead, JoinLeagueRequest
import uuid

router = APIRouter()

# Mock user authentication
def get_current_user(session: Session = Depends(get_session)) -> User:
    user = session.exec(select(User).where(User.email == "test@example.com")).first()
    if not user:
        user = User(
            id=uuid.uuid4(),
            email="test@example.com",
            full_name="Test User",
            role=UserRole.player,
        )
        session.add(user)
        session.commit()
        session.refresh(user)
    return user

@router.post("/leagues/", response_model=LeagueRead)
def create_league(league: LeagueCreate, db: Session = Depends(get_session), current_user: User = Depends(get_current_user)):
    # The user creating the league becomes the manager
    current_user.role = UserRole.manager

    new_league = League(
        name=league.name,
        manager_id=current_user.id,
        points_for_win=league.points_for_win,
        points_for_loss=league.points_for_loss,
    )

    db.add(new_league)
    current_user.league_id = new_league.id
    db.add(current_user)
    db.commit()
    db.refresh(new_league)

    return LeagueRead.from_orm(new_league)

@router.get("/leagues/{league_id}/invite", response_model=InviteLinkResponse)
def get_invite_link(league_id: uuid.UUID, db: Session = Depends(get_session), current_user: User = Depends(get_current_user)):
    league = db.get(League, league_id)
    if not league:
        raise HTTPException(status_code=404, detail="League not found")

    if league.manager_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the league manager can generate invite links")

    # In a real app, this would be a unique, expiring token
    invite_code = str(league.id)
    url = f"https://app.padelmanager.com/join?code={invite_code}"
    return InviteLinkResponse(url=url)

@router.post("/leagues/join", response_model=UserRead)
def join_league(request: JoinLeagueRequest, db: Session = Depends(get_session), current_user: User = Depends(get_current_user)):
    try:
        league_id = uuid.UUID(request.invite_code)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid invite code")

    league = db.get(League, league_id)
    if not league:
        raise HTTPException(status_code=404, detail="League not found")

    current_user.league_id = league.id
    current_user.role = UserRole.player
    db.add(current_user)
    db.commit()
    db.refresh(current_user)

    return current_user
