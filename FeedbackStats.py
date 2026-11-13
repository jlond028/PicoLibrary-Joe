"""
# FeedbackStats.py
# Tracks customer happy and unhappy feedback counts, calculates happiness percentage, and determines LightStrip colors
# Author: insert your name here
"""

from Log import *

# Default RGB color tuples matching Lights.py (used safely even if machine/Lights is not loaded yet)
GREEN_COLOR = (0, 255, 0)
YELLOW_COLOR = (255, 200, 0)
RED_COLOR = (255, 0, 0)


class FeedbackStats:
    """
    Model class for tracking store customer feedback statistics.
    Maintains **happy** and **unhappy** counts, computes the overall happiness
    percentage, maps the percentage to a **Green**, **Yellow**, or **Red** light
    color for a NeoPixel ring, and evaluates whether feedback has fallen below
    the alarm threshold.

    Parameters:
    ----------
    threshold : float, optional
        Minimum acceptable happy percentage before triggering the manager alarm (default: 30.0)
    min_responses : int, optional
        Minimum total feedback responses required before the alarm threshold can trigger (default: 5)

    Examples:
    ---------
    1. Create a FeedbackStats tracker and record feedback:
       `stats = FeedbackStats(threshold=30.0, min_responses=5)`
       `stats.add_happy()`
       `pct = stats.calculate_percentage()`
    2. Get the ring LightStrip color tuple and check the alarm threshold:
       `color = stats.get_light_level()`
       `alarm_needed = stats.is_below_threshold()`
    """

    def __init__(self, threshold=30.0, min_responses=5):
        """
        Initialize the feedback counters and threshold settings.

        Parameters:
        ----------
        threshold : float, optional
            Happiness percentage below which the alarm triggers (default: 30.0)
        min_responses : int, optional
            Minimum number of total responses before evaluating the threshold (default: 5)

        Examples:
        ---------
        1. `stats = FeedbackStats()`
        2. `stats = FeedbackStats(threshold=30.0, min_responses=5)`
        """
        self._happy_count = 0
        self._unhappy_count = 0
        self._threshold = float(threshold)
        self._min_responses = int(min_responses)
        Log.i(f"FeedbackStats initialized (threshold={self._threshold}%, min_responses={self._min_responses})")

    def get_happy_count(self):
        """
        Return the current number of **happy** responses.

        Parameters:
        ----------
        None

        Examples:
        ---------
        1. `happy = stats.get_happy_count()`
        2. `Log.i(f"Happy votes: {stats.get_happy_count()}")`
        """
        return self._happy_count

    def get_unhappy_count(self):
        """
        Return the current number of **unhappy** responses.

        Parameters:
        ----------
        None

        Examples:
        ---------
        1. `unhappy = stats.get_unhappy_count()`
        2. `Log.i(f"Unhappy votes: {stats.get_unhappy_count()}")`
        """
        return self._unhappy_count

    def get_total_count(self):
        """
        Return the total number of feedback responses (`happy + unhappy`).

        Parameters:
        ----------
        None

        Examples:
        ---------
        1. `total = stats.get_total_count()`
        2. `if stats.get_total_count() >= 5: ...`
        """
        return self._happy_count + self._unhappy_count

    def calculate_percentage(self):
        """
        Calculate and return the percentage of happy responses (`0.0` to `100.0`).
        Returns `100.0` when no responses have been recorded yet.

        Parameters:
        ----------
        None

        Examples:
        ---------
        1. `pct = stats.calculate_percentage()`
        2. `Log.i(f"Happiness: {stats.calculate_percentage():.1f}%")`
        """
        total = self.get_total_count()
        if total == 0:
            return 100.0
        return (self._happy_count / total) * 100.0

    def get_light_level(self):
        """
        Determine the RGB color tuple (`GREEN`, `YELLOW`, or `RED`) for the
        ring `LightStrip` based on the current happiness percentage:
        - **Green** `(0, 255, 0)`: `>= 60.0%` happy (or `0` total votes)
        - **Yellow** `(255, 200, 0)`: `30.0%` to `< 60.0%` happy
        - **Red** `(255, 0, 0)`: `< 30.0%` happy

        Parameters:
        ----------
        None

        Examples:
        ---------
        1. `color = stats.get_light_level()`
        2. `lightstrip.setColor(stats.get_light_level())`
        """
        try:
            from Lights import GREEN, YELLOW, RED
        except ImportError:
            GREEN, YELLOW, RED = GREEN_COLOR, YELLOW_COLOR, RED_COLOR

        pct = self.calculate_percentage()
        if pct >= 60.0:
            return GREEN
        elif pct >= self._threshold:
            return YELLOW
        else:
            return RED

    def is_below_threshold(self):
        """
        Check whether the feedback has at least `min_responses` total votes
        and a happiness percentage strictly below `threshold` (`< 30.0%`).

        Parameters:
        ----------
        None

        Examples:
        ---------
        1. `if stats.is_below_threshold(): controller.trigger_alarm()`
        2. `below = stats.is_below_threshold()`
        """
        total = self.get_total_count()
        pct = self.calculate_percentage()
        below = total >= self._min_responses and pct < self._threshold
        Log.i(f"FeedbackStats check: happy={self._happy_count}, unhappy={self._unhappy_count}, total={total}, pct={pct:.1f}%, below_threshold={below}")
        return below

    def add_happy(self):
        """
        Increment the **happy** feedback counter by 1.

        Parameters:
        ----------
        None

        Examples:
        ---------
        1. `stats.add_happy()`
        2. `stats.add_happy(); Log.i(f"Total: {stats.get_total_count()}")`
        """
        self._happy_count += 1
        pct = self.calculate_percentage()
        Log.i(f"FeedbackStats: Added happy vote (happy={self._happy_count}, unhappy={self._unhappy_count}, pct={pct:.1f}%)")

    def add_unhappy(self):
        """
        Increment the **unhappy** feedback counter by 1.

        Parameters:
        ----------
        None

        Examples:
        ---------
        1. `stats.add_unhappy()`
        2. `stats.add_unhappy(); Log.i(f"Total: {stats.get_total_count()}")`
        """
        self._unhappy_count += 1
        pct = self.calculate_percentage()
        Log.i(f"FeedbackStats: Added unhappy vote (happy={self._happy_count}, unhappy={self._unhappy_count}, pct={pct:.1f}%)")

    def reset(self):
        """
        Reset both `happy_count` and `unhappy_count` back to `0`.

        Parameters:
        ----------
        None

        Examples:
        ---------
        1. `stats.reset()`
        2. `stats.reset(); assert stats.get_total_count() == 0`
        """
        self._happy_count = 0
        self._unhappy_count = 0
        Log.i("FeedbackStats: Counts reset to 0")


if __name__ == "__main__":
    Log.i("Starting FeedbackStats self-test...")
    stats = FeedbackStats(threshold=30.0, min_responses=5)

    # Initial state check
    assert stats.get_total_count() == 0
    assert stats.calculate_percentage() == 100.0
    assert stats.get_light_level() == GREEN_COLOR
    assert not stats.is_below_threshold()

    # Add 1 happy, 1 unhappy -> 50% (Yellow), total = 2 (< 5 min responses)
    stats.add_happy()
    stats.add_unhappy()
    assert stats.get_total_count() == 2
    assert stats.calculate_percentage() == 50.0
    assert stats.get_light_level() == YELLOW_COLOR
    assert not stats.is_below_threshold()

    # Add 3 more unhappy -> 1 happy, 4 unhappy -> 20% (Red), total = 5 (>= 5 and < 30%)
    stats.add_unhappy()
    stats.add_unhappy()
    stats.add_unhappy()
    assert stats.get_total_count() == 5
    assert abs(stats.calculate_percentage() - 20.0) < 0.01
    assert stats.get_light_level() == RED_COLOR
    assert stats.is_below_threshold()

    # Reset check
    stats.reset()
    assert stats.get_total_count() == 0
    assert stats.calculate_percentage() == 100.0
    assert stats.get_light_level() == GREEN_COLOR
    assert not stats.is_below_threshold()

    Log.i("Testing complete - all FeedbackStats checks passed")
