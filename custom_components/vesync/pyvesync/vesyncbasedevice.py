"""Base class for all VeSync devices."""
from __future__ import annotations
import logging
import json
from typing import Optional
from abc import ABCMeta, abstractmethod

from .helpers import Helpers, EDeviceFamily

logger = logging.getLogger(__name__)

STATUS_ON = 'on'
STATUS_OFF = 'off'
MODE_ADVANCED_SLEEP = 'advancedSleep'
MODE_AUTO = 'auto'
MODE_DIM = 'dim'
MODE_HUMIDITY = 'humidity'
MODE_MANUAL = 'manual'
MODE_NORMAL = 'normal'
MODE_PET = 'pet'
MODE_SLEEP = 'sleep'
MODE_TURBO = 'turbo'

class VeSyncBaseDevice:
    """Properties shared across all VeSync devices.

    Base class for all VeSync devices.

    Parameters:
        details (dict): Device details from API call.
        manager (VeSync): Manager object for API calls.

    Attributes:
        device_name (str): Name of device.
        device_image (str): URL for device image.
        cid (str): Device ID.
        connection_status (str): Connection status of device.
        connection_type (str): Connection type of device.
        device_type (str): Type of device.
        type (str): Type of device.
        uuid (str): UUID of device, not always present.
        config_module (str): Configuration module of device.
        mac_id (str): MAC ID of device.
        mode (str): Mode of device.
        speed (Union[str, int]): Speed of device.
        extension (dict): Extension of device, not used.
        current_firm_version (str): Current firmware version of device.
        device_region (str): Region of device. (US, EU, etc.)
        pid (str): Product ID of device, pulled by some devices on update.
        sub_device_no (int): Sub-device number of device.
        config (dict): Configuration of device, including firmware version
        device_status (str): Status of device, on or off.

    Methods:
        is_on(): Return True if device is on.
        firmware_update(): Return True if firmware update available.
        display(): Print formatted device info to stdout.
        displayJSON(): JSON API for device details.
    """
    manager = None # VeSync
    cid: str = None
    config: dict = {}
    config_module: str = None
    connection_status: str = None
    connection_type: Optional[str] = None
    current_firm_version: str = None
    device_family: EDeviceFamily = EDeviceFamily.NOT_SUPPORTED
    device_name: str = None
    device_image: str = None
    device_region: Optional[str] = None
    device_status: Optional[str] = None
    device_type: str = None
    extension = None
    mac_id: Optional[str] = None
    mode: Optional[str] = None
    pid = None
    speed: Optional[int] = None
    sub_device_no: int = 0
    type: Optional[str] = None
    uuid: Optional[str] = None
    speed: Optional[str] = None
    
    __metaclass__ = ABCMeta

    def __init__(self, details: dict, manager, device_family: EDeviceFamily) -> None:
        """Initialize VeSync device base class."""
        self.manager = manager
        if 'cid' in details and details['cid'] is not None:
            self.device_name = details['deviceName']
            self.device_image = details.get('deviceImg')
            self.cid = details['cid']
            self.connection_status = details['connectionStatus']
            self.connection_type = details.get('connectionType')
            self.device_type = details['deviceType']
            self.type = details.get('type')
            self.uuid = details.get('uuid')
            self.config_module = details['configModule']
            self.mac_id = details.get('macID')
            self.mode = details.get('mode')
            self.speed = details.get('speed') if details.get('speed') != '' else None
            self.extension = details.get('extension')
            self.current_firm_version = details.get('currentFirmVersion')
            self.device_region = details.get('deviceRegion')
            self.pid = None
            self.sub_device_no = details.get('subDeviceNo', 0)
            if isinstance(details.get('extension'), dict):
                ext = details['extension']
                self.speed = ext.get('fanSpeedLevel')
                self.mode = ext.get('mode')
            if self.connection_status != 'online':
                self.device_status = STATUS_OFF
            else:
                self.device_status = details.get('deviceStatus')

            self.device_family = device_family

        else:
            logger.error('No cid found for %s', self.__class__.__name__)
        self.details = {}

    def __eq__(self, other: object) -> bool:
        """Use device CID and subdevice number to test equality."""
        if not isinstance(other, VeSyncBaseDevice):
            return NotImplemented
        return bool(other.cid == self.cid
                    and other.sub_device_no == self.sub_device_no)

    def __hash__(self) -> int:
        """Use CID and sub-device number to make device hash."""
        if isinstance(self.sub_device_no, int) and self.sub_device_no > 0:
            return hash(self.cid + str(self.sub_device_no))
        return hash(self.cid)

    def __str__(self) -> str:
        """Use device info for string represtation of class."""
        return f'Device Name: {self.device_name}, ' + \
               f'Device Type: {self.device_type}, ' + \
               f'SubDevice No.: {self.sub_device_no}, ' + \
               f'Status: {self.device_status}'

    def __repr__(self) -> str:
        """Representation of device details."""
        return f'DevClass: {self.__class__.__name__}, ' + \
               f'Name:{self.device_name}, ' + \
               f'Device No: {self.sub_device_no}, ' + \
               f'DevStatus: {self.device_status}, ' + \
               f'CID: {self.cid}'

    @property
    def is_on(self) -> bool:
        """Return true if device is on."""
        return (self.device_status == STATUS_ON)

    @property
    def firmware_update(self) -> bool:
        """Return True if firmware update available."""
        cfv = self.config.get('current_firmware_version')
        lfv = self.config.get('latest_firmware_version')
        if cfv is not None and lfv is not None:
            if cfv != lfv:
                return True
        else:
            logger.debug('Call device.get_config() to get firmware versions')
        return False

    def call_api_v1(self, api, body):
        r = Helpers.call_api(f'/cloud/v1/deviceManaged/{api}',
            method='post',
            headers=Helpers.req_header_bypass(self.manager),
            json_object=body
        )
        return r

    def get_pid(self) -> None:
        """Get managed device configuration."""
        body = Helpers.req_body_device_detail(self.manager)
        body['configModule'] = self.config_module
        body['region'] = self.device_region
        body['method'] = 'configInfo'
        r = self.call_api_v1('configInfo', body)
        if not isinstance(r, dict) or r.get('code') != 0 or r.get('result') is None:
            logger.error('Error getting config info for %s', self.device_name)
            return
        self.pid = r.get('result', {}).get('pid')

    def display(self) -> None:
        """Print formatted device info to stdout.

        Example:
        ```
        Device Name:..................Living Room Lamp
        Model:........................ESL100
        Subdevice No:.................0
        Status:.......................on
        Online:.......................online
        Type:.........................wifi
        CID:..........................1234567890abcdef
        ```
        """
        disp = [
            ('Device Name', self.device_name),
            ('Model', self.device_type),
            ('Subdevice No', str(self.sub_device_no)),
            ('Status', self.device_status),
            ('Connection', self.connection_status),
            ('Type', self.type),
            ('CID', self.cid),
        ]
        if self.uuid is not None:
            disp.append(('UUID', self.uuid))

        for line in disp:
            print(f"{line[0]+': ':.<30} {line[1]}")

    def displayJSON(self) -> str:  # pylint: disable=invalid-name
        """JSON API for device details.

        Returns:
            str: JSON formatted string of device details.

        Example:
        ```
        {
            "Device Name": "Living Room Lamp",
            "Model": "ESL100",
            "Subdevice No": "0",
            "Status": "on",
            "Online": "online",
            "Type": "wifi",
            "CID": "1234567890abcdef"
        }
        ```
        """
        return json.dumps(
            {
                'Device Name': self.device_name,
                'Model': self.device_type,
                'Subdevice No': str(self.sub_device_no),
                'Status': self.device_status,
                'Online': self.connection_status,
                'Type': self.type,
                'CID': self.cid,
            },
            indent=4)

    @abstractmethod
    def turn(self, status: str) -> bool:
        """Turn on/off vesync lightbulb.

        Helper function called by `turn_on()` and `turn_off()`.

        Args:
            status (str): 'on' or 'off'

        Returns:
            bool: True if successful, False otherwise.
        """

    def turn_on(self) -> bool:
        """Turn on device and return True if successful."""
        return self.turn(STATUS_ON)

    def turn_off(self) -> bool:
        """Turn off devivce and return True if successful."""
        return self.turn(STATUS_OFF)
