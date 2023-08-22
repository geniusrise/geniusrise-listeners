# 🧠 Geniusrise
# Copyright (C) 2023  geniusrise.ai
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import asyncio
from typing import Optional

import redis  # type: ignore
from geniusrise import Spout, State, StreamingOutput


class RedisStream(Spout):
    def __init__(self, output: StreamingOutput, state: State, **kwargs):
        super().__init__(output, state)
        self.top_level_arguments = kwargs

    async def _listen(
        self,
        stream_key: str,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        last_id: Optional[str] = None,
    ):
        """
        Start listening for data from the Redis stream.
        """
        try:
            self.log.info(f"Starting to listen to Redis stream {stream_key} on host {host}")

            self.redis = redis.StrictRedis(host=host, port=port, password=password, decode_responses=True, db=db)
            current_state = self.state.get_state(self.id) or {
                "success_count": 0,
                "failure_count": 0,
                "last_id": last_id,
            }
            last_id = (
                current_state["last_id"]
                if "last_id" in current_state and last_id is None and current_state["last_id"] is not None
                else "0"
                if last_id is None
                else last_id
            )

            while True:
                try:
                    # Use run_in_executor to run the synchronous redis call in a separate thread
                    result = await asyncio.get_event_loop().run_in_executor(
                        None, self.redis.xread, {stream_key: last_id, "count": 10, "block": 1000}
                    )

                    for _, messages in result:
                        for msg_id, fields in messages:
                            last_id = msg_id

                            # Enrich the data with metadata about the stream key and message ID
                            enriched_data = {
                                "data": fields,
                                "stream_key": stream_key,
                                "message_id": msg_id,
                            }

                            # Use the output's save method
                            self.output.save(enriched_data)

                            # Update the state using the state
                            current_state = self.state.get_state(self.id) or {
                                "success_count": 0,
                                "failure_count": 0,
                                "last_id": last_id,
                            }
                            current_state["success_count"] += 1
                            current_state["last_id"] = last_id
                            self.state.set_state(self.id, current_state)
                except Exception as e:
                    self.log.exception(f"Failed to process SNS message: {e}")
                    current_state["failure_count"] += 1
                    self.state.set_state(self.id, current_state)

                await asyncio.sleep(1)  # to prevent high CPU usage

        except Exception as e:
            self.log.error(f"Error processing Redis Stream message: {e}")

            # Update the state using the state
            current_state = self.state.get_state(self.id) or {
                "success_count": 0,
                "failure_count": 0,
                "last_id": last_id,
            }
            current_state["failure_count"] += 1
            self.state.set_state(self.id, current_state)

    def listen(
        self,
        stream_key: str,
        host: str = "localhost",
        port: int = 6379,
        db=0,
        password: Optional[str] = None,
    ):
        """
        Start the asyncio event loop to listen for data from the Redis stream.
        """
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self._listen(stream_key=stream_key, host=host, port=port, db=db, password=password))
