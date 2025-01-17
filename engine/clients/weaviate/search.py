import uuid
from typing import List, Tuple

from weaviate import WeaviateClient
from weaviate.collections import Collection
from weaviate.connect import ConnectionParams
from weaviate.classes.query import MetadataQuery
from weaviate.classes.config import Reconfigure

from engine.base_client.search import BaseSearcher
from engine.clients.weaviate.config import WEAVIATE_CLASS_NAME, WEAVIATE_DEFAULT_PORT
from engine.clients.weaviate.parser import WeaviateConditionParser


class WeaviateSearcher(BaseSearcher):
    search_params = {}
    parser = WeaviateConditionParser()
    collection: Collection
    client: WeaviateClient

    @classmethod
    def init_client(cls, host, distance, connection_params: dict, search_params: dict):
        url = f"http://{host}:{connection_params.get('port', WEAVIATE_DEFAULT_PORT)}"
        client = WeaviateClient(
            ConnectionParams.from_url(url, 50051), skip_init_checks=True
        )
        client.connect()
        cls.collection = client.collections.get(
            WEAVIATE_CLASS_NAME, skip_argument_validation=True
        )
        cls.search_params = search_params
        cls.client = client

    @classmethod
    def search_one(self, vector, meta_conditions, top) -> List[Tuple[int, float]]:
        res = self.collection.query.near_vector(
            near_vector=vector,
            filters=self.parser.parse(meta_conditions),
            limit=top,
            return_metadata=MetadataQuery(distance=True),
            return_properties=[],
        )
        return [(hit.uuid.int, hit.metadata.distance) for hit in res.objects]

    def setup_search(self):
        self.collection.config.update(
            vector_index_config=Reconfigure.VectorIndex.hnsw(
                ef=self.search_params["vectorIndexConfig"]["ef"]
            )
        )

    @classmethod
    def delete_client(cls):
        if cls.client is not None:
            cls.client.close()
