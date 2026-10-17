"""T-026: episodes open, extend, expire after 7 quiet days, and close (AI_DESIGN §5.2)."""

from datetime import timedelta

import pytest

from app.domain.enums import EpisodeStatus, Stage, Tier
from app.domain.episodes import close, expire, is_expired, update_episode, with_watch
from tests.factories import cfg, ist, stage


def test_first_stage_opens_an_episode() -> None:
    episode = update_episode(None, stage(Stage.S1_LIQUIDATION, ist(1, 10)), cfg())
    assert episode.status is EpisodeStatus.OPEN
    assert episode.opened_at == ist(1, 10)
    assert len(episode.stages) == 1


def test_later_stages_extend_the_open_episode() -> None:
    episode = update_episode(None, stage(Stage.S1_LIQUIDATION, ist(1, 10)), cfg())
    episode = update_episode(episode, stage(Stage.S2_POOLING, ist(2, 11)), cfg())
    assert [s.stage for s in episode.stages] == [Stage.S1_LIQUIDATION, Stage.S2_POOLING]
    assert episode.last_stage_at == ist(2, 11)
    assert episode.opened_at == ist(1, 10)


def test_episode_expires_after_seven_quiet_days() -> None:
    episode = update_episode(None, stage(Stage.S1_LIQUIDATION, ist(1, 10)), cfg())
    assert not is_expired(episode, ist(8, 10), cfg())
    assert is_expired(episode, ist(8, 10) + timedelta(minutes=1), cfg())
    expired = expire(episode, cfg())
    assert expired.status is EpisodeStatus.EXPIRED
    assert expired.closed_at == ist(8, 10)


def test_stage_after_expiry_opens_a_fresh_episode() -> None:
    episode = update_episode(None, stage(Stage.S1_LIQUIDATION, ist(1, 10)), cfg())
    fresh = update_episode(episode, stage(Stage.S3_NEW_PAYEE, ist(10, 10)), cfg())
    assert fresh.opened_at == ist(10, 10)
    assert [s.stage for s in fresh.stages] == [Stage.S3_NEW_PAYEE]


def test_closed_benign_does_not_whitelist_new_stages() -> None:
    episode = update_episode(None, stage(Stage.S1_LIQUIDATION, ist(1, 10)), cfg())
    closed = close(episode, EpisodeStatus.CLOSED_BENIGN, ist(1, 12))
    fresh = update_episode(closed, stage(Stage.S3_NEW_PAYEE, ist(1, 13)), cfg())
    assert fresh.status is EpisodeStatus.OPEN
    assert fresh.opened_at == ist(1, 13)


def test_close_requires_a_closed_status() -> None:
    episode = update_episode(None, stage(Stage.S1_LIQUIDATION, ist(1, 10)), cfg())
    with pytest.raises(ValueError, match="closed status"):
        close(episode, EpisodeStatus.OPEN, ist(1, 12))


def test_watch_history_appends_points() -> None:
    episode = update_episode(None, stage(Stage.S1_LIQUIDATION, ist(1, 10)), cfg())
    episode = with_watch(episode, 15, Tier.LOW, ist(1, 10), "EVT-1")
    episode = with_watch(episode, 40, Tier.MEDIUM, ist(2, 18), "SIG-1")
    assert [p.score for p in episode.watch_history] == [15, 40]
    assert (episode.watch_score, episode.watch_tier) == (40, Tier.MEDIUM)
