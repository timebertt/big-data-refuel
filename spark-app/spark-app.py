from os import environ

from pyspark import SparkConf
from pyspark.sql import SparkSession
from pyspark.sql.functions import *
from pyspark.sql.types import DoubleType, StringType, StructType, TimestampType, IntegerType

mode = environ.get("MODE", "local")  # 'local' or 'cluster'
dbOptions = {"host": "mysql", 'port': 3306, "user": "root", "password": "mysecretpw", "database": "prices"}
windowDuration = '4 hours'

# load default spark config (including hadoop config based on `HADOOP_CONF_DIR` environment variable)
sparkConf = SparkConf()

# Create a spark session
# add --master "local[*]" as a command-line option to spark-submit if you want to run this locally (e.g. in a standalone docker container)
spark = SparkSession.builder \
    .config(conf=sparkConf) \
    .appName("Structured Streaming") \
    .getOrCreate()

# Set log level
spark.sparkContext.setLogLevel('WARN')


def mapZeroToNull(x):
    return when(col(x) > 0, col(x)).otherwise(None)


# schemas
pricesSchema = StructType() \
    .add("date", StringType()) \
    .add("station_uuid", StringType()) \
    .add("diesel", DoubleType()) \
    .add("e5", DoubleType()) \
    .add("e10", DoubleType()) \
    .add("dieselchange", IntegerType()) \
    .add("e5change", IntegerType()) \
    .add("e10change", IntegerType())

stationsSchema = StructType() \
    .add("uuid", StringType()) \
    .add("name", StringType()) \
    .add("brand", StringType()) \
    .add("street", StringType()) \
    .add("house_number", StringType()) \
    .add("post_code", StringType()) \
    .add("city", StringType()) \
    .add("latitude", StringType()) \
    .add("longitude", StringType()) \
    .add("first_active", StringType()) \
    .add("openingtimes_json", StringType())

# load data from hdfs
pricesURL = "file:///data/*-prices-filtered.csv"
if mode == "cluster":
    pricesURL = "hdfs:///input/prices/*-prices.csv"

prices = spark.readStream.format("csv").schema(pricesSchema).option("header", "true") \
    .load(pricesURL) \
    .withColumn('date', unix_timestamp('date', "yyyy-MM-dd HH:mm:ssX").cast(TimestampType())) \
    .withColumn('diesel', mapZeroToNull('diesel')) \
    .withColumn('e5', mapZeroToNull('e5')) \
    .withColumn('e10', mapZeroToNull('e10'))

stationsURL = "file:///data/*-stations-filtered.csv"
if mode == "cluster":
    stationsURL = "hdfs:///input/stations/*-stations.csv"

stations = spark.readStream.format("csv").schema(stationsSchema).option("header", "true") \
    .load(stationsURL) \
    .dropDuplicates(["uuid"])  # returns one row per station (we don't care about changes in metadata)

# compute min prices per time window and post code
minPrices = prices \
    .join(stations, prices.station_uuid == stations.uuid, "inner") \
    .withWatermark("date", windowDuration) \
    .groupBy(
    window(
        column("date"),
        windowDuration
    ).alias("window"),
    "post_code"
) \
    .agg(
    min(column("diesel")).alias("diesel"),
    min(column("e5")).alias("e5"),
    min(column("e10")).alias("e10"),
) \
    .select(
    column("*"),
    date_format("window.start", "yyyy-MM-dd HH:mm:ss").alias("window_start"),
    date_format("window.end", "yyyy-MM-dd HH:mm:ss").alias("window_end"),
) \
    .drop("window")

minPrices.printSchema()

# write aggregated data to mysql
def saveToDatabase(batchDataframe, batchId):
    # use jdbc driver to write to mysql. Manual insert/upsert handling will not scale, the built-in jdbc handling
    # already provides connection pooling, etc.
    batchDataframe.write \
        .format('jdbc').options(
        url='jdbc:mysql://{}:{}/{}'.format(dbOptions["host"], dbOptions["port"], dbOptions["database"]),
        driver='com.mysql.cj.jdbc.Driver',
        dbtable='fuel_prices',
        user=dbOptions["user"],
        password=dbOptions["password"]) \
        .mode('append').save()
    # Note: append makes jobs fail, if data is already present in mysql. Other modes cause the jobs to hang forever.
    # Hence, append is used here although it's conceptually wrong for this use case.
    # In order to rerun the spark App, the table has to be truncated first.
    # If checkpointing is enabled (i.e. running on cluster), Spark might be able to recover from checkpoints though and
    # continue the execution without duplicate key failures.


dbInsertStream = minPrices \
    .writeStream \
    .trigger(processingTime="1 minute") \
    .outputMode("append") \
    .foreachBatch(saveToDatabase)

if mode == "cluster":
    # configure checkpointing to HDFS
    dbInsertStream = dbInsertStream.option("checkpointLocation", "/checkpoint")

dbInsertStream.start()

# Wait for termination
spark.streams.awaitAnyTermination()
