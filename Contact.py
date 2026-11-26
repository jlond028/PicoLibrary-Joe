"""
# Contact.py
# Data model class representing a CRM customer contact retrieved from the REST API
# Author: Joseph Londono
"""

from Log import *


class Contact:
    """
    Represents a single contact associated with a CRM Customer.

    Parameters:
    ----------
    id : str
        Unique identifier of the contact (stored as string to preserve large IDs)
    name : str
        Full name of the contact
    title : str, optional
        Job title of the contact (default: "")
    company : str, optional
        Company name of the contact (default: "")
    phone : str, optional
        Phone number of the contact (default: "")
    contact_type : str, optional
        Role or category of the contact (default: "")

    Examples:
    ---------
    1. c = Contact("101", "James Johnson", "Manager", "Lights Inc.", "305 242 4511", "Product Manager")
    2. summary = c.getSummary()
    """

    def __init__(self, id, name, title="", company="", phone="", contact_type=""):
        """
        Initialize a Contact instance with attributes from the CRM REST API.

        Parameters:
        ----------
        id : str or int
            Unique contact ID
        name : str
            Contact's full name
        title : str, optional
            Contact's job title (default: "")
        company : str, optional
            Contact's company name (default: "")
        phone : str, optional
            Contact's phone number (default: "")
        contact_type : str, optional
            Contact's role/type (default: "")
        """
        self.id = str(id) if id is not None else ""
        self.name = name if name else "Unknown"
        self.title = title if title else ""
        self.company = company if company else ""
        self.phone = phone if phone else ""
        self.contact_type = contact_type if contact_type else ""
        Log.i(f"Contact: created '{self.name}' ({self.title})")

    def getSummary(self):
        """
        Return a concise summary string of the contact for logging or display.

        Examples:
        ---------
        1. contact.getSummary()
        """
        role = self.title or self.contact_type or self.company or "Contact"
        return f"{self.name} - {role}"

    def __str__(self):
        return self.getSummary()


if __name__ == "__main__":
    c = Contact(
        id=12891474447230973,
        name="James Johnson",
        title="Manager",
        company="Lights Inc.",
        phone="305 242 4511",
        contact_type="Product Manager",
    )
    summary = c.getSummary()
    Log.i(f"Contact summary: {summary}")
    assert c.name == "James Johnson"
    assert c.title == "Manager"
    assert summary == "James Johnson - Manager"

    c_null = Contact(id=None, name=None, title=None)
    Log.i(f"Null-safe contact summary: {c_null.getSummary()}")
    assert c_null.name == "Unknown"

    Log.i("Testing complete - Contact class passed all checks")
