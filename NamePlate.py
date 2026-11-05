"""
# NamePlate.py
# Application controller coordinating display, buttons, lights, buzzer, and employees
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
from Employee import Employee

try:
    sleep_ms = time.sleep_ms
except AttributeError:
    # Desktop Python fallback for local testing
    sleep_ms = lambda ms: time.sleep(ms / 1000)

# Availability Color Mapping (RGB tuples)
COLOR_AVAILABLE = (0, 255, 0)    # Green
COLOR_AWAY = (255, 200, 0)       # Yellow
COLOR_BUSY = (255, 0, 0)         # Red
COLOR_DEFAULT = (0, 0, 255)      # Blue (Fallback)


class NamePlate:
    """
    Central controller class for the Dynamic Office Nameplate System.
    Manages navigation, employee cycling, LCD pagination, acoustic feedback,
    and RGB status illumination.

    Parameters:
    ----------
    display : Display
        Display instance (e.g. LCDDisplay)
    buttons : list
        List of Button instances (expected names: 'prev', 'next', 'avail')
    lightStrip : LightStrip
        LightStrip instance for availability status indication
    buzzer : PassiveBuzzer
        PassiveBuzzer instance for acoustic feedback
    employees : list
        Initial list of Employee instances

    Examples:
    ---------
    1. np = NamePlate(display, [b_prev, b_next, b_avail], strip, buz, [emp1, emp2])
    """

    def __init__(self, display, buttons: list, lightStrip, buzzer, employees: list):
        self._display = display
        self._buttons = buttons if buttons is not None else []
        self._lightStrip = lightStrip
        self._buzzer = buzzer
        self._employees = employees if employees is not None else []
        self._currentIndex = 0
        self._pageIndex = 0

        Log.i(f"NamePlate: Initializing with {len(self._employees)} employees and {len(self._buttons)} buttons")

        # Register this controller as handler for all buttons
        for btn in self._buttons:
            if hasattr(btn, "setHandler"):
                btn.setHandler(self)
                Log.i(f"NamePlate: Registered as handler for button {getattr(btn, '_name', 'unknown')}")

        # Render initial state
        self.updateDisplay()
        self.updateStatusLight()

    def addEmployee(self, employee: Employee) -> None:
        """
        Add a new employee to the roster.

        Parameters:
        ----------
        employee : Employee
            Employee instance to append to the system
        """
        if isinstance(employee, Employee):
            self._employees.append(employee)
            Log.i(f"NamePlate: Added employee {employee.getName()} (Total: {len(self._employees)})")
        else:
            Log.w("NamePlate: Attempted to add invalid employee object")

    def nextEmployee(self) -> None:
        """
        Advance to the next employee in the list (with circular wrap-around).
        Plays navigation chirp, resets page index, and refreshes hardware.
        """
        if not self._employees:
            return
        self._currentIndex = (self._currentIndex + 1) % len(self._employees)
        self._pageIndex = 0
        Log.i(f"NamePlate: Next employee -> index {self._currentIndex} ({self._employees[self._currentIndex].getName()})")
        self.playTone(523, 70)  # C5 tone for Next
        self.updateStatusLight()
        self.updateDisplay()

    def previousEmployee(self) -> None:
        """
        Navigate to the previous employee in the list (with circular wrap-around).
        Plays navigation chirp, resets page index, and refreshes hardware.
        """
        if not self._employees:
            return
        self._currentIndex = (self._currentIndex - 1) % len(self._employees)
        self._pageIndex = 0
        Log.i(f"NamePlate: Previous employee -> index {self._currentIndex} ({self._employees[self._currentIndex].getName()})")
        self.playTone(440, 70)  # A4 tone for Prev
        self.updateStatusLight()
        self.updateDisplay()

    def cycleAvailability(self) -> None:
        """
        Cycle the availability of the currently displayed employee.
        Emits acoustic confirmation and updates status light and LCD.
        """
        if not self._employees:
            return
        current_emp = self._employees[self._currentIndex]
        current_emp.cycleAvailability()
        Log.i(f"NamePlate: Cycled availability for {current_emp.getName()} -> {current_emp.getAvailability()}")
        self.playTone(659, 80)  # E5 tone for Availability toggle
        self.updateStatusLight()
        self.updateDisplay()

    def updateDisplay(self, nextPage: bool = False) -> None:
        """
        Update the 16x2 LCD display with current employee information.

        Parameters:
        ----------
        nextPage : bool, optional
            If True, advances to the next multi-page info screen (default: False).
        """
        if not self._employees or self._display is None:
            return

        current_emp = self._employees[self._currentIndex]
        pages = current_emp.getDisplayLines()

        if not pages:
            return

        if nextPage:
            self._pageIndex = (self._pageIndex + 1) % len(pages)
        else:
            self._pageIndex = self._pageIndex % len(pages)

        line1, line2 = pages[self._pageIndex]

        # Write lines to row 0 and row 1 of LCD (formatted to 16 chars)
        if hasattr(self._display, "showText"):
            self._display.showText((str(line1) + (" " * 16))[:16], row=0, col=0)
            self._display.showText((str(line2) + (" " * 16))[:16], row=1, col=0)
        Log.i(f"NamePlate Display [Page {self._pageIndex+1}/{len(pages)}]: '{line1}' | '{line2}'")

    def updateStatusLight(self) -> None:
        """
        Update the LightStrip RGB color according to current availability:
        - Green for Available
        - Yellow for Away
        - Red for Busy
        """
        if not self._employees or self._lightStrip is None:
            return

        current_emp = self._employees[self._currentIndex]
        avail = current_emp.getAvailability().lower()

        if "avail" in avail:
            color = COLOR_AVAILABLE
            color_name = "Green (Available)"
        elif "away" in avail:
            color = COLOR_AWAY
            color_name = "Yellow (Away)"
        elif "busy" in avail:
            color = COLOR_BUSY
            color_name = "Red (Busy)"
        else:
            color = COLOR_DEFAULT
            color_name = "Blue (Unknown)"

        if hasattr(self._lightStrip, "setColor"):
            self._lightStrip.setColor(color)
        if hasattr(self._lightStrip, "show"):
            self._lightStrip.show()
        Log.i(f"NamePlate Light: Set status light to {color_name}")

    def playTone(self, frequency: int, durationMs: int) -> None:
        """
        Play an acoustic feedback tone on the buzzer.

        Parameters:
        ----------
        frequency : int
            Frequency of the tone in Hertz
        durationMs : int
            Duration of the tone in milliseconds
        """
        if self._buzzer is None:
            return

        try:
            if hasattr(self._buzzer, "play") and hasattr(self._buzzer, "stop"):
                self._buzzer.play(frequency)
                sleep_ms(durationMs)
                self._buzzer.stop()
            elif hasattr(self._buzzer, "beep"):
                self._buzzer.beep(frequency, durationMs)
        except Exception as e:
            Log.w(f"NamePlate: Error playing tone ({e})")

    def buttonPressed(self, name: str) -> None:
        """
        Callback invoked by Button instances on press.
        Routes button actions based on button name.

        Parameters:
        ----------
        name : str
            Identifies the button ('prev', 'next', or 'avail')
        """
        Log.i(f"NamePlate: Button pressed -> '{name}'")
        if name == "prev":
            self.previousEmployee()
        elif name == "next":
            self.nextEmployee()
        elif name == "avail" or name == "status":
            self.cycleAvailability()
        else:
            Log.w(f"NamePlate: Unrecognized button name '{name}'")

    def buttonReleased(self, name: str) -> None:
        """
        Callback invoked by Button instances on release.
        """
        Log.i(f"NamePlate: Button released -> '{name}'")


if __name__ == "__main__":
    Log.i("--- Testing NamePlate Class ---")

    # Mock hardware drivers for testing without physical Pico attached
    class MockDisplay:
        def __init__(self):
            self.lines = ["", ""]
        def showText(self, text, row=0, col=0):
            self.lines[row] = text
        def clear(self):
            self.lines = ["", ""]

    class MockLightStrip:
        def __init__(self):
            self.color = None
        def setColor(self, color):
            self.color = color
        def show(self):
            pass

    class MockBuzzer:
        def __init__(self):
            self.last_tone = None
        def play(self, tone):
            self.last_tone = tone
        def stop(self):
            pass

    class MockButton:
        def __init__(self, name):
            self._name = name
            self._handler = None
        def setHandler(self, handler):
            self._handler = handler
        def press(self):
            if self._handler:
                self._handler.buttonPressed(self._name)

    mock_disp = MockDisplay()
    mock_led = MockLightStrip()
    mock_buz = MockBuzzer()
    btn_prev = MockButton("prev")
    btn_next = MockButton("next")
    btn_avail = MockButton("avail")

    e1 = Employee("Alice", "Staff", "IT", "555-0101", "Available")
    e2 = Employee("Bob", "Faculty", "CS", "555-0102", "Busy")

    np = NamePlate(mock_disp, [btn_prev, btn_next, btn_avail], mock_led, mock_buz, [e1, e2])

    assert np._currentIndex == 0
    assert mock_led.color == COLOR_AVAILABLE

    # Test Next Button
    btn_next.press()
    assert np._currentIndex == 1
    assert mock_led.color == COLOR_BUSY
    assert mock_buz.last_tone == 523

    # Test Prev Button
    btn_prev.press()
    assert np._currentIndex == 0
    assert mock_led.color == COLOR_AVAILABLE

    # Test Availability Button
    btn_avail.press()
    assert e1.getAvailability() == "Away"
    assert mock_led.color == COLOR_AWAY

    # Test Pagination
    np.updateDisplay(nextPage=True)
    assert np._pageIndex == 1

    Log.i("Testing complete - all NamePlate checks passed")
