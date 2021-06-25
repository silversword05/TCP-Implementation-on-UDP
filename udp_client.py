import asyncio
from asyncio.events import AbstractEventLoop
from asyncio.futures import Future
from typing import Any
from functools import partial

MSS = 1
INITIAL_CWND: int = 1
INITIAL_SSTHRESH: int = 64
MAX_DATAGRAM_LIMIT = 10000
TIMEOUT = 0.002
SLEEP_TIME = 0.000002
STATE_DICT = {0: 'Slow Start', 1: 'Congestion Avoidance', 2: 'Fast Recovery'}


class EchoClientProtocol(asyncio.DatagramProtocol):
    # noinspection PyTypeChecker
    def __init__(self, on_con_lost, loop, f_out):
        self.on_con_lost: Future[Any] = on_con_lost
        self.loop: AbstractEventLoop = loop
        self.transport: asyncio.DatagramTransport = None
        self.timeout_callback_handle: asyncio.TimerHandle = None
        self.current_state: int = -1
        self.last_message_sent: int = 0
        self.last_message_acknowledged: int = 0
        self.ssthresh: int = INITIAL_SSTHRESH
        self.cwnd: float = INITIAL_CWND
        self.duplicate_acknowledgement_count: int = 0
        self.f_out = f_out

    def connection_made(self, transport: asyncio.DatagramTransport):
        self.transport = transport
        self.current_state = 0
        print('INFO: Client connection made', transport.get_extra_info("peername"))
        self.last_message_sent += 1
        print('INFO: Client sending first data', self.last_message_sent)
        asyncio.ensure_future(self.transmit_segment(), loop=self.loop)
        timeout_callback_function = partial(self.timeout_callback_function, message_for=self.last_message_sent)
        self.timeout_callback_handle = self.loop.call_later(delay=TIMEOUT, callback=timeout_callback_function)
        print('INFO: Client connection made function complete')

    def timeout_callback_function(self, message_for: int):
        if not self.timeout_callback_handle.cancelled():
            print('INFO: Client timeout callback handle cancelled')
            self.timeout_callback_handle.cancel()
        if message_for <= self.last_message_acknowledged:
            print('INFO: Invalid timeout in client')
            asyncio.ensure_future(self.transmit_segments(), loop=self.loop)
            return
        print('INFO: Client timeout for message', message_for)
        print('INFO: Client in state', STATE_DICT[self.current_state])
        self.ssthresh = max(int(self.cwnd / 2.0), 1)
        self.cwnd = INITIAL_CWND
        self.duplicate_acknowledgement_count = 0
        asyncio.ensure_future(self.transmit_segment(), loop=self.loop)
        self.current_state = 0
        print('INFO: Client timeout callback function complete')

    async def transmit_segment(self):
        print('INFO: Client sending message', self.last_message_acknowledged + 1)
        self.f_out.write(f'INFO: {str(self.loop.time())} transmit segment cwnd {round(self.cwnd, 2)} ssthresh {self.ssthresh} \n')
        self.transport.sendto(str(self.last_message_acknowledged + 1).encode())
        await asyncio.sleep(SLEEP_TIME)
        print('INFO: Client transmit segment function complete')

    async def transmit_segments(self):
        print('INFO: Client sending message', self.last_message_sent, 'acknowledgement', self.last_message_acknowledged)
        self.f_out.write(f'INFO: {str(self.loop.time())} transmit segments cwnd {round(self.cwnd, 2)} ssthresh {self.ssthresh} \n')
        while self.last_message_sent - self.last_message_acknowledged < self.cwnd:
            self.last_message_sent += 1
            print('INFO: Client sending data', self.last_message_sent)
            self.transport.sendto(str(self.last_message_sent).encode())
            await asyncio.sleep(SLEEP_TIME)
        timeout_callback_function = partial(self.timeout_callback_function, message_for=self.last_message_sent)
        self.timeout_callback_handle = self.loop.call_later(delay=TIMEOUT, callback=timeout_callback_function)
        print('INFO: Client transmit segments function complete')

    def datagram_received(self, data, addr):
        print("INFO: Client data received:", data.decode(), 'from', str(addr))
        acknowledgement_number: int = int(data.decode())
        if not self.timeout_callback_handle.cancelled():
            print('INFO: Client timeout callback handle cancelled')
            self.timeout_callback_handle.cancel()
        if self.last_message_sent > MAX_DATAGRAM_LIMIT:
            print('INFO: Client last datagram sent', self.last_message_sent, 'datagram acknowledged', self.last_message_acknowledged)
            print('INFO: All data sent successfully, closing connection')
            self.transport.close()
            print('INFO: Client connection closed successfully')
            return
        if acknowledgement_number < self.last_message_acknowledged:
            print('INFO: Client received invalid acknowledgement number', acknowledgement_number)
        elif acknowledgement_number > self.last_message_acknowledged:  # New acknowledgement
            print('INFO: Client in state', STATE_DICT[self.current_state], 'New acknowledgement received', acknowledgement_number)
            self.last_message_acknowledged = acknowledgement_number
            if self.current_state == 0:
                self.cwnd += MSS
                self.duplicate_acknowledgement_count = 0
                asyncio.ensure_future(self.transmit_segments(), loop=self.loop)
                if self.cwnd >= self.ssthresh:
                    self.current_state = 1
            elif self.current_state == 1:
                self.cwnd += MSS * (MSS * 1.0 / self.cwnd)
                self.duplicate_acknowledgement_count = 0
                asyncio.ensure_future(self.transmit_segments(), loop=self.loop)
            else:
                self.current_state = 1
                self.cwnd = self.ssthresh
                self.duplicate_acknowledgement_count = 0
            print('INFO: Client in state', STATE_DICT[self.current_state])
        else:  # Duplicate acknowledgement
            print('INFO: Client in state', STATE_DICT[self.current_state], 'Duplicate acknowledgement received', acknowledgement_number)
            if self.current_state == 2:
                self.cwnd += MSS
                asyncio.ensure_future(self.transmit_segments(), loop=self.loop)
            else:
                self.duplicate_acknowledgement_count += 1
                asyncio.ensure_future(self.transmit_segments(), loop=self.loop)
            if self.duplicate_acknowledgement_count == 3:
                print('INFO: Client received 3 duplicate acknowledgements ssthresh', self.ssthresh, 'cwnd', self.cwnd)
                self.current_state = 2
                self.ssthresh = max(int(self.cwnd / 2.0), 1)
                self.cwnd = self.ssthresh + 3 * MSS
                asyncio.ensure_future(self.transmit_segment(), loop=self.loop)
            print('INFO: Client in state', STATE_DICT[self.current_state])
        print('INFO: Client datagram received function complete')

    def error_received(self, exc):
        print('INFO: Client error received:', exc)

    def connection_lost(self, exc):
        print("INFO: Client connection closed", exc)
        self.on_con_lost.set_result(True)


async def main():
    print("INFO: Starting UDP client")
    # Get a reference to the event loop as we plan to use
    # low-level APIs.

    f_out = open('cwnd_data.log', 'w')
    loop: AbstractEventLoop = asyncio.get_running_loop()
    on_con_lost: Future[Any] = loop.create_future()
    transport, protocol = await loop.create_datagram_endpoint(lambda: EchoClientProtocol(on_con_lost, loop, f_out), remote_addr=('127.0.0.1', 9999))

    try:
        await on_con_lost
    finally:
        transport.close()
    await asyncio.sleep(2)
    print('INFO: Client closing data file')
    f_out.close()


asyncio.run(main())
