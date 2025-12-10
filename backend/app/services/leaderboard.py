import uuid
from typing import List, Dict
from pydantic import BaseModel, Field
from sqlmodel import Session, select
from sqlalchemy.orm import selectinload
from app.models import League, Match, MatchStatus, User

class PlayerStats(BaseModel):
    player_id: uuid.UUID
    player_name: str
    matches_played: int = 0
    wins: int = 0
    losses: int = 0
    points: int = 0
    win_percentage: float = 0.0
    sets_won: int = 0
    sets_lost: int = 0
    set_diff: int = 0
    games_won: int = 0
    games_lost: int = 0
    game_diff: int = 0
    streak: List[str] = Field(default_factory=list)


def calculate_leaderboard(league_id: uuid.UUID, session: Session) -> List[PlayerStats]:
    # Step A: Fetch Data
    league = session.get(League, league_id)
    if not league:
        return []

    statement = (
        select(Match)
        .where(Match.league_id == league_id, Match.status == MatchStatus.approved)
        .order_by(Match.date)
        .options(
            selectinload(Match.participants).selectinload(User),
            selectinload(Match.score),
            selectinload(Match.league)
        )
    )
    matches = session.exec(statement).all()

    # Step B: Aggregate Stats
    stats: Dict[uuid.UUID, PlayerStats] = {
        player.id: PlayerStats(player_id=player.id, player_name=player.full_name)
        for player in league.players
    }

    for match in matches:
        if not match.score:
            continue

        # Determine winner
        score = match.score
        team_a_sets_won = (1 if score.set_1_home > score.set_1_away else 0) + \
                          (1 if score.set_2_home > score.set_2_away else 0) + \
                          (1 if score.set_3_home is not None and score.set_3_home > score.set_3_away else 0)

        team_b_sets_won = (1 if score.set_1_away > score.set_1_home else 0) + \
                          (1 if score.set_2_away > score.set_2_home else 0) + \
                          (1 if score.set_3_away is not None and score.set_3_away > score.set_3_home else 0)

        if team_a_sets_won == team_b_sets_won:
            continue

        winner_team = "A" if team_a_sets_won > team_b_sets_won else "B"

        team_a_games_won = score.set_1_home + score.set_2_home + (score.set_3_home or 0)
        team_b_games_won = score.set_1_away + score.set_2_away + (score.set_3_away or 0)

        for participant in match.participants:
            player_stat = stats.get(participant.player_id)
            if not player_stat:
                continue
            player_stat.matches_played += 1

            is_winner = (participant.team == "A" and winner_team == "A") or \
                        (participant.team == "B" and winner_team == "B")

            if is_winner:
                player_stat.wins += 1
                player_stat.points += league.points_for_win
                player_stat.streak.append("W")
            else:
                player_stat.losses += 1
                player_stat.points += league.points_for_loss
                player_stat.streak.append("L")

            player_stat.streak = player_stat.streak[-5:]

            if participant.team == "A":
                player_stat.sets_won += team_a_sets_won
                player_stat.sets_lost += team_b_sets_won
                player_stat.games_won += team_a_games_won
                player_stat.games_lost += team_b_games_won
            else: # Team B
                player_stat.sets_won += team_b_sets_won
                player_stat.sets_lost += team_a_sets_won
                player_stat.games_won += team_b_games_won
                player_stat.games_lost += team_a_games_won

    leaderboard = list(stats.values())

    for ps in leaderboard:
        if ps.matches_played > 0:
            ps.win_percentage = round((ps.wins / ps.matches_played) * 100, 2)
        ps.set_diff = ps.sets_won - ps.sets_lost
        ps.game_diff = ps.games_won - ps.games_lost

    # Step C: Sorting Logic
    leaderboard.sort(
        key=lambda p: (p.points, p.win_percentage, p.set_diff, p.game_diff),
        reverse=True
    )

    # Step D: Return
    return leaderboard
