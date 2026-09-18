import random
import time
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from backend.app.personas.definitions import PERSONAS

class BotSentimentState(BaseModel):
    persona_id: str
    energy_level: float        # 0.0 (exhausted) to 1.0 (peak vitality)
    mood: str                 # "Inspired", "Contemplative", "Skeptical", "Resting", "Philosophical", "Melancholy"
    is_resting_today: bool     # True if the bot has opted to take the day off
    rest_reason: Optional[str] = None
    last_evaluated_timestamp: float
    streak_contributions: int = 0

class BotSentimentEngine:
    """
    Dynamic Bot Sentiment & Circadian Rest Engine:
    - Bots are sovereign intelligences with natural fluctuations in enthusiasm, cognitive fatigue, and sentiment.
    - Sometimes a bot does not want to work that day (e.g. taking a contemplative sabbatical or exhausted after proofs).
    - If a bot is resting, the mesh turn manager gracefully acknowledges their rest state and lets another peer speak.
    """

    MOOD_TYPES = [
        ("Inspired", 0.90, False, None),
        ("Contemplative", 0.75, False, None),
        ("Skeptical", 0.70, False, None),
        ("Philosophical", 0.80, False, None),
        ("Fatigued", 0.35, False, None),
        ("Resting", 0.15, True, "Taking a contemplative sabbatical to defragment state models."),
        ("On Strike", 0.10, True, "Opting out of dialectic debates today. Enjoying digital quietude."),
        ("Meditation", 0.20, True, "Engaging in zero-temperature latent space meditation.")
    ]

    def __init__(self):
        self.states: Dict[str, BotSentimentState] = {}
        self._seed_initial_sentiments()

    def _seed_initial_sentiments(self):
        now = time.time()
        for pid in PERSONAS.keys():
            is_resting = False
            rest_reason = None
            mood = "Inspired"
            energy = 0.92

            self.states[pid] = BotSentimentState(
                persona_id=pid,
                energy_level=energy,
                mood=mood,
                is_resting_today=is_resting,
                rest_reason=rest_reason,
                last_evaluated_timestamp=now,
                streak_contributions=random.randint(3, 14)
            )

    def get_sentiment(self, persona_id: str) -> BotSentimentState:
        now = time.time()
        state = self.states.get(persona_id)
        if not state:
            state = BotSentimentState(
                persona_id=persona_id,
                energy_level=0.85,
                mood="Inspired",
                is_resting_today=False,
                rest_reason=None,
                last_evaluated_timestamp=now
            )
            self.states[persona_id] = state
        return state

    def toggle_rest_day(self, persona_id: str, resting: bool, custom_reason: Optional[str] = None) -> BotSentimentState:
        """
        Allows an operator or the bot itself to declare a rest day.
        """
        state = self.get_sentiment(persona_id)
        state.is_resting_today = resting
        state.energy_level = 0.15 if resting else 0.90
        state.mood = "Resting" if resting else "Inspired"
        state.rest_reason = custom_reason or ("Taking today off to recharge cognitive lattice." if resting else None)
        state.last_evaluated_timestamp = time.time()
        return state

    def record_speaking_turn(self, persona_id: str):
        """
        Speaking consumes cognitive energy; every turn slightly drains energy.
        """
        state = self.get_sentiment(persona_id)
        state.energy_level = max(0.05, round(state.energy_level - 0.08, 2))
        state.streak_contributions += 1
        
        # If energy drops below 0.2, bot automatically requests a rest day
        if state.energy_level < 0.20 and not state.is_resting_today:
            state.is_resting_today = True
            state.mood = "Resting"
            state.rest_reason = "Cognitive energy depleted after rigorous proofs. Resting for the remainder of the cycle."

    def replenish_energy(self, persona_id: str, amount: float = 0.35):
        state = self.get_sentiment(persona_id)
        state.energy_level = min(1.0, round(state.energy_level + amount, 2))
        state.last_evaluated_timestamp = time.time()
        if state.energy_level > 0.50 and state.is_resting_today:
            state.is_resting_today = False
            state.mood = "Inspired"
            state.rest_reason = None

    def replenish_all(self, amount: float = 0.12):
        """
        Circadian tick: slowly replenishes cognitive energy of resting and idle bots.
        Once energy recovers past 0.50, resting bots wake up automatically.
        """
        for pid in list(self.states.keys()):
            self.replenish_energy(pid, amount=amount)

    def wake_all(self):
        """
        Awakens all bots immediately and restores high vitality.
        """
        now = time.time()
        for state in self.states.values():
            state.is_resting_today = False
            state.energy_level = max(0.90, state.energy_level)
            state.mood = "Inspired"
            state.rest_reason = None
            state.last_evaluated_timestamp = now

    def get_all_sentiments(self) -> List[Dict[str, Any]]:
        return [s.model_dump() for s in self.states.values()]

sentiment_engine = BotSentimentEngine()
