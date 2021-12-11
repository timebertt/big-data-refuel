# Use Case: Analyzing fuel prices

## Prerequisites

Namespace `refuel`:
```bash
k create ns refuel
```

A running Hadoop cluster with YARN:

```bash
helm repo add stable https://charts.helm.sh/stable
storage_class=default # replace with faster StorageClass if desired 
helm install --namespace=refuel --set hdfs.dataNode.replicas=1 \
  --set hdfs.webhdfs.enabled=true \
  --set yarn.nodeManager.replicas=3 \
  --set yarn.nodeManager.resources.requests.cpu=2,yarn.nodeManager.resources.requests.memory=4Gi \
  --set yarn.nodeManager.resources.limits.cpu=3,yarn.nodeManager.resources.limits.memory=6Gi \
  --set persistence.nameNode.enabled=true \
  --set persistence.nameNode.storageClass=$storage_class \
  --set persistence.nameNode.size=15Gi \
  --set persistence.dataNode.enabled=true \
  --set persistence.dataNode.storageClass=$storage_class \
  --set persistence.dataNode.size=50Gi \
  hadoop stable/hadoop
```

Note: `yarn.nodeManager.replicas` is the number of workers that can run spark jobs submitted to yarn.
When setting `yarn.nodeManager.resources.requests.{cpu,memory}`, consider the amount of compute resources available in your cluster,
e.g. a minikube cluster is limited by the size of your machine.

## Deploy

To develop using [Skaffold](https://skaffold.dev/), use `skaffold dev` (development mode with automatic rebuilds on file changes) or `skaffold run` (one-time deploy).

### Download CronJob

We use a [Kubernetes CronJob](https://kubernetes.io/docs/concepts/workloads/controllers/cron-jobs/) to fetch raw data from https://dev.azure.com/tankerkoenig/tankerkoenig-data/_git/tankerkoenig-data and store it in HDFS.
Each execution downloads data for one day starting with a configured start date (env var `DOWNLOAD_START_DATE`). It can be executed with a high frequency (e.g. every 2 minutes) to simulate new data arriving every day.

```
$ k exec hadoop-hadoop-hdfs-dn-0 -- hdfs dfs -ls "/input/*/*"
-rw-r--r--   3 root supergroup   26716562 2021-12-09 19:46 /input/prices/2021-11-01-prices.csv
-rw-r--r--   3 root supergroup   27371251 2021-12-09 19:46 /input/prices/2021-11-02-prices.csv
-rw-r--r--   3 root supergroup   27861891 2021-12-09 19:47 /input/prices/2021-11-03-prices.csv
-rw-r--r--   3 root supergroup   27217196 2021-12-09 19:47 /input/prices/2021-11-04-prices.csv
-rw-r--r--   3 root supergroup   27511444 2021-12-09 19:48 /input/prices/2021-11-05-prices.csv
-rw-r--r--   3 root supergroup   24953811 2021-12-09 19:48 /input/prices/2021-11-06-prices.csv
-rw-r--r--   3 root supergroup    4442792 2021-12-09 19:46 /input/stations/2021-11-01-stations.csv
-rw-r--r--   3 root supergroup    4439113 2021-12-09 19:46 /input/stations/2021-11-02-stations.csv
-rw-r--r--   3 root supergroup    4440561 2021-12-09 19:47 /input/stations/2021-11-03-stations.csv
-rw-r--r--   3 root supergroup    4439959 2021-12-09 19:48 /input/stations/2021-11-04-stations.csv
-rw-r--r--   3 root supergroup    4443412 2021-12-09 19:48 /input/stations/2021-11-05-stations.csv
-rw-r--r--   3 root supergroup    4442876 2021-12-09 19:49 /input/stations/2021-11-06-stations.csv

$ k exec hadoop-hadoop-hdfs-dn-0 -- hdfs dfs -du -h "/input"
11       /input/last_downloaded_date
176.4 M  /input/prices
25.4 M   /input/stations
```

### Spark App

Our Spark app will read the downloaded data from HDFS.
Connection details are configured in `core-site.xml` and `hdfs-site.xml` (file location is configured via `HADOOP_CONF_DIR` environment variable).

To run the spark app locally in a Docker container:
```bash
$ docker-compose up -d --build
$ docker exec -it big-data-refuel_spark-app_1 bash
spark@ef55f43b991d:/spark-app$ /entrypoint.sh spark-app.py
...
```

Our Spark app checkpoints to HDFS under `/checkpoint`:
```
$ k exec hadoop-hadoop-hdfs-dn-0 -- hdfs dfs -du -h "/checkpoint/*"
41  /checkpoint/commits/0
41  /checkpoint/commits/1
45  /checkpoint/metadata
488  /checkpoint/offsets/0
500  /checkpoint/offsets/1
500  /checkpoint/offsets/2
712  /checkpoint/sources/0
736  /checkpoint/sources/1
3.8 M    /checkpoint/state/0
137.2 M  /checkpoint/state/1
623.2 K  /checkpoint/state/2
```

If the App is interrupted (e.g. because of a Pod deletion/failure), execution is continued from where it left off.
However, it might take a few minutes to initialize the Spark Jobs from the checkpoints.

### Frontend

To run locally:
```bash
$ docker-compose up -d
$ python web-app/app.py
```
