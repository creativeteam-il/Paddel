import uuid
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlmodel import Session, select

from app.database import get_session, engine
from app.models import Match, MatchParticipant, Score, User, MatchStatus
from app.schemas import MatchCreate
from app.services.ai import generate_match_summary

router = APIRouter()

def is_valid_set_score(home: int, away: int) -> bool:
    """Validates a single Padel set score."""
    if home < 0 or away < 0:
        return False

    # Case 1: Standard win (e.g., 6-4, 6-3)
    if (home == 6 and away < 5) or (away == 6 and home < 5):
        return True

    # Case 2: Extended set (e.g., 7-5 or 7-6 tie-break)
    if (home == 7 and 5 <= away <= 6) or (away == 7 and 5 <= home <= 6):
        return True

    return False

def get_player_names(db: Session, player_ids: list[uuid.UUID]) -> dict[uuid.UUID, str]:
    """Fetches player names from a list of IDs."""
    players = db.exec(select(User).where(User.id.in_(player_ids))).all()
    return {player.id: player.full_name for player in players}


# Placeholder for user authentication
def get_current_user(db: Session = Depends(get_session)) -> User:
    """
    Placeholder dependency to simulate fetching the authenticated user.
    In a real application, this would be replaced with your actual authentication logic
    (e.g., decoding a JWT token).
    """
    user = db.exec(select(User)).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found for placeholder auth")
    return user


async def update_match_summary(match_id: uuid.UUID):
    """
    Background task to generate and save the AI match summary.
    """
    # Create a new database session for the background task
    with Session(engine) as db:
        match = db.get(Match, match_id)
        if not match:
            return

        player_names = get_player_names(db, [p.player_id for p in match.participants])

        team_a_players = [p for p in match.participants if p.team == "A"]
        team_b_players = [p for p in match.participants if p.team == "B"]

        match_data_for_ai = {
            "team_a": [player_names[p.player_id] for p in team_a_players],
            "team_b": [player_names[p.player_id] for p in team_b_players],
            "scores": {
                "set_1": f"{match.score.set_1_home}-{match.score.set_1_away}",
                "set_2": f"{match.score.set_2_home}-{match.score.set_2_away}",
                "set_3": f"{match.score.set_3_home}-{match.score.set_3_away}" if match.score.set_3_home is not None else None,
            },
        }

        summary = await generate_match_summary(match_data_for_ai)
        match.summary_text = summary
        db.add(match)
        db.commit()


@router.post("/matches/", status_code=201)
async def create_match(
    match_data: MatchCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Endpoint to report a new match.
    """
    # 1. Validation
    all_player_ids = match_data.team_a_players + match_data.team_b_players
    players = db.exec(select(User).where(User.id.in_(all_player_ids))).all()

    if len(players) != 4:
        raise HTTPException(status_code=404, detail="One or more players not found")

    for player in players:
        if player.league_id != match_data.league_id:
            raise HTTPException(
                status_code=400,
                detail=f"Player {player.full_name} is not in the specified league.",
            )

    # Validate scores
    scores = match_data.scores
    if not is_valid_set_score(scores.set_1_home, scores.set_1_away) or \
       not is_valid_set_score(scores.set_2_home, scores.set_2_away):
        raise HTTPException(status_code=400, detail="Invalid score in the first two sets.")

    if scores.set_3_home is not None and scores.set_3_away is not None:
        if not is_valid_set_score(scores.set_3_home, scores.set_3_away):
            raise HTTPException(status_code=400, detail="Invalid score in the third set.")


    # 2. Persistence
    new_match = Match(
        league_id=match_data.league_id,
        status=MatchStatus.pending,
        submitted_by=current_user.id
    )
    db.add(new_match)
    db.flush() # To get the new_match.id

    participants = []
    for player_id in match_data.team_a_players:
        participants.append(MatchParticipant(match_id=new_match.id, player_id=player_id, team="A"))
    for player_id in match_data.team_b_players:
        participants.append(MatchParticipant(match_id=new_match.id, player_id=player_id, team="B"))

    new_score = Score(match_id=new_match.id, **scores.dict())

    db.add_all(participants)
    db.add(new_score)
    db.commit()
    db.refresh(new_match)

    # 3. AI Trigger
    background_tasks.add_task(update_match_summary, new_match.id)

    return new_match
