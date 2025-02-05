"""VeSync API Device Libary."""

import logging
import re
import time
from typing import List, Optional

from .helpers import Helpers, EDeviceFamily, logger as helper_logger
from .vesyncbasedevice import VeSyncBaseDevice
from .vesyncbulb import factory as bulb_factory, logger as bulb_logger
from .vesyncfan import factory as fan_factory, logger as fan_logger
from .vesynckitchen import factory as kitchen_factory, logger as kitchen_logger
from .vesyncoutlet import factory as outlet_factory, logger as outlet_logger
from .vesyncswitch import factory as switch_factory, logger as switch_logger

logger = logging.getLogger(__name__)

API_RATE_LIMIT: int = 30
DEFAULT_TZ: str = 'America/New_York'

DEFAULT_ENER_UP_INT: int = 21600

FACTORIES = (bulb_factory, fan_factory, kitchen_factory, outlet_factory, switch_factory)


class VeSync:  # pylint: disable=function-redefined
    """VeSync Manager Class."""

    _debug: bool
    _redact:bool
    username: str
    password: str
    token: Optional[str] = None
    account_id: Optional[str] = None
    country_code: Optional[str] = None
    enabled: float = False
    update_interval: int = API_RATE_LIMIT
    last_update_ts: Optional[float] = None
    in_process: bool = False
    _energy_update_interval: int = DEFAULT_ENER_UP_INT
    _energy_check: bool = True
    time_zone: str = DEFAULT_TZ
 
    def __init__(self, username, password, time_zone=DEFAULT_TZ,
                 debug=False, redact=True):
        """Initialize VeSync Manager.

        This class is used as the manager for all VeSync objects, all methods and
        API calls are performed from this class. Time zone, debug and redact are
        optional. Time zone must be a string of an IANA time zone format. Once
        class is instantiated, call `manager.login()` to log in to VeSync servers,
        which returns `True` if successful. Once logged in, call `manager.update()`
        to retrieve devices and update device details.

        Parameters:
            username : str
                VeSync account username (usually email address)
            password : str
                VeSync account password
            time_zone : str, optional
                Time zone for device from IANA database, by default DEFAULT_TZ
            debug : bool, optional
                Enable debug logging, by default False
            redact : bool, optional
                Redact sensitive information in logs, by default True

        Attributes:
            fans : list
                List of VeSyncFan objects for humidifiers and air purifiers
            outlets : list
                List of VeSyncOutlet objects for smart plugs
            switches : list
                List of VeSyncSwitch objects for wall switches
            bulbs : list
                List of VeSyncBulb objects for smart bulbs
            kitchen : list
                List of VeSyncKitchen objects for smart kitchen appliances
            dev_list : dict
                Dictionary of device lists
            token : str
                VeSync API token
            account_id : str
                VeSync account ID
            enabled : bool
                True if logged in to VeSync, False if not
        """
        self.debug = debug
        self.redact = redact
        self.username = username
        self.password = password
        self._device_list: list[VeSyncBaseDevice] = []

        if isinstance(time_zone, str) and time_zone:
            reg_test = r'[^a-zA-Z/_]'
            if bool(re.search(reg_test, time_zone)):
                logger.warning('Invalid characters in time zone %s - using default!', time_zone)
            else:
                self.time_zone = time_zone
        else:
            logger.warning('Time zone is not a string - using default!')

    @property
    def debug(self) -> bool:
        """Return debug flag."""
        return self._debug

    @debug.setter
    def debug(self, new_flag: bool) -> None:
        """Set debug flag."""
        self._debug = new_flag
        level = logging.DEBUG if new_flag else logging.WARNING

        logger.setLevel(level)
        bulb_logger.setLevel(level)
        fan_logger.setLevel(level)
        helper_logger.setLevel(level)
        outlet_logger.setLevel(level)
        switch_logger.setLevel(level)
        kitchen_logger.setLevel(logging.DEBUG)

    @property
    def redact(self) -> bool:
        """Return debug flag."""
        return self._redact

    @redact.setter
    def redact(self, new_flag: bool) -> None:
        """Set debug flag."""
        if new_flag:
            Helpers.should_redact = True
        elif new_flag is False:
            Helpers.should_redact = False
        self._redact = new_flag

    @property
    def energy_update_interval(self) -> int:
        """Return energy update interval."""
        return self._energy_update_interval

    @energy_update_interval.setter
    def energy_update_interval(self, new_energy_update: int) -> None:
        """Set energy update interval in seconds."""
        if new_energy_update > 0:
            self._energy_update_interval = new_energy_update

    @staticmethod
    def remove_dev_test(device, new_list: list) -> bool:
        """Test if device should be removed - False = Remove."""
        if isinstance(new_list, list) and device.cid:
            for item in new_list:
                device_found = False
                if 'cid' in item:
                    if device.cid == item['cid']:
                        device_found = True
                        break
                else:
                    logger.debug('No cid found in - %s', str(item))
            if not device_found:
                logger.debug(
                    'Device removed - %s - %s',
                    device.device_name, device.device_type
                )
                return False
        return True

    def add_dev_test(self, new_dev: dict) -> bool:
        """Test if new device should be added - True = Add."""
        if 'cid' in new_dev:
            for dev in self._device_list:
                if (
                    dev.cid == new_dev.get('cid')
                    and new_dev.get('subDeviceNo', 0) == dev.sub_device_no
                ):
                    return False
        return True

    def remove_old_devices(self, devices: list) -> bool:
        """Remove devices not found in device list return."""
        before = len(self._device_list)
        self._device_list = [x for x in self._device_list if self.remove_dev_test(x, devices)]
        after = len(self._device_list)
        if before != after:
            logger.debug('%s devices removed', str((before - after)))
        return True

    @staticmethod
    def set_dev_id(devices: list) -> list:
        """Correct devices without cid or uuid."""
        dev_num = 0
        dev_rem = []
        for dev in devices:
            if dev.get('cid') is None:
                if dev.get('macID') is not None:
                    dev['cid'] = dev['macID']
                elif dev.get('uuid') is not None:
                    dev['cid'] = dev['uuid']
                else:
                    dev_rem.append(dev_num)
                    logger.warning('Device with no ID  - %s',
                                   dev.get('deviceName'))
            dev_num += 1
            if dev_rem:
                devices = [i for j, i in enumerate(
                            devices) if j not in dev_rem]
        return devices

    def object_factory(self, details: dict) -> VeSyncBaseDevice:
        """Get device type and instantiate class.

        Pulls the device types from each module to determine the type of device and
        instantiates the device object.

        Args:
            dev_type (str): Device model type returned from API
            config (dict): Device configuration from `VeSync.get_devices()` API call

        Returns:
            VeSyncBaseDevice: instantiated device object or None for unsupported devices.

        Note:
            Each device type implements a factory for the supported device types.
            the newly created device instance is added to the device list.
        """
        dev_type = details.get('deviceType')
        dev_name = details.get('deviceName', '#MISS#')
        for factory in FACTORIES:
            try:
                device = factory(dev_type, details, self)
                if device:
                    self._device_list.append(device)
                    break
            except AttributeError as err:
                logger.debug('Error - %s: device %s(%s) not added', err, dev_name, dev_type)

        if (device is None):
            logger.debug('Unknown device %s (%s) - not added!', dev_type, dev_name)

        return device

    def process_devices(self, dev_list: list) -> bool:
        """Instantiate Device Objects.

        Internal method run by `get_devices()` to instantiate device objects.

        """
        devices = VeSync.set_dev_id(dev_list)

        num_devices = len(self._device_list)

        if not devices:
            logger.warning('No devices found in api return')
            return False
        if num_devices == 0:
            logger.debug('New device list initialized')
        else:
            self.remove_old_devices(devices)

        devices[:] = [x for x in devices if self.add_dev_test(x)]
        self._device_list = []
        detail_keys = ['deviceType', 'deviceName', 'deviceStatus']
        for dev_details in devices:
            if not all(k in dev_details for k in detail_keys):
                logger.debug('Error adding device')
                continue
            self.object_factory(dev_details)

        return True

    def get_devices(self) -> bool:
        """Return tuple listing outlets, switches, and fans of devices.

        This is an internal method called by `update()`
        """
        if not self.enabled:
            return False

        self.in_process = True

        proc_return = False
        body = Helpers.req_body_devices(self)
        r = Helpers.call_api('/cloud/v1/deviceManaged/devices',
            method='post',
            headers=Helpers.req_header_bypass(),
            json_object=body
        )

        if r and Helpers.code_check(r):
            if 'result' in r and 'list' in r['result']:
                device_list = r['result']['list']
                proc_return = self.process_devices(device_list)
            else:
                logger.error('Device list in response not found')
        else:
            logger.warning('Error retrieving device list')

        self.in_process = False

        return proc_return

    def login(self) -> bool:
        """Log into VeSync server.

        Username and password are provided when class is instantiated.

        Returns:
            True if login successful, False if not
        """
        user_check = isinstance(self.username, str) and len(self.username) > 0
        pass_check = isinstance(self.password, str) and len(self.password) > 0
        if user_check is False:
            logger.error('Username invalid')
            return False
        if pass_check is False:
            logger.error('Password invalid')
            return False

        r = Helpers.call_api('/cloud/v1/user/login',
            'post',
            json_object=Helpers.req_body_login(self)
        )

        if Helpers.code_check(r) and 'result' in r:
            self.token = r.get('result').get('token')
            self.account_id = r.get('result').get('accountID')
            self.country_code = r.get('result').get('countryCode')
            self.enabled = True
            logger.debug('Login successful')
            logger.debug('token %s', self.token)
            logger.debug('account_id %s', self.account_id)

            return True
        logger.error('Error logging in with username and password')
        return False

    def device_time_check(self) -> bool:
        """Test if update interval has been exceeded."""
        return (
            self.last_update_ts is None
            or (time.time() - self.last_update_ts) > self.update_interval
        )

    def update(self) -> None:
        """Fetch updated information about devices.

        Pulls devices list from VeSync and instantiates any new devices. Devices
        are stored in the instance attributes `outlets`, `switches`, `fans`, and
        `bulbs`. The `_device_list` attribute is a dictionary of these attributes.
        """
        if self.device_time_check():

            if not self.enabled:
                logger.error('Not logged in to VeSync')
                return

            self.get_devices()

            logger.debug('Start updating the device details one by one')
            self.update_all_devices()

            self.last_update_ts = time.time()

    def update_energy(self, bypass_check=False) -> None:
        """Fetch updated energy information for outlet devices."""
        for outlet in self.outlets:
            outlet.update_energy(bypass_check)

    def update_all_devices(self) -> None:
        """Run `get_details()` for each device and update state."""
        for dev in self._device_list:
            dev.update()

    @property
    def bulbs(self) -> List[VeSyncBaseDevice]:
        '''Returns a list of all registered bulbs'''
        return [dev for dev in self._device_list if dev.device_family == EDeviceFamily.BULB]

    @property
    def fans(self) -> List[VeSyncBaseDevice]:
        '''Returns a list of all registered fans'''
        return [dev for dev in self._device_list if dev.device_family == EDeviceFamily.FAN]

    @property
    def kitchen(self) -> List[VeSyncBaseDevice]:
        '''Returns a list of all registered kitchen devices'''
        return [dev for dev in self._device_list if dev.device_family == EDeviceFamily.KITCHEN]

    @property
    def outlets(self) -> List[VeSyncBaseDevice]:
        '''Returns a list of all registered outlets'''
        return [dev for dev in self._device_list if dev.device_family == EDeviceFamily.OUTLET]

    @property
    def switches(self) -> List[VeSyncBaseDevice]:
        '''Returns a list of all registered switches'''
        return [dev for dev in self._device_list if dev.device_family == EDeviceFamily.SWITCH]

    @property
    def device_list(self) -> List[VeSyncBaseDevice]:
        '''Returns a list of all registered devices'''
        return [dev for dev in self._device_list]
