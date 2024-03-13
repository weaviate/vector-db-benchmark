# vector-db-benchmark

### Weaviate Benchmark Reproduction

We reran the benchmark with the same dataset `dbpedia-openai-1M-1536-angular` on same Azure hardware as published:
 
> - Client: 8 vcpus, 16 GiB memory, 64GiB storage (`Standard D8ls v5` on Azure Cloud)
> - Server: 8 vcpus, 32 GiB memory, 64GiB storage (`Standard D8s v3` on Azure Cloud)

Because both vector databases primarily rely on the HNSW algorithm for the vector index, we had a simple goal with this repeat benchmark: Let’s test HNSW performance with as similar parameters as possible.

So instead of creating a comparison with different build parameters (such as on the benchmark site where Qdrant has `efConstruction=512` while Weaviate has `efConstruction=256`) we selected the same build parameters:

- `efConstruction=512` (how deep the graph is searched when indexing a vector)
- `maxConnections=32` (how many edges the graph has on upper levels)

We didn’t use quantization for the following reasons:

- Quantization is impacted heavily by disk caching for performance due to on disk rescoring. This creates large variability especially with the original experiments like `qdrant-sq-rps-m-64-ef-256` that rerun the same queries at different parallel settings.
- We wanted to test base HNSW performance, which is the default algorithm in both databases.

### Results

### Import performance

Database | Configuration | Dataset | Total index time
-- | -- | -- | --
Weaviate | weaviate-1.24.1-m32-efc256 | dbpedia-openai-1M-1536-angular | 20m46s
Qdrant | qdrant-1.8.1-m32-efc256 | dbpedia-openai-1M-1536-angular | 32m02s


Weaviate has <em><strong>37% less total index time</strong></em> for the same HNSW configuration.

Note the benchmark waits until the Qdrant collection is green and HNSW indices merged. Weaviate has an optional async indexing feature that provides similar fast upload times.

### Query performance

![image](https://github.com/qdrant/vector-db-benchmark/assets/2173919/1ee71392-b265-42da-bb9d-8ce1ddfac0d3)

The above graph shows the standard rps/precision curve built by varying the search time `ef` parameter. 

Weaviate is significantly faster 🚀 around the 99% precision target with Weaviate RPS 1225 at 98.9% precision vs Qdrant RPS 471 at 99.0%.

We found the python testing framework on a single instance could not always stress the engine for maximum queries per second (causing the flattened query performance at low `ef`) but agree with the proposal that the majority of users will use a python client.

## Experiment configuration

```json

[{
 "name": "weaviate-1.24.1-m32-efc256",
 "engine": "weaviate",
 "connection_params": {
   "timeout_config": 60
 },
 "collection_params": {
	 "vectorIndexConfig": {
		 "efConstruction": 256,
		 "maxConnections": 32
	 }
 },
 "search_params": [
   { "parallel": 100, "vectorIndexConfig": { "ef": 16} },
   { "parallel": 100, "vectorIndexConfig": { "ef": 32} },
   { "parallel": 100, "vectorIndexConfig": { "ef": 64} },
   { "parallel": 100, "vectorIndexConfig": { "ef": 128} },
   { "parallel": 100, "vectorIndexConfig": { "ef": 256} },
   { "parallel": 100, "vectorIndexConfig": { "ef": 512} },
   { "parallel": 100, "vectorIndexConfig": { "ef": 768} }
 ],
 "upload_params": { "parallel": 8, "batch_size": 1024 }
},
{
  "name": "qdrant-1.8.1-m32-efc256",
  "engine": "qdrant",
  "connection_params": { "timeout": 60 },
  "collection_params": {
    "optimizers_config": { "memmap_threshold":10000000 },
    "hnsw_config": { "m": 32, "ef_construct": 256 }
  },
  "search_params": [
    { "parallel": 100, "search_params": { "hnsw_ef": 16 } },
    { "parallel": 100, "search_params": { "hnsw_ef": 32 } },
    { "parallel": 100, "search_params": { "hnsw_ef": 64 } },
    { "parallel": 100, "search_params": { "hnsw_ef": 128 } },
    { "parallel": 100, "search_params": { "hnsw_ef": 256 } },
    { "parallel": 100, "search_params": { "hnsw_ef": 512 } },
    { "parallel": 100, "search_params": { "hnsw_ef": 768 } }
  ],
  "upload_params": { "parallel": 8, "batch_size": 1024 }
}]
```

### Things we changed

- Updated Weaviate python client to latest v4 version. This has [numerous performance improvements](https://weaviate.io/blog/grpc-performance-improvements) including adding gRPC support.
- Updated Weaviate to newer [1.24.1 image](https://weaviate.io/blog/weaviate-1-24-release).

Along the way we also fixed isssues in the benchmark including

- Set Weaviate docker config to use the same host’s networking stack as with Qdrant
- Removed unnecessary GC settings
- Improved Weaviate configuration settings in general

# Original README

There are various vector search engines available, and each of them may offer
a different set of features and efficiency. But how do we measure the
performance? There is no clear definition and in a specific case you
may worry about a specific thing, while not paying much attention to other aspects. This
project is a general framework for benchmarking different engines under the
same hardware constraints, so you can choose what works best for you.

Running any benchmark requires choosing an engine, a dataset and defining the
scenario against which it should be tested. A specific scenario may assume
running the server in a single or distributed mode, a different client
implementation and the number of client instances.

## How to run a benchmark?

Benchmarks are implemented in server-client mode, meaning that the server is
running in a single machine, and the client is running on another.

### Run the server

All engines are served using docker compose. The configuration is in the [servers](./engine/servers/).

To launch the server instance, run the following command:

```bash
cd ./engine/servers/<engine-configuration-name>
docker compose up
```

Containers are expected to expose all necessary ports, so the client can connect to them.

### Run the client

Install dependencies:

```bash
pip install poetry
poetry install
```

Run the benchmark:

```bash
Usage: run.py [OPTIONS]

  Example: python3 -m run --engines *-m-16-* --datasets glove-*

Options:
  --engines TEXT                  [default: *]
  --datasets TEXT                 [default: *]
  --host TEXT                     [default: localhost]
  --skip-upload / --no-skip-upload
                                  [default: no-skip-upload]
  --install-completion            Install completion for the current shell.
  --show-completion               Show completion for the current shell, to
                                  copy it or customize the installation.
  --help                          Show this message and exit.
```

Command allows you to specify wildcards for engines and datasets.
Results of the benchmarks are stored in the `./results/` directory.

## How to update benchmark parameters?

Each engine has a configuration file, which is used to define the parameters for the benchmark.
Configuration files are located in the [configuration](./experiments/configurations/) directory.

Each step in the benchmark process is using a dedicated configuration's path:

* `connection_params` - passed to the client during the connection phase.
* `collection_params` - parameters, used to create the collection, indexing parameters are usually defined here.
* `upload_params` - parameters, used to upload the data to the server.
* `search_params` - passed to the client during the search phase. Framework allows multiple search configurations for the same experiment run.

Exact values of the parameters are individual for each engine.

## How to register a dataset?

Datasets are configured in the [datasets/datasets.json](./datasets/datasets.json) file.
Framework will automatically download the dataset and store it in the [datasets](./datasets/) directory.

## How to implement a new engine?

There are a few base classes that you can use to implement a new engine.

* `BaseConfigurator` - defines methods to create collections, setup indexing parameters.
* `BaseUploader` - defines methods to upload the data to the server.
* `BaseSearcher` - defines methods to search the data.

See the examples in the [clients](./engine/clients) directory.

Once all the necessary classes are implemented, you can register the engine in the [ClientFactory](./engine/clients/client_factory.py).

