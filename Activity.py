"""
# Activity.py
# Data model class representing a CRM customer activity retrieved from the REST API
# Author: Joseph Londono
"""

from Log import *


class Activity:
    """
    Represents a single activity performed with a CRM Customer.

    Parameters:
    ----------
    id : str
        Unique identifier of the activity
    activity_type : str
        Type of activity (e.g., "Meeting", "Phone Call")
    name : str
        Short name of the activity (e.g., "Face-to-Face", "Cold Call")
    description : str, optional
        Detailed description of the activity (default: "")
    activity_date : str, optional
        Date of the activity (default: "")
    owner : str, optional
        Person responsible for the activity (default: "")
    location : str, optional
        Location where the activity occurred (default: "")

    Examples:
    ---------
    1. a = Activity("6", "Meeting", "Face-to-Face", "In person meeting")
    2. summary = a.getSummary()
    """

    def __init__(
        self,
        id,
        activity_type,
        name,
        description="",
        activity_date="",
        owner="",
        location="",
    ):
        """
        Initialize an Activity instance with attributes from the CRM REST API.

        Parameters:
        ----------
        id : str or int
            Unique activity ID
        activity_type : str
            Category of activity (e.g., "Meeting", "Phone Call")
        name : str
            Activity name (e.g., "Face-to-Face")
        description : str, optional
            Activity description (default: "")
        activity_date : str, optional
            Activity date string (default: "")
        owner : str, optional
            Activity owner name (default: "")
        location : str, optional
            Activity location (default: "")
        """
        self.id = str(id) if id is not None else ""
        self.activity_type = activity_type if activity_type else "Activity"
        self.name = name if name else "Unnamed"
        self.description = description if description else ""
        self.activity_date = activity_date if activity_date else ""
        self.owner = owner if owner else ""
        self.location = location if location else ""
        Log.i(f"Activity: created '{self.activity_type}: {self.name}'")

    def getSummary(self):
        """
        Return a concise summary string of the activity for logging or display.

        Examples:
        ---------
        1. activity.getSummary()
        """
        return f"{self.activity_type}: {self.name}"

    def __str__(self):
        return self.getSummary()


if __name__ == "__main__":
    a = Activity(
        id=6,
        activity_type="Meeting",
        name="Face-to-Face",
        description="In person meeting with customer / prospect",
        activity_date=None,
        owner=None,
        location=None,
    )
    summary = a.getSummary()
    Log.i(f"Activity summary: {summary}")
    assert a.id == "6"
    assert a.activity_type == "Meeting"
    assert summary == "Meeting: Face-to-Face"

    a_call = Activity(id=2, activity_type="Phone Call", name="Cold Call", owner="Jack Han")
    Log.i(f"Second activity: {a_call.getSummary()} (owner={a_call.owner})")
    assert a_call.owner == "Jack Han"

    Log.i("Testing complete - Activity class passed all checks")
