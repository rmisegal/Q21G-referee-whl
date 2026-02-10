# Comparison: GmailAsReferee vs RLGM + GMC

**Version:** 1.0.0

This document provides a detailed comparison between the GmailAsReferee reference implementation and the proposed RLGM + GMC architecture.

---

## 1. Message Handling Comparison

| Message Type | GmailAsReferee | RLGM + GMC | Gap? |
|--------------|----------------|------------|------|
| **League Manager -> Referee** ||||
| BROADCAST_START_SEASON | `BroadcastStartSeasonHandler` | RLGM: `handlers_season.py` | No |
| SEASON_REGISTRATION_RESPONSE | `SeasonRegistrationResponseHandler` | RLGM: `handlers_season.py` | No |
| BROADCAST_ASSIGNMENT_TABLE | `BroadcastAssignmentTableHandler` | RLGM: `handlers_assignment.py` | No |
| BROADCAST_NEW_LEAGUE_ROUND | `BroadcastNewRoundHandler` | RLGM: `handlers_lifecycle.py` | No |
| BROADCAST_END_LEAGUE_ROUND | `BroadcastEndRoundHandler` | RLGM: `handlers_lifecycle.py` | No |
| BROADCAST_END_SEASON | `BroadcastEndSeasonHandler` | RLGM: `handlers_season.py` | No |
| BROADCAST_ROUND_RESULTS | `BroadcastRoundResultsHandler` | RLGM: `handlers_lifecycle.py` | No |
| BROADCAST_KEEP_ALIVE | `BroadcastKeepAliveHandler` | RLGM: `handlers_health.py` | No |
| BROADCAST_CRITICAL_RESET | `BroadcastCriticalResetHandler` | RLGM: `handlers_critical.py` | No |
| BROADCAST_CRITICAL_PAUSE | `BroadcastCriticalPauseHandler` | RLGM: `handlers_critical.py` | No |
| **Referee -> League Manager** ||||
| SEASON_REGISTRATION_REQUEST | `response_builder.py` | RLGM: `response_builder.py` | No |
| RESPONSE_GROUP_ASSIGNMENT | `assignment_handler.py` | RLGM: `handlers_assignment.py` | No |
| MATCH_RESULT_REPORT | `q21_message_builder.py` | RLGM: `orchestrator.py` | No |
| RESPONSE_KEEP_ALIVE | `broadcast_handlers_health.py` | RLGM: `handlers_health.py` | No |
| **Player -> Referee (Q21)** ||||
| Q21WARMUPRESPONSE | `Q21WarmupResponseHandler` | GMC: `_message_router.py` | No |
| Q21QUESTIONSBATCH | `Q21QuestionsBatchHandler` | GMC: `_message_router.py` | No |
| Q21GUESSSUBMISSION | `Q21GuessSubmissionHandler` | GMC: `_message_router.py` | No |
| **Referee -> Player (Q21)** ||||
| Q21WARMUPCALL | `q21_generators.py` | GMC: `_envelope_builder.py` | No |
| Q21ROUNDSTART | `q21_generators.py` | GMC: `_envelope_builder.py` | No |
| Q21ANSWERSBATCH | `q21_generators.py` | GMC: `_envelope_builder.py` | No |
| Q21SCOREFEEDBACK | `q21_generators.py` | GMC: `_envelope_builder.py` | No |

---

## 2. State Machine Comparison

| State | GmailAsReferee | RLGM + GMC | Gap? |
|-------|----------------|------------|------|
| INIT_START_STATE | `referee_state_machine.py` | RLGM: `state_machine.py` | No |
| WAITING_FOR_CONFIRMATION | `referee_state_machine.py` | RLGM: `state_machine.py` | No |
| WAITING_FOR_ASSIGNMENT | `referee_state_machine.py` | RLGM: `state_machine.py` | No |
| RUNNING | `referee_state_machine.py` | RLGM: `state_machine.py` | No |
| IN_GAME | `referee_state_machine.py` | RLGM: `state_machine.py` | No |
| PAUSED | `referee_state_machine.py` | RLGM: `state_machine.py` | No |
| COMPLETED | `referee_state_machine.py` | RLGM: `state_machine.py` | No |

---

## 3. Game Phase Comparison

| Phase | GmailAsReferee | GMC | Gap? |
|-------|----------------|-----|------|
| IDLE | N/A (uses SETUP) | `GamePhase.IDLE` | No |
| WARMUP | `Q21Phase.WARMUP` | `GamePhase.WARMUP_SENT` | No |
| WARMUP_COMPLETE | Implicit | `GamePhase.WARMUP_COMPLETE` | No |
| QUESTIONS | `Q21Phase.QUESTIONS_SUBMISSION` | `GamePhase.ROUND_STARTED` | No |
| ANSWERS | `Q21Phase.ANSWERING` | `GamePhase.ANSWERS_SENT` | No |
| GUESSING | `Q21Phase.GUESSING` | `GamePhase.SCORING_COMPLETE` | No |
| COMPLETE | `Q21Phase.FINISHED` | `GamePhase.MATCH_REPORTED` | No |

---

## 4. Database Table Comparison

| Table | GmailAsReferee | RLGM + GMC | Gap? |
|-------|----------------|------------|------|
| referee_seasons | Yes | RLGM: Yes | No |
| round_assignments | Yes | RLGM: Yes | No |
| assigned_matches | Yes | RLGM: Yes | No |
| broadcasts_received | Yes | RLGM: Yes | No |
| q21_game_state | Yes | GMC: In-memory | Different approach |
| player_responses | Yes | GMC: In-memory | Different approach |
| player_scores | Yes | GMC: In-memory | Different approach |

**Note:** GMC uses in-memory state for single-game lifecycle. RLGM persists season/assignment data to database for multi-game orchestration.

---

## 5. Callback Comparison

| Callback | GmailAsReferee | GMC | Gap? |
|----------|----------------|-----|------|
| get_warmup_question() | `RefereeStrategy` interface | `RefereeAI` abstract class | No |
| get_round_start_info() | `RefereeStrategy` interface | `RefereeAI` abstract class | No |
| get_answers() | `RefereeStrategy` interface | `RefereeAI` abstract class | No |
| get_score_feedback() | `RefereeStrategy` interface | `RefereeAI` abstract class | No |

---

## 6. Feature Comparison

| Feature | GmailAsReferee | RLGM + GMC | Gap? |
|---------|----------------|------------|------|
| Season registration | Yes | RLGM: Yes | No |
| Assignment handling | Yes | RLGM: Yes | No |
| Round management | Yes | RLGM: Yes | No |
| Multiple games per round | Yes | RLGM: Yes (sequential) | No |
| Game execution | Yes | GMC: Yes | No |
| Player communication | Yes | GMC: Yes | No |
| LM communication | Yes | RLGM: Yes | No |
| Match result reporting | Yes | RLGM: Yes | No |
| Callback validation | Partial | GMC: Full schema validation | No |
| Callback timeouts | Yes | GMC: Yes (30-180s) | No |
| State persistence | Database | RLGM: DB, GMC: Memory | Acceptable |
| Pause/Resume | Yes | RLGM: Yes | No |
| Critical reset | Yes | RLGM: Yes | No |
| Keep-alive | Yes | RLGM: Yes | No |

---

## 7. Verification Summary

| Category | Total Items | Covered | Gaps |
|----------|-------------|---------|------|
| LM -> Referee Messages | 10 | 10 | 0 |
| Referee -> LM Messages | 4 | 4 | 0 |
| Player -> Referee Messages | 3 | 3 | 0 |
| Referee -> Player Messages | 4 | 4 | 0 |
| State Machine States | 7 | 7 | 0 |
| Game Phases | 7 | 7 | 0 |
| Callbacks | 4 | 4 | 0 |
| Features | 14 | 14 | 0 |
| **TOTAL** | **53** | **53** | **0** |

---

## 8. Architectural Differences

### 8.1 Responsibility Split

| Aspect | GmailAsReferee | RLGM + GMC |
|--------|----------------|------------|
| Season management | Unified | RLGM |
| Game execution | Unified | GMC |
| LM communication | Unified | RLGM only |
| Player communication | Unified | GMC only |
| State persistence | All in DB | RLGM: DB, GMC: Memory |

### 8.2 Code Organization

| Aspect | GmailAsReferee | RLGM + GMC |
|--------|----------------|------------|
| Structure | Monolithic (100+ files) | Modular (RLGM + GMC packages) |
| Dependencies | PostgreSQL, Gmail API, etc. | Same, but cleanly separated |
| Testing | Complex integration tests | Isolated unit tests per component |
| Student exposure | N/A | Only 4 callbacks visible |

### 8.3 Deployment Model

| Aspect | GmailAsReferee | RLGM + GMC |
|--------|----------------|------------|
| Distribution | Full project clone | pip install q21-referee |
| Configuration | config.json + .env | Simple config dict |
| Obfuscation | None | RLGM/GMC internals Cythonized |

---

## 9. Conclusion

**No functional gaps exist** between the GmailAsReferee reference implementation and the proposed RLGM + GMC architecture.

The key differences are architectural:
1. **Separation of concerns**: RLGM handles season/LM; GMC handles games/players
2. **Simplified student API**: Only 4 callbacks exposed
3. **Modular design**: Easier to test, maintain, and extend
4. **Clean distribution**: pip-installable package with hidden complexity

Both implementations provide identical functionality from the League Manager's perspective.
