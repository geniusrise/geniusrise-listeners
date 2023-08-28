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

import json
import boto3
from geniusrise import Spout, State, StreamingOutput
from typing import Optional


class Kinesis(Spout):
    def __init__(self, output: StreamingOutput, state: State, **kwargs):
        r"""
        Initialize the Kinesis class.

        Args:
            output (StreamingOutput): An instance of the StreamingOutput class for saving the data.
            state (State): An instance of the State class for maintaining the state.
            **kwargs: Additional keyword arguments.

        ## Using geniusrise to invoke via command line
        ```bash
        genius Kinesis rise \
            streaming \
                --output_kafka_topic kinesis_test \
                --output_kafka_cluster_connection_string localhost:9094 \
            postgres \
                --postgres_host 127.0.0.1 \
                --postgres_port 5432 \
                --postgres_user postgres \
                --postgres_password postgres \
                --postgres_database geniusrise \
                --postgres_table state \
            listen \
                --args stream_name=my_stream shard_id=shardId-000000000000
        ```

        ## Using geniusrise to invoke via YAML file
        ```yaml
        version: "1"
        spouts:
            my_kinesis_spout:
                name: "Kinesis"
                method: "listen"
                args:
                    stream_name: "my_stream"
                    shard_id: "shardId-000000000000"
                output:
                    type: "streaming"
                    args:
                        output_topic: "kinesis_test"
                        kafka_servers: "localhost:9094"
                state:
                    type: "postgres"
                    args:
                        postgres_host: "127.0.0.1"
                        postgres_port: 5432
                        postgres_user: "postgres"
                        postgres_password: "postgres"
                        postgres_database: "geniusrise"
                        postgres_table: "state"
                deploy:
                    type: "k8s"
                    args:
                        name: "my_kinesis_spout"
                        namespace: "default"
                        image: "my_kinesis_spout_image"
                        replicas: 1
        ```
        """
        super().__init__(output, state)
        self.top_level_arguments = kwargs
        self.kinesis = boto3.client("kinesis")

    def listen(
        self,
        stream_name: str,
        shard_id: str = "shardId-000000000000",
        region_name: Optional[str] = None,
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
    ):
        """
        📖 Start listening for data from the Kinesis stream.

        Args:
            stream_name (str): The name of the Kinesis stream.
            shard_id (str, optional): The shard ID to read from. Defaults to "shardId-000000000000".
            region_name (str, optional): The AWS region name.
            aws_access_key_id (str, optional): AWS access key ID for authentication.
            aws_secret_access_key (str, optional): AWS secret access key for authentication.

        Raises:
            Exception: If there is an error while processing Kinesis records.
        """
        if region_name:
            self.kinesis = boto3.client("kinesis", region_name=region_name)
        if aws_access_key_id and aws_secret_access_key:
            self.kinesis = boto3.client(
                "kinesis",
                aws_access_key_id=aws_access_key_id,
                aws_secret_access_key=aws_secret_access_key,
                region_name=region_name,
            )

        shard_iterator = self.kinesis.get_shard_iterator(
            StreamName=stream_name, ShardId=shard_id, ShardIteratorType="LATEST"
        )["ShardIterator"]

        while True:
            try:
                response = self.kinesis.get_records(ShardIterator=shard_iterator, Limit=100)

                for record in response["Records"]:
                    data = json.loads(record["Data"])

                    # Enrich the data with metadata about the sequence number
                    enriched_data = {
                        "data": data,
                        "sequence_number": record["SequenceNumber"],
                    }

                    # Use the output's save method
                    self.output.save(enriched_data)

                    # Update the state using the state
                    current_state = self.state.get_state(self.id) or {
                        "success_count": 0,
                        "failure_count": 0,
                    }
                    current_state["success_count"] += 1
                    self.state.set_state(self.id, current_state)

                shard_iterator = response["NextShardIterator"]

            except Exception as e:
                self.log.error(f"Error processing Kinesis record: {e}")

                # Update the state using the state
                current_state = self.state.get_state(self.id) or {
                    "success_count": 0,
                    "failure_count": 0,
                }
                current_state["failure_count"] += 1
                self.state.set_state(self.id, current_state)
