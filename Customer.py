"""
# Customer.py
# Data model class representing a CRM Customer with composed Contact and Activity lists
# Author: Joseph Londono
"""

from Log import *


class Customer:
    """
    Represents a CRM Customer (Client) and manages its associated Contact and Activity objects.

    Parameters:
    ----------
    id : str or int
        Unique identifier of the customer (stored as string to preserve large 39-digit IDs)
    customer_name : str
        Name of the customer / client
    category : str, optional
        Customer category (e.g., "Consumer", "Corporate") (default: "")
    category_description : str, optional
        Description of the category (default: "")
    geography_name : str, optional
        Geographic region (e.g., "North America") (default: "")
    cust_type : str, optional
        Customer stage/type (e.g., "Production", "PoC") (default: "")

    Examples:
    ---------
    1. cust = Customer("19", "Illumina Biotech", "Consumer", "General Consumer", "North America")
    2. cust.addContact(contact)
    3. cust.addActivity(activity)
    4. count = cust.getActivityCount()
    """

    def __init__(
        self,
        id,
        customer_name,
        category="",
        category_description="",
        geography_name="",
        cust_type="",
    ):
        """
        Initialize a Customer instance.

        Parameters:
        ----------
        id : str or int
            Unique customer ID
        customer_name : str
            Display name of the customer
        category : str, optional
            Customer category (default: "")
        category_description : str, optional
            Description of the customer category (default: "")
        geography_name : str, optional
            Customer geography/region (default: "")
        cust_type : str, optional
            Customer type/stage (default: "")
        """
        self.id = str(id) if id is not None else ""
        self.customer_name = customer_name if customer_name else "Unnamed"
        self.category = category if category else "N/A"
        self.category_description = category_description if category_description else ""
        self.geography_name = geography_name if geography_name else "N/A"
        self.type = cust_type if cust_type else "N/A"
        self.contacts = []
        self.activities = []
        self.detailsLoaded = False
        Log.i(f"Customer: created '{self.customer_name}' (id={self.id})")

    def addContact(self, contact):
        """
        Add a Contact object to this customer.

        Parameters:
        ----------
        contact : Contact
            The Contact instance to associate with this customer

        Examples:
        ---------
        1. customer.addContact(contact)
        """
        self.contacts.append(contact)
        Log.i(f"Customer '{self.customer_name}': added contact '{contact.name}'")

    def addActivity(self, activity):
        """
        Add an Activity object to this customer.

        Parameters:
        ----------
        activity : Activity
            The Activity instance to associate with this customer

        Examples:
        ---------
        1. customer.addActivity(activity)
        """
        self.activities.append(activity)
        Log.i(f"Customer '{self.customer_name}': added activity '{activity.name}'")

    def getContacts(self):
        """
        Return the list of Contact objects for this customer.

        Examples:
        ---------
        1. contacts = customer.getContacts()
        """
        return self.contacts

    def getActivities(self):
        """
        Return the list of Activity objects for this customer.

        Examples:
        ---------
        1. activities = customer.getActivities()
        """
        return self.activities

    def getActivityCount(self):
        """
        Return the total number of activities recorded for this customer.

        Examples:
        ---------
        1. n = customer.getActivityCount()
        """
        return len(self.activities)

    def hasDetailsLoaded(self):
        """
        Return True if contacts and activities have already been loaded for this customer.

        Examples:
        ---------
        1. if not customer.hasDetailsLoaded(): ...
        """
        return self.detailsLoaded

    def setDetailsLoaded(self, loaded=True):
        """
        Mark whether contacts and activities have been loaded for this customer.

        Parameters:
        ----------
        loaded : bool, optional
            Loaded state flag (default: True)

        Examples:
        ---------
        1. customer.setDetailsLoaded(True)
        """
        self.detailsLoaded = loaded

    def __str__(self):
        return f"{self.customer_name} ({self.category})"


if __name__ == "__main__":
    from Contact import Contact
    from Activity import Activity

    cust = Customer(
        id="128914493284257047125893002539859332792",
        customer_name="Joseph Londono",
        category="Consumer",
        category_description="General Consumer",
        geography_name="North America",
        cust_type=None,
    )
    assert not cust.hasDetailsLoaded()

    cust.addContact(Contact("1", "James Johnson", "Manager", "Lights Inc.", "305 242 4511", "Product Manager"))
    cust.addActivity(Activity("6", "Meeting", "Face-to-Face", "In person meeting"))
    cust.addActivity(Activity("2", "Phone Call", "Cold Call", owner="Jack Han"))
    cust.setDetailsLoaded(True)

    Log.i(f"Customer '{cust.customer_name}' contacts={len(cust.getContacts())}, activities={cust.getActivityCount()}")
    assert len(cust.getContacts()) == 1
    assert cust.getActivityCount() == 2
    assert cust.hasDetailsLoaded()

    Log.i("Testing complete - Customer class passed all checks")
