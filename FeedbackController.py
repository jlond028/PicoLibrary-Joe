"""
# FeedbackController.py
# State-driven controller for the Store Feedback System using PicoLibrary components
# Author: insert your name here
"""

import time
from Log import *
from FeedbackStats import FeedbackStats


class FeedbackController:
    """
    Main controller class for the **Store Feedback System** on Raspberry Pi Pico.
    Coordinates `StateModel`, `FeedbackStats`, `LCDDisplay`, `LightStrip`,
    `PassiveBuzzer`, `UltrasonicSensor`, `Button`, and `SoftwareTimer`.

    Implements the 5-state feedback workflow:
    - **State 0 (`Welcome`)**: Displays `"Welcome to Ikea"` and colors the ring `LightStrip` (**Green**, **Yellow**, or **Red**).
    - **State 1 (`Selection`)**: Triggered by `uss_trip`; displays `"How was your visit?"` and starts a 5-second timer.
    - **State 2 (`Happy`)**: Triggered by `green_press`; increments happy count, updates ring color, displays `"Thank you"`, plays happy music, and starts a 5-second timer.
    - **State 3 (`Unhappy`)**: Triggered by `red_press`; increments unhappy count, updates ring color, displays `"Sorry to hear that"`, plays a sad tone, and waits 5 seconds before either returning to **State 0** (`timer_timeout`) or transitioning to **State 4** (`feedback_below_threshold` when total responses >= 5 and happy percentage < 30%).
    - **State 4 (`Alarm`)**: Displays `"Calling manager"`, plays a 2-tone alarm in `stateDo`, and resets stats when exited via `green_press`.

    Parameters:
    ----------
    sda : int, optional
        I2C SDA GPIO pin for the `LCDDisplay` (default: 0)
    scl : int, optional
        I2C SCL GPIO pin for the `LCDDisplay` (default: 1)
    light_pin : int, optional
        GPIO pin for the NeoPixel `LightStrip` ring (default: 2)
    numleds : int, optional
        Number of LEDs in the NeoPixel ring (default: 16)
    trig_pin : int, optional
        GPIO trigger pin for the `UltrasonicSensor` (default: 3)
    echo_pin : int, optional
        GPIO echo pin for the `UltrasonicSensor` (default: 4)
    green_pin : int, optional
        GPIO pin for the green (Happy / Reset) `Button` (default: 14)
    red_pin : int, optional
        GPIO pin for the red (Unhappy) `Button` (default: 15)
    buzzer_pin : int, optional
        GPIO pin for the `PassiveBuzzer` (default: 16)
    timeout_sec : int, optional
        Display timeout duration in seconds for States 1, 2, and 3 (default: 5)

    Examples:
    ---------
    1. Instantiate with default Wokwi pins and start the state model:
       `controller = FeedbackController()`
       `controller.run()`
    2. Stop the controller cleanly on shutdown:
       `controller.stop()`
    """

    # State constants matching the State Model Diagram
    STATE_WELCOME = 0
    STATE_SELECTION = 1
    STATE_HAPPY = 2
    STATE_UNHAPPY = 3
    STATE_ALARM = 4

    def __init__(
        self,
        sda=0,
        scl=1,
        light_pin=2,
        numleds=8,
        trig_pin=3,
        echo_pin=4,
        green_pin=14,
        red_pin=15,
        buzzer_pin=16,
        timeout_sec=5,
        display=None,
        lightstrip=None,
        buzzer=None,
        uss=None,
        green_btn=None,
        red_btn=None,
        timer=None,
        stats=None
    ):
        """
        Initialize the `FeedbackController`, hardware peripherals, and `StateModel`.

        Parameters:
        ----------
        sda : int, optional
            I2C SDA pin for LCDDisplay (default: 0)
        scl : int, optional
            I2C SCL pin for LCDDisplay (default: 1)
        light_pin : int, optional
            GPIO pin for LightStrip (default: 2)
        numleds : int, optional
            Number of NeoPixels on the ring (default: 16)
        trig_pin : int, optional
            Trigger GPIO pin for UltrasonicSensor (default: 3)
        echo_pin : int, optional
            Echo GPIO pin for UltrasonicSensor (default: 4)
        green_pin : int, optional
            GPIO pin for the green button (default: 14)
        red_pin : int, optional
            GPIO pin for the red button (default: 15)
        buzzer_pin : int, optional
            GPIO pin for the passive buzzer (default: 16)
        timeout_sec : int, optional
            Timeout in seconds for selection and thank-you screens (default: 5)

        Examples:
        ---------
        1. `controller = FeedbackController()`
        2. `controller = FeedbackController(timeout_sec=5)`
        """
        Log.i("FeedbackController: Initializing components...")

        self._timeout_sec = timeout_sec
        self._below_threshold_pending = False
        self._state3_start_ms = 0
        self._alarm_toggle = False

        # 1. Business logic model (FeedbackStats)
        self._stats = stats if stats is not None else FeedbackStats(threshold=30.0, min_responses=5)

        # 2. Hardware peripherals (lazy-imported from PicoLibrary unless injected)
        if display is None:
            from Displays import LCDDisplay
            self._display = LCDDisplay(sda=sda, scl=scl)
        else:
            self._display = display

        if lightstrip is None:
            from LightStrip import LightStrip
            self._lightstrip = LightStrip(pin=light_pin, name="FeedbackRing", numleds=numleds, brightness=0.5)
        else:
            self._lightstrip = lightstrip

        if buzzer is None:
            from Buzzer import PassiveBuzzer
            self._buzzer = PassiveBuzzer(pin=buzzer_pin, name="FeedbackBuzzer")
        else:
            self._buzzer = buzzer

        if uss is None:
            from Sensors_advanced import UltrasonicSensor

            class _SafeUltrasonicSensor(UltrasonicSensor):
                def tripped(self):
                    v = self.rawValue()
                    if v <= 0:
                        return False
                    return super().tripped()

            self._uss = _SafeUltrasonicSensor(trigger=trig_pin, echo=echo_pin, name="uss", lowActive=True, threshold=20.0)
        else:
            self._uss = uss

        if green_btn is None:
            from Button import Button
            self._green_btn = Button(green_pin, "green", handler=None, lowActive=True)
        else:
            self._green_btn = green_btn

        if red_btn is None:
            from Button import Button
            self._red_btn = Button(red_pin, "red", handler=None, lowActive=True)
        else:
            self._red_btn = red_btn

        if timer is None:
            from Counters import SoftwareTimer
            self._timer = SoftwareTimer(name="timer", handler=None)
        else:
            self._timer = timer

        # 3. StateModel configuration (5 states: 0..4)
        from StateModel import StateModel
        self._model = StateModel(5, self, debug=True)

        # Register input devices, software timer, and custom event
        self._model.addSensor(self._uss)
        self._model.addButton(self._green_btn)
        self._model.addButton(self._red_btn)
        self._model.addTimer(self._timer)
        self._model.addCustomEvent("feedback_below_threshold")

        # 4. State Transitions matching the State Model Diagram
        self._model.addTransition(self.STATE_WELCOME, ["uss_trip"], self.STATE_SELECTION)
        self._model.addTransition(self.STATE_SELECTION, ["timer_timeout"], self.STATE_WELCOME)
        self._model.addTransition(self.STATE_SELECTION, ["green_press"], self.STATE_HAPPY)
        self._model.addTransition(self.STATE_SELECTION, ["red_press"], self.STATE_UNHAPPY)
        self._model.addTransition(self.STATE_HAPPY, ["timer_timeout"], self.STATE_WELCOME)
        self._model.addTransition(self.STATE_UNHAPPY, ["timer_timeout"], self.STATE_WELCOME)
        self._model.addTransition(self.STATE_UNHAPPY, ["feedback_below_threshold"], self.STATE_ALARM)
        self._model.addTransition(self.STATE_ALARM, ["green_press"], self.STATE_WELCOME)

        Log.i("FeedbackController: Initialization complete")

    def _ticks_ms(self):
        """Return current monotonic millisecond tick count (MicroPython & Desktop safe)."""
        if hasattr(time, "ticks_ms"):
            return time.ticks_ms()
        return int(time.time() * 1000)

    def _ticks_diff(self, end_ms, start_ms):
        """Return elapsed milliseconds between two tick counts."""
        if hasattr(time, "ticks_diff"):
            return time.ticks_diff(end_ms, start_ms)
        return end_ms - start_ms

    def update_lights(self):
        """
        Update the NeoPixel ring `LightStrip` to **Green**, **Yellow**, or **Red**
        based on `FeedbackStats.get_light_level()`.

        Parameters:
        ----------
        None

        Examples:
        ---------
        1. `controller.update_lights()`
        2. `controller._stats.add_happy(); controller.update_lights()`
        """
        color = self._stats.get_light_level()
        pct = self._stats.calculate_percentage()
        Log.i(f"FeedbackController: Updating LightStrip color to {color} (happiness={pct:.1f}%)")
        self._lightstrip.setColor(color)

    def play_happy_music(self):
        """
        Play a short upbeat ascending melody (`C4 -> E4 -> G4`) on the `PassiveBuzzer`.

        Parameters:
        ----------
        None

        Examples:
        ---------
        1. `controller.play_happy_music()`
        2. `if state == 2: controller.play_happy_music()`
        """
        Log.i("FeedbackController: Playing happy music")
        for tone in (262, 330, 392):
            self._buzzer.beep(tone=tone, duration=120)

    def play_sad_tone(self):
        """
        Play a descending sad tone (`E4 -> C4`) on the `PassiveBuzzer`.

        Parameters:
        ----------
        None

        Examples:
        ---------
        1. `controller.play_sad_tone()`
        2. `if state == 3: controller.play_sad_tone()`
        """
        Log.i("FeedbackController: Playing sad tone")
        self._buzzer.beep(tone=330, duration=200)
        self._buzzer.beep(tone=262, duration=300)

    def stateEntered(self, state, event):
        """
        Perform entry actions when entering `state` triggered by `event`.

        Parameters:
        ----------
        state : int
            The state number being entered (`0` through `4`)
        event : str
            The event name that caused the transition

        Examples:
        ---------
        1. `controller.stateEntered(0, "no_event")`
        2. `controller.stateEntered(1, "uss_trip")`
        """
        Log.i(f"FeedbackController: Entering State {state} on event '{event}'")

        if state == self.STATE_WELCOME:
            self._display.clear()
            self._display.showText("Welcome to", 0, 0)
            self._display.showText("Ikea", 1, 0)
            self.update_lights()

        elif state == self.STATE_SELECTION:
            self._display.clear()
            self._display.showText("How was your", 0, 0)
            self._display.showText("visit?", 1, 0)
            self._timer.start(self._timeout_sec)

        elif state == self.STATE_HAPPY:
            self._stats.add_happy()
            self.update_lights()
            self._display.clear()
            self._display.showText("Thank you", 0, 0)
            self.play_happy_music()
            self._timer.start(self._timeout_sec)

        elif state == self.STATE_UNHAPPY:
            self._stats.add_unhappy()
            self.update_lights()
            self._display.clear()
            self._display.showText("Sorry to hear", 0, 0)
            self._display.showText("that", 1, 0)
            self.play_sad_tone()

            # Wait the full 5-second display duration before transitioning:
            # - If below threshold (<30% with >=5 responses), stateDo(3) will trigger
            #   'feedback_below_threshold' after 5 seconds.
            # - Otherwise, the 5-second timer will fire 'timer_timeout' -> State 0.
            if self._stats.is_below_threshold():
                self._below_threshold_pending = True
                self._state3_start_ms = self._ticks_ms()
                total = self._stats.get_total_count()
                Log.i(f"FeedbackController: Below 30% threshold after {total} responses; transitioning to Alarm after {self._timeout_sec}s")
            else:
                self._below_threshold_pending = False
                self._timer.start(self._timeout_sec)

        elif state == self.STATE_ALARM:
            self._display.clear()
            self._display.showText("Calling", 0, 0)
            self._display.showText("manager", 1, 0)
            self._alarm_toggle = False

    def stateLeft(self, state, event):
        """
        Perform exit actions when leaving `state` on `event`.

        Parameters:
        ----------
        state : int
            The state number being exited (`0` through `4`)
        event : str
            The event name causing the transition

        Examples:
        ---------
        1. `controller.stateLeft(1, "green_press")`
        2. `controller.stateLeft(4, "green_press")`
        """
        Log.i(f"FeedbackController: Leaving State {state} on event '{event}'")

        if state in (self.STATE_SELECTION, self.STATE_HAPPY, self.STATE_UNHAPPY):
            self._timer.cancel()
            self._below_threshold_pending = False

        elif state == self.STATE_ALARM:
            self._buzzer.stop()
            self._stats.reset()
            self.update_lights()

    def stateDo(self, state):
        """
        Perform continuous in-state activities for `state` on each iteration of `StateModel.run()`.

        Parameters:
        ----------
        state : int
            The currently active state (`0` through `4`)

        Examples:
        ---------
        1. `controller.stateDo(3)`
        2. `controller.stateDo(4)`
        """
        if state == self.STATE_UNHAPPY:
            if self._below_threshold_pending:
                elapsed_ms = self._ticks_diff(self._ticks_ms(), self._state3_start_ms)
                if elapsed_ms >= int(self._timeout_sec * 1000):
                    self._below_threshold_pending = False
                    self._model.processEvent("feedback_below_threshold")

        elif state == self.STATE_ALARM:
            # Play a 2-tone manager alarm and alternate the ring Red / Off
            self._alarm_toggle = not self._alarm_toggle
            if self._alarm_toggle:
                self._lightstrip.setColor((255, 0, 0))
                self._buzzer.beep(tone=880, duration=150)
            else:
                self._lightstrip.off()
                self._buzzer.beep(tone=587, duration=150)

    def stateEvent(self, state, event):
        """
        Handle in-state events that do not cause a state transition.

        Parameters:
        ----------
        state : int
            Current state number
        event : str
            Event name received

        Examples:
        ---------
        1. `handled = controller.stateEvent(0, "green_press")`
        2. `handled = controller.stateEvent(1, "uss_untrip")`
        """
        return False

    def run(self):
        """
        Start and run the `StateModel` event loop.

        Parameters:
        ----------
        None

        Examples:
        ---------
        1. `controller.run()`
        2. `try: controller.run()\nexcept KeyboardInterrupt: controller.stop()`
        """
        Log.i("FeedbackController: Starting StateModel run loop")
        self._model.run(delay=0.1)

    def stop(self):
        """
        Stop the `StateModel` and clean up display, lightstrip, and buzzer outputs.

        Parameters:
        ----------
        None

        Examples:
        ---------
        1. `controller.stop()`
        2. `controller.stop(); Log.i("Stopped")`
        """
        Log.i("FeedbackController: Stopping StateModel and cleaning up hardware")
        self._model.stop()
        self._buzzer.stop()
        self._lightstrip.off()
        self._display.clear()


if __name__ == "__main__":
    Log.i("Starting FeedbackController on Pico...")
    p = FeedbackController()
    try:
        p.run()
    except KeyboardInterrupt:
        p.stop()
        Log.i("Testing complete - FeedbackController stopped cleanly")
