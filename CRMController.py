"""
# CRMController.py
# MVC Controller for the IoT CRM Machine on Raspberry Pi Pico 2W
# Supports both Option A (eager load) and Option B (lazy load on demand)
# Author: Joseph Londono
"""

import gc
import time
from Log import *
from Customer import Customer
from Contact import Contact
from Activity import Activity


# Fallback RGB color tuples in case Lights is not imported yet
COLOR_OFF = (0, 0, 0)
COLOR_RED = (255, 0, 0)
COLOR_YELLOW = (255, 200, 0)
COLOR_GREEN = (0, 255, 0)
COLOR_BLUE = (0, 0, 255)


class CRMController:
    """
    Main controller for the IoT CRM Machine.
    Connects to Wi-Fi, retrieves Customer/Contact/Activity records from the
    Oracle ORDS REST API, and drives the 16x2 LCDDisplay, Buttons, LightStrip,
    and PassiveBuzzer.

    Parameters:
    ----------
    ssid : str
        Wi-Fi network SSID
    password : str
        Wi-Fi network password
    baseURL : str, optional
        Base URL of the CRM REST API (default: ism6106 Oracle ORDS endpoint)
    eagerLoad : bool, optional
        False = Option B (lazy load on select), True = Option A (eager load all at startup)
    sda : int, optional
        I2C SDA pin for 16x2 LCD (default: 0)
    scl : int, optional
        I2C SCL pin for 16x2 LCD (default: 1)
    light_pin : int, optional
        GPIO pin for NeoPixel LightStrip (default: 2)
    numleds : int, optional
        Number of LEDs on the LightStrip (default: 8)
    next_pin : int, optional
        GPIO pin for the Next button (default: 14)
    select_pin : int, optional
        GPIO pin for the Select button (default: 15)
    buzzer_pin : int, optional
        GPIO pin for the PassiveBuzzer (default: 16)

    Examples:
    ---------
    1. ctrl = CRMController(ssid="MyHotspot", password="secret")
    2. ctrl.run()
    """

    MODE_CUSTOMERS = "CUSTOMERS"
    MODE_CONTACTS = "CONTACTS"
    MODE_ACTIVITIES = "ACTIVITIES"

    def __init__(
        self,
        ssid,
        password,
        baseURL="https://iacademy.oracle.com/ords/ism6106/customer",
        eagerLoad=False,
        sda=0,
        scl=1,
        light_pin=2,
        numleds=8,
        next_pin=14,
        select_pin=15,
        buzzer_pin=16,
        *,
        net=None,
        display=None,
        strip=None,
        buzzer=None,
        btnNext=None,
        btnSelect=None,
    ):
        """
        Initialize the CRMController and its hardware / network components.
        Optional injected components (net, display, strip, buzzer, btnNext, btnSelect)
        allow unit testing without physical hardware.
        """
        self._ssid = ssid
        self._password = password
        self.baseURL = baseURL.rstrip("/")
        self._eagerLoad = eagerLoad

        self.customers = []
        self.currentCustIndex = 0
        self.currentSubIndex = 0
        self.mode = self.MODE_CUSTOMERS

        self._numleds = numleds
        self._pendingButton = None
        self._running = False

        # Lazy-import hardware/network classes so module can be imported off-device
        if net is not None:
            self._net = net
        else:
            from Net import Net
            self._net = Net()

        if display is not None:
            self._display = display
        else:
            from Displays import LCDDisplay
            self._display = LCDDisplay(sda=sda, scl=scl)

        if strip is not None:
            self._strip = strip
        else:
            from LightStrip import LightStrip
            self._strip = LightStrip(pin=light_pin, name="CRMStrip", numleds=numleds)

        if buzzer is not None:
            self._buzzer = buzzer
        else:
            from Buzzer import PassiveBuzzer
            self._buzzer = PassiveBuzzer(pin=buzzer_pin, name="CRMBuzzer")

        if btnNext is not None:
            self._btnNext = btnNext
        else:
            from Button import Button
            self._btnNext = Button(next_pin, "Next", handler=self)

        if btnSelect is not None:
            self._btnSelect = btnSelect
        else:
            from Button import Button
            self._btnSelect = Button(select_pin, "Select", handler=self)

        Log.i("CRMController: initialized")

    def _showLCD(self, line0, line1=""):
        """
        Display two padded 16-character lines cleanly on the 16x2 LCD.
        """
        l0 = str(line0)[:16]
        l1 = str(line1)[:16]
        l0 = l0 + (" " * (16 - len(l0)))
        l1 = l1 + (" " * (16 - len(l1)))
        self._display.showText(l0, 0, 0)
        self._display.showText(l1, 1, 0)

    def _showLoadingAnimation(self, step=0):
        """
        Display a blue loading sweep on the LightStrip while fetching from the API.
        """
        try:
            self._strip.setColor(COLOR_BLUE, (step % self._numleds) + 1)
        except Exception as e:
            Log.e(f"CRMController: LightStrip animation error: {e}")

    def start(self):
        """
        Connect to Wi-Fi, verify API version, load customers (and all details if Option A),
        and display the first customer on the LCD.

        Examples:
        ---------
        1. controller.start()
        """
        Log.i("CRMController: start()")
        self._showLCD("Connecting WiFi", self._ssid)
        self._showLoadingAnimation(2)

        self._net.connect(self._ssid, self._password)
        ip = self._net.getLocalIp()
        Log.i(f"CRMController: connected with IP {ip}")
        self._showLCD("WiFi Connected!", ip)
        self._showLoadingAnimation(4)

        version = self.checkApiVersion()
        self._buzzer.beep(800, 150)
        self._showLCD("API Ready", f"Version: {version}")
        time.sleep(0.8)

        self._showLCD("Loading Clients", "Please wait...")
        self._showLoadingAnimation(6)
        self.loadAllCustomers()

        if self._eagerLoad:
            Log.i("CRMController: Option A (Eager Load) enabled - loading all details")
            self.loadAllDetails()
        else:
            Log.i("CRMController: Option B (Lazy Load) enabled - details load on select")

        self._strip.off()
        self.mode = self.MODE_CUSTOMERS
        self.currentCustIndex = 0
        self.currentSubIndex = 0
        self.updateDisplay()
        Log.i("CRMController: startup complete - ready for user input")

    def checkApiVersion(self):
        """
        Call the /version REST endpoint to verify API connectivity.

        Examples:
        ---------
        1. ver = controller.checkApiVersion()
        """
        url = f"{self.baseURL}/version"
        Log.i(f"CRMController: checkApiVersion() -> GET {url}")
        gc.collect()
        data = self._net.getJson(url)
        if data and "version" in data:
            ver = data["version"]
            Log.i(f"CRMController: API version = {ver}")
            return ver
        Log.e("CRMController: failed to retrieve API version")
        return "Unknown"

    def loadAllCustomers(self):
        """
        Retrieve all customers from /get_customers (following ORDS pagination if hasMore is True)
        and instantiate Customer model objects.

        Examples:
        ---------
        1. controller.loadAllCustomers()
        """
        self.customers = []
        url = f"{self.baseURL}/get_customers"
        page = 0

        while url:
            page += 1
            Log.i(f"CRMController: loadAllCustomers() page {page} -> GET {url}")
            gc.collect()
            data = self._net.getJson(url)
            if not data or "items" not in data:
                Log.e("CRMController: no customer items returned")
                break

            for item in data["items"]:
                cust = Customer(
                    id=item.get("id"),
                    customer_name=item.get("customer_name"),
                    category=item.get("category"),
                    category_description=item.get("category_description"),
                    geography_name=item.get("geography_name"),
                    cust_type=item.get("type"),
                )
                self.customers.append(cust)

            # Follow ORDS "next" link if there are more than 25 customers
            next_url = None
            if data.get("hasMore"):
                for link in data.get("links", []):
                    if link.get("rel") == "next":
                        next_url = link.get("href")
                        break
            url = next_url

        Log.i(f"CRMController: loaded {len(self.customers)} customers")

    def loadAllDetails(self):
        """
        Option A (Eager Load): Loop through every customer and fetch all contacts
        and activities upfront during startup.

        Examples:
        ---------
        1. controller.loadAllDetails()
        """
        Log.i(f"CRMController: loadAllDetails() for {len(self.customers)} customers")
        for idx, customer in enumerate(self.customers):
            self._showLCD("Loading All...", f"{idx + 1}/{len(self.customers)}")
            self._showLoadingAnimation(idx)
            self.loadCustomerDetails(customer)
        Log.i("CRMController: loadAllDetails() finished")

    def loadCustomerDetails(self, customer):
        """
        Option B (Lazy Load): Fetch contacts and activities for a single Customer
        from /get_contacts/:cust_id and /get_activities/:cust_id.

        Parameters:
        ----------
        customer : Customer
            The Customer object whose contacts and activities will be populated

        Examples:
        ---------
        1. controller.loadCustomerDetails(customer)
        """
        Log.i(f"CRMController: loadCustomerDetails('{customer.customer_name}')")
        self._showLCD("Loading Details", customer.customer_name)
        self._showLoadingAnimation(3)

        # Fetch contacts
        contacts_url = f"{self.baseURL}/get_contacts/{customer.id}"
        Log.i(f"CRMController: GET {contacts_url}")
        gc.collect()
        c_data = self._net.getJson(contacts_url)
        if c_data and "items" in c_data:
            for item in c_data["items"]:
                contact = Contact(
                    id=item.get("id"),
                    name=item.get("name"),
                    title=item.get("title"),
                    company=item.get("company"),
                    phone=item.get("phone"),
                    contact_type=item.get("contact_type"),
                )
                customer.addContact(contact)
        else:
            Log.i(f"CRMController: no contacts found for '{customer.customer_name}'")

        self._showLoadingAnimation(6)

        # Fetch activities
        activities_url = f"{self.baseURL}/get_activities/{customer.id}"
        Log.i(f"CRMController: GET {activities_url}")
        gc.collect()
        a_data = self._net.getJson(activities_url)
        if a_data and "items" in a_data:
            for item in a_data["items"]:
                activity = Activity(
                    id=item.get("id"),
                    activity_type=item.get("activity_type"),
                    name=item.get("name"),
                    description=item.get("description"),
                    activity_date=item.get("activity_date"),
                    owner=item.get("owner"),
                    location=item.get("location"),
                )
                customer.addActivity(activity)
        else:
            Log.i(f"CRMController: no activities found for '{customer.customer_name}'")

        customer.setDetailsLoaded(True)
        Log.i(
            f"CRMController: details loaded for '{customer.customer_name}' "
            f"(contacts={len(customer.getContacts())}, activities={customer.getActivityCount()})"
        )

    def buttonPressed(self, name):
        """
        IRQ callback invoked by Button when a button is pressed.
        Queues the button name so network/LCD work runs safely on the main loop.

        Parameters:
        ----------
        name : str
            Name of the button pressed ("Next" or "Select")
        """
        Log.i(f"CRMController: buttonPressed('{name}')")
        self._pendingButton = name

    def buttonReleased(self, name):
        """
        IRQ callback invoked by Button when a button is released.

        Parameters:
        ----------
        name : str
            Name of the button released
        """
        Log.i(f"CRMController: buttonReleased('{name}')")

    def nextItem(self):
        """
        Advance to the next Customer, Contact, or Activity depending on the current mode.

        Examples:
        ---------
        1. controller.nextItem()
        """
        if not self.customers:
            return

        self._buzzer.beep(400, 50)

        if self.mode == self.MODE_CUSTOMERS:
            self.currentCustIndex = (self.currentCustIndex + 1) % len(self.customers)
            cust = self.customers[self.currentCustIndex]
            Log.i(f"CRMController: nextItem() -> Customer #{self.currentCustIndex + 1}: {cust.customer_name}")
            if cust.hasDetailsLoaded():
                self.updateStatusIndicators(cust, playSound=False)
            else:
                self._strip.off()

        elif self.mode == self.MODE_CONTACTS:
            contacts = self.customers[self.currentCustIndex].getContacts()
            if contacts:
                self.currentSubIndex = (self.currentSubIndex + 1) % len(contacts)
                Log.i(f"CRMController: nextItem() -> Contact {self.currentSubIndex + 1}/{len(contacts)}")

        elif self.mode == self.MODE_ACTIVITIES:
            activities = self.customers[self.currentCustIndex].getActivities()
            if activities:
                self.currentSubIndex = (self.currentSubIndex + 1) % len(activities)
                Log.i(f"CRMController: nextItem() -> Activity {self.currentSubIndex + 1}/{len(activities)}")

        self.updateDisplay()

    def selectItem(self):
        """
        Select the current item:
        - In CUSTOMERS mode: lazy-load details if needed, update LightStrip/Buzzer, view CONTACTS
        - In CONTACTS mode: switch to ACTIVITIES for this customer
        - In ACTIVITIES mode: call goBack() to return to CUSTOMERS

        Examples:
        ---------
        1. controller.selectItem()
        """
        if not self.customers:
            return

        cust = self.customers[self.currentCustIndex]

        if self.mode == self.MODE_CUSTOMERS:
            Log.i(f"CRMController: selectItem() -> Customer '{cust.customer_name}'")
            if not cust.hasDetailsLoaded():
                self.loadCustomerDetails(cust)
            else:
                Log.i(f"CRMController: using cached details for '{cust.customer_name}'")

            self.updateStatusIndicators(cust, playSound=True)
            self.mode = self.MODE_CONTACTS
            self.currentSubIndex = 0
            self.updateDisplay()

        elif self.mode == self.MODE_CONTACTS:
            Log.i(f"CRMController: selectItem() -> switching to ACTIVITIES for '{cust.customer_name}'")
            self._buzzer.beep(600, 80)
            self.mode = self.MODE_ACTIVITIES
            self.currentSubIndex = 0
            self.updateDisplay()

        elif self.mode == self.MODE_ACTIVITIES:
            self.goBack()

    def goBack(self):
        """
        Return from sub-views (CONTACTS or ACTIVITIES) back to the CUSTOMERS list.

        Examples:
        ---------
        1. controller.goBack()
        """
        Log.i("CRMController: goBack() -> returning to CUSTOMERS mode")
        self._buzzer.beep(350, 80)
        self.mode = self.MODE_CUSTOMERS
        self.currentSubIndex = 0
        self._strip.off()
        self.updateDisplay()

    def updateStatusIndicators(self, customer, playSound=True):
        """
        Update the LightStrip color and PassiveBuzzer cue based on the customer's activity count:
        - 0 activities: RED + alert tone
        - 1-2 activities: YELLOW + select chime
        - 3+ activities: GREEN + success chime

        Parameters:
        ----------
        customer : Customer
            The selected Customer object
        playSound : bool, optional
            Whether to play the buzzer audio cue (default: True)

        Examples:
        ---------
        1. controller.updateStatusIndicators(customer)
        """
        count = customer.getActivityCount()
        if count == 0:
            Log.i(f"CRMController: '{customer.customer_name}' has 0 activities -> LightStrip RED")
            self._strip.setColor(COLOR_RED)
            if playSound:
                self._buzzer.beep(220, 200)
                self._buzzer.beep(180, 250)
        elif count <= 2:
            Log.i(f"CRMController: '{customer.customer_name}' has {count} activities -> LightStrip YELLOW")
            self._strip.setColor(COLOR_YELLOW)
            if playSound:
                self._buzzer.beep(700, 100)
                self._buzzer.beep(900, 120)
        else:
            Log.i(f"CRMController: '{customer.customer_name}' has {count} activities -> LightStrip GREEN")
            self._strip.setColor(COLOR_GREEN)
            if playSound:
                self._buzzer.beep(800, 100)
                self._buzzer.beep(1200, 150)

    def updateDisplay(self):
        """
        Render the current Customer, Contact, or Activity onto the 16x2 LCDDisplay.

        Examples:
        ---------
        1. controller.updateDisplay()
        """
        if not self.customers:
            self._showLCD("No Customers", "Check API/WiFi")
            return

        cust = self.customers[self.currentCustIndex]

        if self.mode == self.MODE_CUSTOMERS:
            line0 = cust.customer_name
            line1 = f"#{self.currentCustIndex + 1}/{len(self.customers)} {cust.category}"
            self._showLCD(line0, line1)

        elif self.mode == self.MODE_CONTACTS:
            contacts = cust.getContacts()
            if contacts:
                c = contacts[self.currentSubIndex]
                role = c.title or c.contact_type or c.company
                line0 = c.name
                line1 = f"C{self.currentSubIndex + 1}/{len(contacts)} {role}"
                self._showLCD(line0, line1)
            else:
                self._showLCD("No Contacts", "Select->Activ.")

        elif self.mode == self.MODE_ACTIVITIES:
            activities = cust.getActivities()
            if activities:
                a = activities[self.currentSubIndex]
                line0 = f"A{self.currentSubIndex + 1}/{len(activities)} {a.activity_type}"
                line1 = a.name
                self._showLCD(line0, line1)
            else:
                self._showLCD("No Activities", "Select->Back")

    def run(self):
        """
        Start the CRM controller and process queued button events in the main loop.

        Examples:
        ---------
        1. controller.run()
        """
        self.start()
        self._running = True
        while self._running:
            if self._pendingButton is not None:
                btn = self._pendingButton
                self._pendingButton = None
                if btn == "Next":
                    self.nextItem()
                elif btn == "Select":
                    self.selectItem()
            time.sleep(0.05)

    def stop(self):
        """
        Stop the controller loop and turn off hardware outputs cleanly.

        Examples:
        ---------
        1. controller.stop()
        """
        Log.i("CRMController: stop()")
        self._running = False
        self._strip.off()
        self._buzzer.stop()
        self._display.reset()
        try:
            self._net.disconnect()
        except Exception:
            pass


if __name__ == "__main__":
    # Self-contained mock test (runs cleanly on desktop Python or Pico)
    class _MockNet:
        def connect(self, ssid, password):
            Log.i(f"[MockNet] connect({ssid})")

        def getLocalIp(self):
            return "192.168.1.42"

        def getJson(self, url):
            if url.endswith("/version"):
                return {"version": "1.0"}
            if url.endswith("/get_customers"):
                return {
                    "items": [
                        {
                            "id": 128914493284257047125893002539859332792,
                            "customer_name": "Joseph Londono",
                            "category": "Consumer",
                            "category_description": "General Consumer",
                            "geography_name": "North America",
                            "type": None,
                        }
                    ],
                    "hasMore": False,
                }
            if "/get_contacts/" in url:
                return {
                    "items": [
                        {
                            "id": 101,
                            "name": "James Johnson",
                            "title": "Manager",
                            "company": "Lights Inc.",
                            "phone": "305 242 4511",
                            "contact_type": "Product Manager",
                        }
                    ]
                }
            if "/get_activities/" in url:
                return {
                    "items": [
                        {
                            "id": 6,
                            "activity_type": "Meeting",
                            "name": "Face-to-Face",
                            "description": "In person meeting",
                        },
                        {
                            "id": 2,
                            "activity_type": "Phone Call",
                            "name": "Cold Call",
                            "owner": "Jack Han",
                        },
                    ]
                }
            return None

        def disconnect(self):
            Log.i("[MockNet] disconnect()")

    class _MockDisplay:
        def showText(self, text, row=0, col=0):
            Log.i(f"[MockLCD] row {row}: '{text}'")

        def reset(self):
            Log.i("[MockLCD] reset()")

    class _MockStrip:
        def setColor(self, color, numPixels=None):
            Log.i(f"[MockStrip] setColor({color}, numPixels={numPixels})")

        def off(self):
            Log.i("[MockStrip] off()")

    class _MockBuzzer:
        def beep(self, tone=500, duration=150):
            Log.i(f"[MockBuzzer] beep({tone}Hz, {duration}ms)")

        def stop(self):
            Log.i("[MockBuzzer] stop()")

    class _MockButton:
        pass

    ctrl = CRMController(
        ssid="TestHotspot",
        password="test",
        eagerLoad=False,
        net=_MockNet(),
        display=_MockDisplay(),
        strip=_MockStrip(),
        buzzer=_MockBuzzer(),
        btnNext=_MockButton(),
        btnSelect=_MockButton(),
    )
    ctrl.start()
    assert len(ctrl.customers) == 1
    assert not ctrl.customers[0].hasDetailsLoaded()

    # Simulate Option B flow: Select customer -> loads contacts & activities -> view contacts -> view activities -> goBack
    ctrl.selectItem()
    assert ctrl.customers[0].hasDetailsLoaded()
    assert ctrl.mode == CRMController.MODE_CONTACTS
    ctrl.selectItem()
    assert ctrl.mode == CRMController.MODE_ACTIVITIES
    ctrl.selectItem()
    assert ctrl.mode == CRMController.MODE_CUSTOMERS
    ctrl.stop()

    Log.i("Testing complete - CRMController passed all Option B checks")
