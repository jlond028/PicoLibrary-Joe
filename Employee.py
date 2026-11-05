"""
# Employee.py
# Domain model representing employees, faculty, staff, administrators, and student workers
# Author: insert your name here
"""

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
from Calendar import Calendar


def _format_lcd_line(text: str, width: int = 16) -> str:
    """Helper function to format text to exactly width characters in MicroPython."""
    return (str(text) + (" " * width))[:width]


class Employee:
    """
    Abstract base class representing an employee in the system.
    Provides standard availability management and defines the polymorphic
    interface for LCD text generation.

    Parameters:
    ----------
    name : str
        Full or display name of the employee
    title : str
        Job title or role description
    department : str
        Department or academic unit
    phone : str
        Official phone number or campus extension
    availability : str, optional
        Initial status: "Available", "Away", or "Busy" (default: "Available")

    Examples:
    ---------
    1. emp = Employee("Jane Doe", "Advisor", "Student Affairs", "555-0142")
       emp.cycleAvailability()
    """

    AVAILABLE = "Available"
    AWAY = "Away"
    BUSY = "Busy"
    STATUSES = [AVAILABLE, AWAY, BUSY]

    def __init__(self, name: str, title: str, department: str, phone: str, availability: str = "Available"):
        self._name = name
        self._title = title
        self._department = department
        self._phoneNumber = phone
        self._availability = availability
        Log.i(f"Employee: Created {name} ({title}) in {department} [Phone: {phone}, {availability}]")

    def getName(self) -> str:
        """Return employee name."""
        return self._name

    def getPhoneNumber(self) -> str:
        """Return employee phone number."""
        return self._phoneNumber

    def getPhone(self) -> str:
        """Convenience alias for getPhoneNumber."""
        return self._phoneNumber

    def getAvailability(self) -> str:
        """Return current availability status."""
        return self._availability

    def setAvailability(self, status: str) -> None:
        """Set employee availability status."""
        if status in self.STATUSES:
            self._availability = status
            Log.i(f"Employee {self._name}: Availability set to {status}")
        else:
            Log.w(f"Employee {self._name}: Unknown availability status '{status}'")

    def cycleAvailability(self) -> None:
        """Cycle availability between Available -> Away -> Busy -> Available."""
        current = self.getAvailability()
        try:
            current_idx = self.STATUSES.index(current)
        except ValueError:
            current_idx = 0
        new_status = self.STATUSES[(current_idx + 1) % len(self.STATUSES)]
        self.setAvailability(new_status)

    def getDisplayLines(self) -> tuple:
        """
        Return a tuple of (line1, line2) page tuples for 16x2 LCD display.
        """
        status_abbr = self.getAvailability()[:4]
        line1 = _format_lcd_line(f"{self._name[:10]} [{status_abbr}]")
        page0 = (line1, _format_lcd_line(self._title))
        page1 = (line1, _format_lcd_line(self._department))
        page2 = (line1, _format_lcd_line(f"Ph: {self._phoneNumber}"))
        return (page0, page1, page2)


class Faculty(Employee):
    """
    Represents faculty members with assigned courses and office hours.

    Parameters:
    ----------
    name : str
        Name of faculty member
    title : str
        Academic title (e.g., Professor, Assoc Prof)
    department : str
        Academic department
    phone : str
        Phone number or campus extension
    availability : str, optional
        Initial availability (default: "Available")
    courses : list, optional
        List of course code strings (e.g. ["CS101", "CS202"])
    officeHours : str, optional
        Office hours string (e.g. "MWF 10-12")
    """

    def __init__(self, name: str, title: str, department: str, phone: str,
                 availability: str = "Available", courses: list = None, officeHours: str = ""):
        super().__init__(name, title, department, phone, availability)
        self._courses = courses if courses is not None else []
        self._officeHours = officeHours
        Log.i(f"Faculty: Initialized {name} with courses {self._courses} and office hours '{officeHours}'")

    def getCourses(self) -> list:
        """Return list of assigned courses."""
        return self._courses

    def getOfficeHours(self) -> str:
        """Return office hours description."""
        return self._officeHours

    def getDisplayLines(self) -> tuple:
        """
        Return multi-page LCD output showing courses, office hours, and contact.
        """
        status_abbr = self.getAvailability()[:4]
        line1 = _format_lcd_line(f"{self._name[:10]} [{status_abbr}]")

        courses_str = ", ".join(self._courses)
        page0 = (line1, _format_lcd_line(f"Courses: {courses_str}"))
        page1 = (line1, _format_lcd_line(f"OH: {self._officeHours}"))
        page2 = (line1, _format_lcd_line(f"Ph: {self._phoneNumber}"))
        return (page0, page1, page2)


class Staff(Employee):
    """
    Represents administrative staff members.
    """

    def __init__(self, name: str, title: str, department: str, phone: str, availability: str = "Available"):
        super().__init__(name, title, department, phone, availability)

    def getDepartment(self) -> str:
        """Return staff department."""
        return self._department

    def getDisplayLines(self) -> tuple:
        """Return LCD display pages for staff."""
        status_abbr = self.getAvailability()[:4]
        line1 = _format_lcd_line(f"{self._name[:10]} [{status_abbr}]")
        page0 = (line1, _format_lcd_line(self._title))
        page1 = (line1, _format_lcd_line(f"Dept: {self._department}"))
        page2 = (line1, _format_lcd_line(f"Ph: {self._phoneNumber}"))
        return (page0, page1, page2)


class Administrator(Employee):
    """
    Represents an administrator whose availability is automatically
    governed by a simulated Calendar schedule.

    Parameters:
    ----------
    calendar : Calendar, optional
        Calendar instance providing automated event schedules
    """

    def __init__(self, name: str, title: str, department: str, phone: str,
                 availability: str = "Available", calendar: Calendar = None):
        super().__init__(name, title, department, phone, availability)
        self._calendar = calendar
        Log.i(f"Administrator: Initialized {name} with calendar integration")

    def getAvailability(self) -> str:
        """Query availability from the linked Calendar."""
        if self._calendar is not None:
            return self._calendar.getCurrentStatus()
        return self._availability

    def automaticAvailability(self) -> str:
        """Synchronize and return the automated status."""
        self._availability = self.getAvailability()
        return self._availability

    def cycleAvailability(self) -> None:
        """
        Override: Availability for administrators is automatically determined
        by calendar schedule; manual cycling is disabled.
        """
        Log.i(f"Administrator {self._name}: Manual cycling disabled (Calendar managed: {self.getAvailability()})")

    def getDisplayLines(self) -> tuple:
        """Return LCD display pages including calendar schedule status."""
        current_status = self.getAvailability()
        status_abbr = current_status[:4]
        line1 = _format_lcd_line(f"{self._name[:10]} [{status_abbr}]")

        sim_time = self._calendar.getSimulatedTime() if self._calendar else "--:--"
        page0 = (line1, _format_lcd_line(self._title))
        page1 = (line1, _format_lcd_line(f"Dept: {self._department}"))
        page2 = (line1, _format_lcd_line(f"Ph: {self._phoneNumber}"))
        page3 = (line1, _format_lcd_line(f"Cal@{sim_time}: {current_status}"))
        return (page0, page1, page2, page3)


class StudentWorker(Employee):
    """
    Represents a student worker with specific scheduling and support roles.
    """

    def __init__(self, name: str, title: str, department: str, phone: str, availability: str = "Available"):
        super().__init__(name, title, department, phone, availability)

    def getAvailability(self) -> str:
        """Return student worker availability."""
        return self._availability

    def getDisplayLines(self) -> tuple:
        """Return LCD display pages for student worker."""
        status_abbr = self.getAvailability()[:4]
        line1 = _format_lcd_line(f"{self._name[:10]} [{status_abbr}]")
        page0 = (line1, _format_lcd_line(self._title))
        page1 = (line1, _format_lcd_line(f"Dept: {self._department}"))
        page2 = (line1, _format_lcd_line(f"Ph: {self._phoneNumber}"))
        return (page0, page1, page2)


if __name__ == "__main__":
    Log.i("--- Testing Employee Class Hierarchy ---")

    # 1. Test Base Employee
    emp = Employee("Test Person", "Role", "Dept", "555-0100")
    assert emp.getName() == "Test Person"
    assert emp.getPhoneNumber() == "555-0100"
    assert emp.getAvailability() == "Available"
    emp.cycleAvailability()
    assert emp.getAvailability() == "Away"
    emp.cycleAvailability()
    assert emp.getAvailability() == "Busy"
    emp.cycleAvailability()
    assert emp.getAvailability() == "Available"

    # 2. Test Faculty
    fac = Faculty("Dr. Smith", "Professor", "CS", "555-0101",
                  courses=["CS101", "CS202"], officeHours="MWF 10-12")
    assert fac.getCourses() == ["CS101", "CS202"]
    assert fac.getOfficeHours() == "MWF 10-12"
    pages = fac.getDisplayLines()
    assert len(pages) == 3
    assert len(pages[0][0]) == 16 and len(pages[0][1]) == 16
    Log.i(f"Faculty Page 0: '{pages[0][0]}' / '{pages[0][1]}'")
    Log.i(f"Faculty Page 1: '{pages[1][0]}' / '{pages[1][1]}'")
    Log.i(f"Faculty Page 2: '{pages[2][0]}' / '{pages[2][1]}'")

    # 3. Test Administrator with Calendar
    cal = Calendar(sim_start_hour=9, sec_per_sim_hour=10)
    cal.addEvent("Executive Meeting", "09:00", "10:30", "Busy")
    admin = Administrator("Dean Vance", "Dean", "Engineering", "555-0102", calendar=cal)
    assert admin.getAvailability() == "Busy"
    admin.cycleAvailability()
    assert admin.getAvailability() == "Busy"

    # 4. Test StudentWorker
    student = StudentWorker("Sam Jones", "Lab Assistant", "CS Lab", "555-0103")
    assert student.getName() == "Sam Jones"
    student_pages = student.getDisplayLines()
    assert len(student_pages) == 3

    Log.i("Testing complete - all Employee checks passed")
