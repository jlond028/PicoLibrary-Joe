"""
# Calendar.py
# Simulated calendar event management for office nameplate scheduling
# Author: insert your name here
"""

import time
try:
    from Log import *
except ImportError:
    class Log:
        @classmethod
        def i(cls, msg): print(f"[INFO] {msg}")
        @classmethod
        def d(cls, msg): print(f"[DEBUG] {msg}")
        @classmethod
        def w(cls, msg): print(f"[WARN] {msg}")
        @classmethod
        def e(cls, msg): print(f"[ERROR] {msg}")

try:
    ticks_ms = time.ticks_ms
    ticks_diff = time.ticks_diff
except AttributeError:
    # Desktop Python fallback for local testing
    ticks_ms = lambda: int(time.time() * 1000)
    ticks_diff = lambda a, b: a - b


class Calendar:
    """
    Manages schedule events and computes current availability status.
    Supports fast-forward simulation so calendar transitions can be observed
    in demonstrations and simulated environments.

    Parameters:
    ----------
    sim_start_hour : int, optional
        Starting hour for fast-forward simulation (0-23, default: 9 for 09:00 AM)
    sec_per_sim_hour : int, optional
        Number of real seconds that represent one simulated hour (default: 10)

    Examples:
    ---------
    1. cal = Calendar()
       cal.addEvent("Staff Meeting", "09:00", "10:00", "Busy")
       status = cal.getCurrentStatus()
    """

    def __init__(self, sim_start_hour: int = 9, sec_per_sim_hour: int = 10):
        """
        Initialize the calendar event list and simulation timebase.
        """
        Log.i("Calendar: Initializing simulated calendar")
        self._events = []
        self._sim_start_minute = sim_start_hour * 60
        self._sec_per_sim_hour = max(1, sec_per_sim_hour)
        self._start_ticks = ticks_ms()

    def addEvent(self, title: str, startTime: str, endTime: str, status: str) -> None:
        """
        Add a scheduled event to the calendar.

        Parameters:
        ----------
        title : str
            Descriptive title of the event (e.g. "Department Meeting")
        startTime : str
            Start time formatted as "HH:MM" (24-hour format)
        endTime : str
            End time formatted as "HH:MM" (24-hour format)
        status : str
            Availability status during the event ("Available", "Away", or "Busy")
        """
        event = {
            "title": title,
            "startTime": startTime,
            "endTime": endTime,
            "status": status
        }
        self._events.append(event)
        Log.i(f"Calendar: Added event '{title}' [{startTime}-{endTime}] -> {status}")

    def getCurrentStatus(self) -> str:
        """
        Determine current availability status based on active simulated time.

        Returns:
        -------
        str : "Available", "Away", or "Busy" based on active scheduled event.
        """
        sim_time_str = self.getSimulatedTime()

        for event in self._events:
            if event["startTime"] <= sim_time_str < event["endTime"]:
                Log.i(f"Calendar: Active event '{event['title']}' at {sim_time_str} -> {event['status']}")
                return event["status"]

        # Default availability when no event is scheduled
        return "Available"

    def getSimulatedTime(self) -> str:
        """
        Helper method to compute and return current simulated time as "HH:MM".
        """
        elapsed_ms = ticks_diff(ticks_ms(), self._start_ticks)
        ms_per_sim_minute = (self._sec_per_sim_hour * 1000) / 60
        elapsed_sim_minutes = int(elapsed_ms / ms_per_sim_minute)

        current_total_minutes = (self._sim_start_minute + elapsed_sim_minutes) % 1440
        hour = current_total_minutes // 60
        minute = current_total_minutes % 60
        return f"{hour:02d}:{minute:02d}"


if __name__ == "__main__":
    Log.i("--- Testing Calendar Class ---")
    cal = Calendar(sim_start_hour=9, sec_per_sim_hour=2)

    cal.addEvent("Staff Meeting", "09:00", "10:00", "Busy")
    cal.addEvent("Office Hours", "10:00", "11:00", "Available")
    cal.addEvent("Lunch Break", "11:00", "12:00", "Away")

    sim_time = cal.getSimulatedTime()
    status = cal.getCurrentStatus()
    Log.i(f"Initial simulated time: {sim_time}, status: {status}")
    assert status == "Busy", f"Expected Busy at 09:00, got {status}"

    Log.i("Testing complete - all Calendar checks passed")
