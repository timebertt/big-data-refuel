# Use Case: Analyzing fuel prices

## Prerequisites

A running Strimzi.io Kafka operator

```bash
helm repo add strimzi http://strimzi.io/charts/
helm install my-kafka-operator strimzi/strimzi-kafka-operator
kubectl apply -f https://farberg.de/talks/big-data/code/helm-kafka-operator/kafka-cluster-def.yaml
```

A running Hadoop cluster with YARN (for checkpointing)

```bash
helm repo add stable https://charts.helm.sh/stable
helm install --namespace=default --set hdfs.dataNode.replicas=1 --set yarn.nodeManager.replicas=1 --set hdfs.webhdfs.enabled=true my-hadoop-cluster stable/hadoop
```

## Deploy

To develop using [Skaffold](https://skaffold.dev/), use `skaffold dev` (development mode with automatic rebuilds on file changes) or `skaffold run` (one-time deploy).

### Download Job

We use a [Kubernetes Job](https://kubernetes.io/docs/concepts/workloads/controllers/job/) to fetch raw data from https://dev.azure.com/tankerkoenig/tankerkoenig-data/_git/tankerkoenig-data and store it in HDFS.
For performance reasons and disk space requirements it only downloads raw data for one month of 2021 (for now).

```
$ k exec my-hadoop-cluster-hadoop-hdfs-dn-0 -- hdfs dfs -ls "/input/*/*/*"
Found 19 items
-rw-r--r--   3 root supergroup   26716562 2021-11-20 09:30 /input/prices/2021/11/2021-11-01-prices.csv
-rw-r--r--   3 root supergroup   27371251 2021-11-20 09:30 /input/prices/2021/11/2021-11-02-prices.csv
...
Found 19 items
-rw-r--r--   3 root supergroup    4442792 2021-11-20 09:30 /input/stations/2021/11/2021-11-01-stations.csv
-rw-r--r--   3 root supergroup    4439113 2021-11-20 09:30 /input/stations/2021/11/2021-11-02-stations.csv
...

$ k exec my-hadoop-cluster-hadoop-hdfs-dn-0 -- hdfs dfs -du -h "/input"
490.8 M  /input/prices
80.5 M   /input/stations
```

### Spark App

Our Spark app will read the downloaded data from HDFS.
Connection details are configured in `core-site.xml` and `hdfs-site.xml` (file location is configured via `HADOOP_CONF_DIR` environment variable).
