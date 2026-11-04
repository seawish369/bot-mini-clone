import itertools
import threading
from types import SimpleNamespace


class FakeOpenAI:
    def __init__(self, api_key: str = "sk-test"):
        self.stores: dict[str, SimpleNamespace] = {}
        self.uploaded: dict[str, tuple[str, str]] = {}
        self.items: dict[str, SimpleNamespace] = {}
        self.fail_parts: set[int] = set()
        self.lock = threading.Lock()
        self.ids = itertools.count(1)
        self.files = FakeFiles(self)
        self.vector_stores = FakeVectorStores(self)

    def next_id(self, prefix: str) -> str:
        with self.lock:
            return f"{prefix}-{next(self.ids)}"


class FakeFiles:
    def __init__(self, client: FakeOpenAI):
        self.client = client

    def create(self, file, purpose):
        name, content = file
        file_id = self.client.next_id("file")
        self.client.uploaded[file_id] = (name, content.decode("utf-8"))
        return SimpleNamespace(id=file_id)

    def delete(self, file_id):
        self.client.uploaded.pop(file_id, None)


class FakeVectorStores:
    def __init__(self, client: FakeOpenAI):
        self.client = client
        self.files = FakeVectorStoreFiles(client)

    def list(self, limit=100):
        return list(self.client.stores.values())

    def create(self, name, chunking_strategy):
        store = SimpleNamespace(id=self.client.next_id("vs"), name=name, chunking_strategy=chunking_strategy)
        self.client.stores[store.id] = store
        return store


class FakeVectorStoreFiles:
    def __init__(self, client: FakeOpenAI):
        self.client = client

    def create_and_poll(self, file_id, vector_store_id, chunking_strategy, attributes):
        status = "failed" if attributes["part"] in self.client.fail_parts else "completed"
        item = SimpleNamespace(id=file_id, status=status, attributes=dict(attributes), last_error=None)
        with self.client.lock:
            self.client.items[file_id] = item
        return item

    def list(self, vector_store_id, limit=100):
        return list(self.client.items.values())

    def delete(self, file_id, vector_store_id):
        self.client.items.pop(file_id)
