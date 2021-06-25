import asyncio
import random
from asyncio.events import AbstractEventLoop

MAX_DATAGRAM_LIMIT: int = 10000
SLEEP_TIME: float = 0.000002
SERVER_SERVE_TIME: int = 120
FAILURE_THRESHOLD: float = 0.01


class EchoServerProtocol(asyncio.DatagramProtocol):
    # noinspection PyTypeChecker
    def __init__(self, loop):
        self.transport: asyncio.DatagramTransport = None
        self.last_message_acknowledged: int = 0
        self.loop: AbstractEventLoop = loop

    def connection_made(self, transport):
        self.transport = transport
        print('INFO: Server connection made', transport.get_extra_info("peername"))
        print('INFO: Server connection made function complete')

    def datagram_received(self, data, addr):
        print("INFO: Client data received:", data.decode(), 'from', str(addr))
        probability = random.random()
        message = int(data.decode())
        if probability >= FAILURE_THRESHOLD:
            if message > self.last_message_acknowledged:
                print('INFO: Server updating acknowledgement', message)
                self.last_message_acknowledged = message
            asyncio.ensure_future(self.transmit_segment(addr), loop=self.loop)
        else:
            print('INFO: Server skipping acknowledgement for', data.decode())
        print('INFO: Server datagram received function complete')

    async def transmit_segment(self, addr):
        print('INFO: Server sending acknowledgement for', self.last_message_acknowledged)
        self.transport.sendto(str(self.last_message_acknowledged).encode(), addr)
        await asyncio.sleep(SLEEP_TIME)
        print('INFO: Server transmit segment function complete')

    def error_received(self, exc):
        print('INFO: Server error received:', exc)

    def connection_lost(self, exc):
        print("INFO: Server connection closed", exc)


async def main():
    print("INFO: Starting UDP server")
    # Get a reference to the event loop as we plan to use
    # low-level APIs.
    loop = asyncio.get_running_loop()
    # One protocol instance will be created to serve all
    # client requests.
    transport, protocol = await loop.create_datagram_endpoint(lambda: EchoServerProtocol(loop), local_addr=('127.0.0.1', 9999))

    try:
        await asyncio.sleep(SERVER_SERVE_TIME)
    finally:
        transport.close()


asyncio.run(main())
