import os
import time

import arrow
import serial
import yaml

__version__ = '1.0'
__author__ = 'Francesco Milani'


class ActuatorManager:
    conn = None
    log_path = None

    def __init__(self) -> None:
        try:
            config = self._get_config()
            file_name = "actuator_{}.log".format(
                arrow.now().format(config['DATE_FORMAT'])
            )
            self.log_path = os.path.join('logs', file_name)
            self.SERIAL_PORT = config['SERIAL_PORT']
            self.CHECK_INTERVAL = config['CHECK_INTERVAL']
            self.DATETIME_FORMAT = config['DATETIME_FORMAT']
            self.COLLECTION_TIME_DEFAULT = config['COLLECTION_TIME_DEFAULT']
            self.CONFIG = config.get('optional', {})
        except KeyError as e:
            print(f'ERROR: Missing required configuration {e} from config.yaml')
            exit(-1)
        except FileNotFoundError:
            print('ERROR: Cannot find config.yaml')
            exit(-1)

    @staticmethod
    def _get_config() -> dict:
        with open("config.yaml", "r") as f:
            return yaml.load(f, Loader=yaml.FullLoader)

    def _wait_until(self, end: arrow.arrow) -> None:
        while arrow.now() < end:
            time.sleep(self.CHECK_INTERVAL)

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
        conn.write(f'GO{pos}\r\n')

    def _get_wait_and_wait_delta(self, pos: int, now: arrow.arrow):
        shift = self.CONFIG.get(
            f'COLLECTION_TIME_POS_{pos}',
            self.COLLECTION_TIME_DEFAULT
        )
        wait = now.shift(minutes=+shift)
        return wait, wait - now

    def _change_position_and_wait(self) -> None:
        for pos in range(1, 11):
            now = arrow.now()
            self._set_position(pos)
            wait, wait_delta = self._get_wait_and_wait_delta(pos, now)

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
            print(message)
            self._log_message(message)
            while True:
                self._change_position_and_wait()

        except (KeyboardInterrupt, SystemExit):
            if self.conn and self.conn.isOpen():
                self.conn.close()
            message = 'Exiting: ' + arrow.now().format(self.DATETIME_FORMAT)
            print(message)
            self._log_message(message)
            exit(0)


if __name__ == '__main__':
    ActuatorManager().run()
