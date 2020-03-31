from os.path import join
from pathlib import Path
from time import sleep

import arrow
import serial
import yaml

__version__ = '1.1'
__author__ = 'Francesco Milani'


class ActuatorPositionSwitcher:
    conn = None
    log_path = None

    def __init__(self) -> None:
        try:
            config = self._get_config()
            self._prepare_log_folder()
            file_name = "actuator_{}.log".format(
                arrow.now().format(config['DATE_FORMAT'])
            )
            self.log_path = join('logs', file_name)
            self.SERIAL_PORT = config['SERIAL_PORT']
            self.CHECK_INTERVAL = config['CHECK_INTERVAL']
            self.DATETIME_FORMAT = config['DATETIME_FORMAT']
            self.COLLECTION_TIME_DEFAULT = config['COLLECTION_TIME_DEFAULT']
            self.NUMBER_OF_CYCLES = config['NUMBER_OF_CYCLES']
            self.STARTING_POSITION = config['STARTING_POSITION']
            self.CONFIG = config.get('optional', {})

        except KeyError as e:
            self._handle_exception(f'ERROR: Missing required configuration {e} from config.yaml')
        except FileNotFoundError:
            self._handle_exception('ERROR: Cannot find config.yaml')

    @staticmethod
    def _handle_exception(message):
        print(message)
        input('press ENTER to exit')
        exit(-1)

    @staticmethod
    def _prepare_log_folder():
        Path('logs').mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _get_config() -> dict:
        with open("config.yaml", "r") as f:
            return yaml.load(f, Loader=yaml.FullLoader)

    def _wait_until(self, end: arrow.arrow) -> None:
        while arrow.now() < end:
            sleep(self.CHECK_INTERVAL)

    def _log_message(self, message: str) -> None:
        with open(self.log_path, 'a') as f:
            f.write(message + '\n')

    def _get_conn(self) -> serial.Serial:
        if not (self.conn and self.conn.isOpen()):
            self.conn = serial.Serial(
                port=self.SERIAL_PORT,
                baudrate=9600,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                bytesize=serial.EIGHTBITS
            )

        return self.conn

    def _set_position(self, pos: int) -> None:
        conn = self._get_conn()
        conn.write(f'GO{pos}\r\n'.encode('utf-8'))

    def _get_wait_and_wait_delta(self, pos: int, now: arrow.arrow, cycle: int):
        key = f'CYCLE_{cycle}' if f'CYCLE_{cycle}' in self.CONFIG else 'CYCLE_ALL'
        cycle_config = self.CONFIG.get(key, {})

        shift = cycle_config.get(
            f'COLLECTION_TIME_POS_{pos}',
            self.COLLECTION_TIME_DEFAULT
        )

        wait = now.shift(minutes=+shift)
        return wait, wait - now

    def _change_position_and_wait(self, cycle: int) -> None:
        start = self.STARTING_POSITION if cycle == 1 else 1
        for pos in range(start, 11):
            now = arrow.now()
            self._set_position(pos)
            wait, wait_delta = self._get_wait_and_wait_delta(pos, now, cycle)

            message = "- {0}: set position: {1} | collection time: {2}".format(
                now.format(self.DATETIME_FORMAT),
                pos,
                wait_delta
            )

            print(message)
            self._log_message(message)
            self._wait_until(wait)

    def run(self) -> None:
        try:
            message = 'Starting: ' + arrow.now().format(self.DATETIME_FORMAT)
            print('Press CTRL+C to safely halt the script.\n')
            print(message)
            self._log_message(message)
            cycle = 1
            while True:
                if self.NUMBER_OF_CYCLES and cycle > self.NUMBER_OF_CYCLES:
                    break

                self._change_position_and_wait(cycle)
                cycle += 1

        except (KeyboardInterrupt, SystemExit):
            if self.conn and self.conn.isOpen():
                self.conn.close()
            message = 'Exiting: ' + arrow.now().format(self.DATETIME_FORMAT)
            print(message)
            self._log_message(message)
            input('\nScript halted. Press ENTER to exit.')
            exit(0)


if __name__ == '__main__':
    ActuatorPositionSwitcher().run()
