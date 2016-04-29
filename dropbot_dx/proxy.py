import pkg_resources
import time

from path_helpers import path
try:
    from base_node_rpc.proxy import ConfigMixinBase, StateMixinBase
    from .node import (Proxy as _Proxy, I2cProxy as _I2cProxy,
                       SerialProxy as _SerialProxy)
    from .config import Config
    from .state import State


    class ConfigMixin(ConfigMixinBase):
        @property
        def config_class(self):
            return Config


    class StateMixin(StateMixinBase):
        @property
        def state_class(self):
            return State


    class ProxyMixin(ConfigMixin, StateMixin):
        '''
        Mixin class to add convenience wrappers around methods of the generated
        `node.Proxy` class.
        '''
        host_package_name = str(path(__file__).parent.name.replace('_', '-'))

        def __init__(self, *args, **kwargs):
            super(ProxyMixin, self).__init__(*args, **kwargs)
            # embeded version isn't working with teensy. Use this for now:
            self.initialize_switching_boards()

        def __del__(self):
            # turn off the high voltage when we disconnect
            self.hv_output_enabled = False

        def get_environment_state(self, i2c_address=0x27):
                    '''
                    Acquire temperature and humidity from Honeywell HIH6000 series
                    sensor.

                    [1]: http://sensing.honeywell.com/index.php/ci_id/142171/la_id/1/document/1/re_id/0
                    '''
                    import pandas as pd

                    # Trigger measurement.
                    self.i2c_write(i2c_address, [])
                    time.sleep(.01)

                    while True:
                        # Read 4 bytes from sensor.
                        humidity_data, temperature_data = self.i2c_read(i2c_address,
                                                                        4).view('>u2')
                        status_code = (humidity_data >> 14) & 0x03
                        if status_code == 0:
                            # Measurement completed successfully.
                            break
                        elif status_code > 1:
                            raise IOError('Error reading from sensor.')
                        # Measurement data is stale (i.e., measurement still in
                        # progress).  Try again.
                        time.sleep(.001)

                    # See URL from docstring for source of equations.
                    relative_humidity = float(humidity_data & 0x03FFF) / ((1 << 14) - 2)
                    temperature_celsius = (float((temperature_data >> 2) & 0x3FFF) /
                                           ((1 << 14) - 2) * 165 - 40)

                    return pd.Series([relative_humidity, temperature_celsius],
                                     index=['relative_humidity',
                                            'temperature_celsius'])

        @property
        def magnet_engaged(self):
            return self.state['magnet_engaged']

        @magnet_engaged.setter
        def magnet_engaged(self, value):
            self.update_state(magnet_engaged=value)

        @property
        def light_intensity(self):
            return self.config['light_intensity']

        @light_intensity.setter
        def light_intensity(self, value):
            self.update_config(light_intensity=value)

        @property
        def light_enabled(self):
            return self.state['light_enabled']

        @light_enabled.setter
        def light_enabled(self, value):
            self.update_state(light_enabled=value)

        @property
        def frequency(self):
            return self.state['frequency']
        
        @frequency.setter
        def frequency(self, value):
            return self.update_state(frequency=value)

        @property
        def voltage(self):
            return self.state['voltage']

        @voltage.setter
        def voltage(self, value):
            return self.update_state(voltage=value)

        @property
        def hv_output_enabled(self):
            return self.state['hv_output_enabled']

        @hv_output_enabled.setter
        def hv_output_enabled(self, value):
            return self.update_state(hv_output_enabled=value)

        @property
        def hv_output_selected(self):
            return self.state['hv_output_selected']

        @hv_output_selected.setter
        def hv_output_selected(self, value):
            return self.update_state(hv_output_selected=value)

        def _state_of_channels(self):
            '''
            Prepend underscore to the auto-generated state_of_channels accessor
            '''
            return super(ProxyMixin, self).state_of_channels()

        def _set_state_of_channels(self, states):
            '''
            Prepend underscore to the auto-generated state_of_channels setter
            '''
            return super(ProxyMixin, self).set_state_of_channels(states)

        @property
        def state_of_channels(self):
            '''
            Retrieve the state bytes from the device and unpacks them into an
            array with one entry per channel.  Return unpacked array.

            Notes
            -----

            State of each channel is binary, 0 or 1.  On device, states are
            stored in bytes, where each byte corresponds to the state of eight
            channels.
            '''
            import numpy as np

            return np.unpackbits(super(ProxyMixin, self).state_of_channels()[::-1])[::-1]

        @state_of_channels.setter
        def state_of_channels(self, states):
            self.set_state_of_channels(states)

        def set_state_of_channels(self, states):
            '''
            Pack array containing one entry per channel to bytes (8 channels
            per byte).  Set state of channels on device using state bytes.

            See also: `state_of_channels` (get)
            '''
            import numpy as np
            
            ok = (super(ProxyMixin, self)
                    .set_state_of_channels(np.packbits(states.astype(int)[::-1])[::-1]))
            if not ok:
                raise ValueError('Error setting state of channels.  Check '
                                 'number of states matches channel count.')
                
        @property
        def baud_rate(self):
            return self.config['baud_rate']

        @baud_rate.setter
        def baud_rate(self, baud_rate):
            return self.update_config(baud_rate=baud_rate)

        @property
        def serial_number(self):
            return self.config['serial_number']

        @serial_number.setter
        def serial_number(self, serial_number):
            return self.update_config(serial_number=serial_number)
        
        @property
        def port(self):
            return self._stream.serial_device.port

        @port.setter
        def port(self, port):
            return self.update_config(port=port)
        
        def _number_of_channels(self):
            return super(ProxyMixin, self).number_of_channels()
        
        @property
        def number_of_channels(self):
            return self._number_of_channels()

        @number_of_channels.setter
        def number_of_channels(self, number_of_channels):
            return self.set_number_of_channels(number_of_channels)

        def _hardware_version(self):
            return super(ProxyMixin, self).hardware_version()

        @property
        def hardware_version(self):
            return self._hardware_version().tostring()

        @property
        def min_waveform_frequency(self):
            return super(ProxyMixin, self).min_waveform_frequency()

        @property
        def max_waveform_frequency(self):
            return super(ProxyMixin, self).max_waveform_frequency()

        @property
        def max_waveform_voltage(self):
            return super(ProxyMixin, self).max_waveform_voltage()

        def initialize_switching_boards(self):
            """
            Embeded version of this function is not detecting switching boards properly. Use this for now...
            """
            PCA9505_CONFIG_IO_REGISTER = 0x18
            PCA9505_OUTPUT_PORT_REGISTER = 0x08

            # Check how many switching boards are connected.  Each additional board's
            # address must equal the previous boards address +1 to be valid.
            number_of_channels = 0

            try:
                for chip in range(8):
                    # set IO ports as inputs
                    buffer = [PCA9505_CONFIG_IO_REGISTER, 0xFF]
                    self.i2c_write(self.config['switching_board_i2c_address'] + chip, buffer)

                    # read back the register value
                    # if it matches what we previously set, this might be a PCA9505 chip
                    if self.i2c_read(self.config['switching_board_i2c_address'] + chip, 1)[0] == 0xFF:
                        # try setting all ports in output mode and initialize to ground
                        port = 0
                        for port in range(5):
                            buffer = [PCA9505_CONFIG_IO_REGISTER + port, 0x00]
                            self.i2c_write(self.config['switching_board_i2c_address'] + chip, buffer)

                            # check that we successfully set the IO config register to 0x00
                            if self.i2c_read(self.config['switching_board_i2c_address'] + chip, 1)[0] != 0x00:
                                return

                            buffer = [PCA9505_OUTPUT_PORT_REGISTER + port, 0xFF]
                            self.i2c_write(self.config['switching_board_i2c_address'] + chip, buffer)

                            # if port=4, it means that we successfully initialized all IO config
                            # registers to 0x00, and this is probably a PCA9505 chip
                            if port == 4:
                                if number_of_channels == 40 * chip:
                                    number_of_channels = 40 * (chip + 1)
                    self.number_of_channels = number_of_channels
            except:
                pass

    class Proxy(ProxyMixin, _Proxy):
        pass

    class I2cProxy(ProxyMixin, _I2cProxy):
        pass

    class SerialProxy(ProxyMixin, _SerialProxy):
        pass

except (ImportError, TypeError):
    Proxy = None
    I2cProxy = None
    SerialProxy = None