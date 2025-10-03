import datetime
import io
import random
import time

import netapult.channel
import netapult.client


class BasicChannel(netapult.channel.Channel):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.output = io.BytesIO()
        self.read_offset: int = 0

    def connect(self):
        current_date: str = datetime.date.today().isoformat()
        self.output.seek(0, io.SEEK_END)
        self.output.write(b"Current time: " + current_date.encode() + b"\n")
        time.sleep(random.randrange(0, 5))
        self.output.seek(0, io.SEEK_END)
        self.output.write(b"localhost> ")

    def disconnect(self):
        self.output.close()

    def read(self, *args, **kwargs):
        self.output.seek(self.read_offset, io.SEEK_SET)
        content = self.output.read()
        self.read_offset += len(content)

        return content

    def write(self, payload: bytes, *args, **kwargs):
        self.output.write(payload)

        for _ in range(payload.count(b"\n")):
            self.output.write(b"localhost> ")


def test_basic_read_write():
    with netapult.client.Client(channel=BasicChannel(protocol_name="basic")) as client:
        prompt_found, prompt = client.find_prompt(read_timeout=10)
        assert b"localhost>" in prompt
