"""Classes for VeSync Switch Devices.

This module provides classes for VeSync Switch Devices:

    1. VeSyncSwitch: Abstract Base class for VeSync Switch Devices.
    2. VeSyncWallSwitch: Class for VeSync Wall Switch Devices ESWL01 and ESWL03.
    3. VeSyncDimmerSwitch: Class for VeSync Dimmer Switch Devices ESWD16.


Attributes:
    feature_dict (dict): Dictionary of switch models and their supported features.
        Defines the class to use for each switch model and the list of features
    switch_modules (dict): Dictionary of switch models as keys and their associated
        classes as string values.

Note:
    The switch device is built from the `feature_dict` dictionary and used by the
    `vesync.object_factory` during initial call to pyvesync.vesync.update() and
    determines the class to instantiate for each switch model. These classes should
    not be instantiated manually.
"""

import logging
import json
import sys
from abc import ABCMeta, abstractmethod
from typing import Dict, Union, Optional

from .helpers import Helpers, EDeviceFamily, API_DETAIL, API_STATUS
from .vesyncbasedevice import VeSyncBaseDevice, STATUS_ON, STATUS_OFF

logger = logging.getLogger(__name__)

module_switch = sys.modules[__name__]

# --8<-- [start:feature_dict]

feature_dict: Dict[str, Dict[str, Union[list, str]]] = {
    'ESWL01': {
        'module': 'VeSyncWallSwitch',
        'features': []
    },
    'ESWL03': {
        'module': 'VeSyncWallSwitch',
        'features': []
    },
    'ESWD16': {
        'module': 'VeSyncDimmerSwitch',
        'features': ['dimmable']
    }
}

# --8<-- [end:feature_dict]

switch_modules: dict = {k: v['module']
                        for k, v in feature_dict.items()}

__all__: list = list(switch_modules.values()) + ['switch_modules']

class VeSyncSwitch(VeSyncBaseDevice):
    """Etekcity Switch Base Class.

    Abstract Base Class for Etekcity Switch Devices, inheriting from
    pyvesync.vesyncbasedevice.VeSyncBaseDevice. Should not be instantiated directly,
    subclassed by VeSyncWallSwitch and VeSyncDimmerSwitch.

    Attributes:
        features (list): List of features supported by the switch device.
        details (dict): Dictionary of switch device details.
    """

    device_family = EDeviceFamily.SWITCH
    features: dict = {}

    __metaclasss__ = ABCMeta

    def __init__(self, details, manager):
        """Initialize Switch Base Class."""
        super().__init__(details, manager, EDeviceFamily.SWITCH)
        self.features = feature_dict.get(self.device_type, {}).get('features')
        if self.features is None:
            logger.error('% device configuration not set', self.device_name)
            raise KeyError(f'Device configuration not set {self.device_name}')

    def is_dimmable(self) -> bool:
        """Return True if switch is dimmable."""
        return bool('dimmable' in self.features)

    @abstractmethod
    def get_details(self) -> None:
        """Get Device Details."""

    @abstractmethod
    def get_config(self) -> None:
        """Get configuration and firmware details."""

    @property
    def active_time(self) -> int:
        """Get active time of switch."""
        return self.details.get('active_time', 0)

    def update(self) -> None:
        """Update device details."""
        self.get_details()

    def _get_body(self, req_type: str, values: Optional[dict] = None) -> dict:
        body = Helpers.req_body(self.manager, req_type)
        body['uuid'] = self.uuid
        if (values):
            body |= values
        return body

    def _get_result(self, body:dict, path: str, method: str) -> dict:
        headers = Helpers.req_headers(self.manager)
        r = Helpers.call_api(path, method, headers=headers, json_object=body)
        return r

class VeSyncWallSwitch(VeSyncSwitch):
    """Etekcity standard wall switch class."""

    def get_details(self) -> None:
        """Get switch device details."""
        body = self._get_body(API_DETAIL)
        r = self._get_result(body, '/inwallswitch/v1/device/devicedetail', 'post')

        if r is not None and Helpers.code_check(r):
            self.device_status = r.get('deviceStatus', self.device_status)
            self.details['active_time'] = r.get('activeTime', 0)
            self.connection_status = r.get(
                'connectionStatus', self.connection_status)
        else:
            logger.debug('Error getting %s details', self.device_name)

    def get_config(self) -> None:
        """Get switch device configuration info."""
        body = self._get_body(API_DETAIL, {'method': 'configurations'})
        r = self._get_result(body, '/inwallswitch/v1/device/configurations', 'post')

        if Helpers.code_check(r):
            self.config = Helpers.build_config_dict(r)
        else:
            logger.warning('Unable to get %s config info', self.device_name)

    def turn(self, status: str) -> bool:
        """Turn switch device on/off."""
        if status not in [STATUS_ON, STATUS_OFF]:
            logger.debug('Invalid status passed to wall switch')
            return False
        body = self._get_body(API_STATUS, {'status': status})
        r = self._get_result(body, '/inwallswitch/v1/device/devicestatus', 'put')

        if r is not None and Helpers.code_check(r):
            self.device_status = status
            return True

        logger.warning('Error turning %s %s', self.device_name, status)
        return False


class VeSyncDimmerSwitch(VeSyncSwitch):
    """VeSync Dimmer Switch Class with RGB Faceplate."""

    _brightness: float = 0
    _indicator_light: str = None
    _rgb_status: str = None
    _rgb_value: dict = {'red': 0, 'blue': 0, 'green': 0}

    def __init__(self, details, manager):
        """Initialize dimmer switch class."""
        super().__init__(details, manager)
        self._brightness = 0
        self._rgb_value = {'red': 0, 'blue': 0, 'green': 0}
        self._rgb_status = 'unknown'
        self._indicator_light = 'unknown'

    def get_details(self) -> None:
        """Get dimmer switch details."""
        body = self._get_body(API_DETAIL)
        r = self._get_result(body, '/dimmer/v1/device/devicedetail', 'post')

        if r is not None and Helpers.code_check(r):
            self.device_status = r.get('deviceStatus', self.device_status)
            self.details['active_time'] = r.get('activeTime', 0)
            self.connection_status = r.get('connectionStatus', self.connection_status)
            self._brightness = r.get('brightness')
            self._rgb_status = r.get('rgbStatus')
            self._rgb_value = r.get('rgbValue')
            self._indicator_light = r.get('indicatorlightStatus')
        else:
            logger.debug('Error getting %s details', self.device_name)

    @property
    def brightness(self) -> float:
        """Return brightness in percent."""
        return self._brightness

    @property
    def indicator_light_status(self) -> str:
        """Faceplate brightness light status."""
        return self._indicator_light

    @property
    def rgb_light_status(self) -> str:
        """RGB Faceplate light status."""
        return self._rgb_status

    @property
    def rgb_light_value(self) -> dict:
        """RGB Light Values."""
        return self._rgb_value

    def get_config(self) -> None:
        """Get dimmable switch device configuration info."""
        body = self._get_body(API_DETAIL, {'method': 'configurations'})
        r = self._get_result(body, '/dimmer/v1/device/configurations', 'post')

        if Helpers.code_check(r):
            self.config = Helpers.build_config_dict(r)
        else:
            logger.warning('Unable to get %s config info', self.device_name)

    def turn(self, status: str) -> bool:
        """Turn switch on/off."""
        if status not in [STATUS_ON, STATUS_OFF]:
            logger.debug('Invalid status passed to wall switch')
            return False
        body = self._get_body(API_STATUS, {'status': status})
        r = self._get_result(body, '/dimmer/v1/device/devicestatus', 'put')

        if r is not None and Helpers.code_check(r):
            self.device_status = status
            return True

        logger.warning('Error turning %s %s', self.device_name, status)
        return False

    def indicator_light_turn(self, status: str) -> bool:
        """Turn indicator light."""
        if status not in [STATUS_ON, STATUS_OFF]:
            logger.debug('Invalid status for wall switch')
            return False
        body = self._get_body(API_STATUS, {'status': status})
        r = self._get_result(body, '/dimmer/v1/device/indicatorlightstatus', 'put')

        if r is not None and Helpers.code_check(r):
            self.device_status = status
            return True

        logger.warning('Error turning %s indicator light %s',
                       self.device_name, status)
        return False

    def indicator_light_on(self) -> bool:
        """Turn Indicator light on."""
        return self.indicator_light_turn(STATUS_ON)

    def indicator_light_off(self) -> bool:
        """Turn indicator light off."""
        return self.indicator_light_turn(STATUS_OFF)

    def rgb_color_status(self, status: str,
                         red: Optional[int] = None,
                         blue: Optional[int] = None,
                         green: Optional[int] = None) -> bool:
        """Set faceplate RGB color."""
        body = self._get_body(API_STATUS, {'status': status})
        if red is not None and blue is not None and green is not None:
            body['rgbValue'] = {'red': red, 'blue': blue, 'green': green}
        r = self._get_result(body, '/dimmer/v1/device/devicergbstatus', 'put')

        if r is not None and Helpers.code_check(r):
            self._rgb_status = status
            if body.get('rgbValue') is not None:
                self._rgb_value = {'red': red, 'blue': blue, 'green': green}
            return True
        logger.warning('Error setting %s RGB %s', self.device_name, status)
        return False

    def rgb_color_off(self) -> bool:
        """Turn RGB Color Off."""
        return self.rgb_color_status(STATUS_OFF)

    def rgb_color_on(self) -> bool:
        """Turn RGB Color Off."""
        return self.rgb_color_status(STATUS_ON)

    def rgb_color_set(self, red: int, green: int, blue: int) -> bool:
        """Set RGB color of faceplate."""
        try:
            red = int(red)
            green = int(green)
            blue = int(blue)
        except ValueError:
            return False
        if isinstance(red, int) and isinstance(
                green, int) and isinstance(blue, int):
            for color in [red, green, blue]:
                if color < 0 or color > 255:
                    logger.warning('Invalid RGB value')
                    return False

            return bool(self.rgb_color_status(STATUS_ON, red, green, blue))
        return False

    def set_brightness(self, brightness: int) -> bool:
        """Set brightness of dimmer - 1 - 100."""
        if isinstance(brightness, int) and (
                brightness > 0 or brightness <= 100):

            body = self._get_body(API_STATUS, {'brightness': brightness})
            r = self._get_result(body, '/dimmer/v1/device/updatebrightness', 'put')

            if r is not None and Helpers.code_check(r):
                self._brightness = brightness
                return True
            logger.warning('Error setting %s brightness', self.device_name)
        else:
            logger.warning('Invalid brightness')
        return False

    def display(self) -> None:
        """Return formatted device info to stdout."""
        super().display()
        disp = [
            ('Indicator Light', self.active_time, 'min'),
            ('Brightness', self._brightness, '%'),
            ('RGB Light', self._rgb_status, ''),
        ]
        for line in disp:
            print(f"{line[0]+': ':.<30} {' '.join(line[1:])}")

    def displayJSON(self) -> str:
        """JSON API for dimmer switch."""
        sup_val = json.loads(super().displayJSON())
        if self.is_dimmable is True:  # pylint: disable=using-constant-test
            sup_val.update(
                {
                    'Indicator Light': str(self.active_time),
                    'Brightness': str(self._brightness),
                    'RGB Light': str(self._rgb_status),
                }
            )
        return json.dumps(sup_val, indent=4)


def factory(module: str, details: dict, manager) -> VeSyncSwitch:
    try:
        definition = switch_modules[module]
        switch = getattr(module_switch, definition)
        return switch(details, manager)
    except:
        return None
