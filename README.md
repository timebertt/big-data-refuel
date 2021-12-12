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

If deployed with this helm chart, the HDFS namenode will format on each start (see https://github.com/helm/charts/issues/19499).
This results in a new cluster ID and thus datanodes (that have the old cluster ID persisted on disk) won't be able to
join the cluster with errors like this:
```text
2021-12-12 09:58:14,108 WARN org.apache.hadoop.hdfs.server.common.Storage: Failed to add storage directory [DISK]file:/root/hdfs/datanode/
java.io.IOException: Incompatible clusterIDs in /root/hdfs/datanode: namenode clusterID = CID-19a00965-8914-47d2-8d61-0b4fc3a8d2cd; datanode clusterID = CID-566449ab-0985-4b54-9aa2-7382ca1f3a93
	at org.apache.hadoop.hdfs.server.datanode.DataStorage.doTransition(DataStorage.java:760)
	at org.apache.hadoop.hdfs.server.datanode.DataStorage.loadStorageDirectory(DataStorage.java:293)
	at org.apache.hadoop.hdfs.server.datanode.DataStorage.loadDataStorage(DataStorage.java:409)
	at org.apache.hadoop.hdfs.server.datanode.DataStorage.addStorageLocations(DataStorage.java:388)
	at org.apache.hadoop.hdfs.server.datanode.DataStorage.recoverTransitionRead(DataStorage.java:556)
	at org.apache.hadoop.hdfs.server.datanode.DataNode.initStorage(DataNode.java:1649)
	at org.apache.hadoop.hdfs.server.datanode.DataNode.initBlockPool(DataNode.java:1610)
	at org.apache.hadoop.hdfs.server.datanode.BPOfferService.verifyAndSetNamespaceInfo(BPOfferService.java:374)
	at org.apache.hadoop.hdfs.server.datanode.BPServiceActor.connectToNNAndHandshake(BPServiceActor.java:280)
	at org.apache.hadoop.hdfs.server.datanode.BPServiceActor.run(BPServiceActor.java:816)
	at java.lang.Thread.run(Thread.java:745)
2021-12-12 09:58:14,111 ERROR org.apache.hadoop.hdfs.server.datanode.DataNode: Initialization failed for Block pool <registering> (Datanode Uuid 46b21fcc-74de-4ec6-9484-8cb2e5a3bbf9) service to hadoop-hadoop-hdfs-nn/100.96.0.22:9000. Exiting.
```

To fix this behaviour, apply the following patch to the `hadoop` ConfigMap:
```bash
k patch cm hadoop-hadoop --patch-file k8s/hadoop-bootstrap-fix.yaml
```
(Remember to patch the ConfigMap again after upgrading the helm chart.)

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
$ docker-compose up -d --build mysql spark-app
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

To run the web app locally in a Docker container:
```bash
$ docker-compose up -d mysql # start mysql prerequisite
$ docker-compose up --build web-app
$ # open http://localhost:5555 in browser
$ # after code changes: stop (^C) and run again
```
