#!/usr/bin/python

# origininal source: https://github.com/8devices/IoTPy/

from time import sleep
from struct import unpack
from smbus import SMBus

# from IoTPy.errors import IoTPy_ThingError


I2C_ADDR_AM2320 = 0x5c  # 0xB8 >> 1
PARAM_AM2320_READ = 0x03
REG_AM2320_HUMIDITY_MSB = 0x00
REG_AM2320_HUMIDITY_LSB = 0x01
REG_AM2320_TEMPERATURE_MSB = 0x02
REG_AM2320_TEMPERATURE_LSB = 0x03
REG_AM2320_DEVICE_ID_BIT_24_31 = 0x0B


class CommunicationError(Exception):
    pass


class AM2320(object):
    """
    AM2320 temperature and humidity sensor class.

    :param interface:  I2C interface id.
    :type interface: :int
    :param sensor_address: AM2320 sensor I2C address. Optional, default 0x5C (92).
    :type sensor_address: int
    """

    def __init__(self, interface, sensor_address=0x5c):
        self.interface = interface
        self.address = sensor_address
        self.temperature = -1000.0
        self.humidity = -1
        self.bus = SMBus(interface)

    def _read_raw(self, command, regaddr, regcount):
        try:
            self.bus.write_i2c_block_data(self.address, 0x00, [])
            self.bus.write_i2c_block_data(self.address, command, [regaddr, regcount])

            sleep(0.002)

            buf = self.bus.read_i2c_block_data(self.address, 0, 8)
        except IOError, exc:
            raise CommunicationError(str(exc))

        buf_str = "".join(chr(x) for x in buf)

        crc = unpack('<H', buf_str[-2:])[0]
        if crc != self._am_crc16(buf[:-2]):
            raise CommunicationError("AM2320 CRC error.")
        return buf_str[2:-2]

    def _am_crc16(self, buf):
        crc = 0xFFFF
        for c in buf:
            crc ^= c
            for i in range(8):
                if crc & 0x01:
                    crc >>= 1
                    crc ^= 0xA001
                else:
                    crc >>= 1
        return crc

    def read_uid(self):
        """
        Read and return unique 32bit sensor ID.

        :return: A unique 32bit sensor ID.
        :rtype: int
        """
        resp = self._read_raw(PARAM_AM2320_READ, REG_AM2320_DEVICE_ID_BIT_24_31, 4)
        uid = unpack('>I', resp)[0]
        return uid

    def read(self):
        """
        Read and store temperature and humidity value.

        Read temperature and humidity registers from the sensor, then convert and store them.
        Use :func:`temperature` and :func:`humidity` to retrieve these values.
        """
        raw_data = self._read_raw(PARAM_AM2320_READ, REG_AM2320_HUMIDITY_MSB, 4)
        self.temperature = unpack('>H', raw_data[-2:])[0] / 10.0
        self.humidity = unpack('>H', raw_data[-4:2])[0] / 10.0


if __name__ == '__main__':
    am2320 = AM2320(1)
    am2320.read()
    print am2320.temperature, am2320.humidity
