import mysqlx
from pyspark import SparkConf
from pyspark.sql import SparkSession
from pyspark.sql.functions import *
from pyspark.sql.types import DoubleType, StringType, StructType, TimestampType, IntegerType

mode = "cluster"
# mode = "local"

dbOptions = {"host": "my-app-mysql-service", 'port': 33060, "user": "root", "password": "mysecretpw"}
if mode == "local":
    dbOptions["host"] = "host.docker.internal"

dbSchema = 'prices'
windowDuration = '4 hours'
slidingDuration = '1 minute'

# load default spark config (including hadoop config based on `HADOOP_CONF_DIR` environment variable)
sparkConf = SparkConf()

# Example Part 1
# Create a spark session
# add --master "local[*]" as a command-line option to spark-submit if you want to run this locally (e.g. in a standalone docker container)
spark = SparkSession.builder \
    .config(conf=sparkConf) \
    .appName("Structured Streaming") \
    .getOrCreate()

# Set log level
spark.sparkContext.setLogLevel('WARN')


# source: "https://dev.azure.com/tankerkoenig/362e70d1-bafa-4cf7-a346-1f3613304973/_apis/git/repositories/0d6e7286-91e4-402c-af56-fa75be1f223d/items?path=/prices/2021/11&versionDescriptor%5BversionOptions%5D=0&versionDescriptor%5BversionType%5D=0&versionDescriptor%5Bversion%5D=master&resolveLfs=true&%24format=octetStream&api-version=5.0&download=true"
# url = "file:/data/*prices.csv"

# # Example Part 2
# # Read messages from Kafka
# kafkaMessages = spark \
#     .readStream \
#     .format("kafka") \
#     .option("kafka.bootstrap.servers",
#             "my-cluster-kafka-bootstrap:9092") \
#     .option("subscribe", "tracking-data") \
#     .option("startingOffsets", "earliest") \
#     .load()


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
pricesURL = "hdfs:///input/prices/2021/11/2021-11-17*-prices.csv"
if mode == "local":
    pricesURL = "file:///data/*-prices.csv"

prices = spark.readStream.format("csv").schema(pricesSchema).option("header", "true") \
    .load(pricesURL) \
    .withColumn('date', unix_timestamp('date', "yyyy-MM-dd HH:mm:ssX").cast(TimestampType())) \
    .withColumn('diesel', mapZeroToNull('diesel')) \
    .withColumn('e5', mapZeroToNull('e5')) \
    .withColumn('e10', mapZeroToNull('e10'))

# Displays the content of the DataFrame to stdout
# prices.show()

# Print the schema in a tree format
# prices.printSchema()

stationsURL = "hdfs:///input/stations/2021/11/2021-11-17*-stations.csv"
if mode == "local":
    stationsURL = "file:///data/*-stations-filtered.csv"

stations = spark.readStream.format("csv").schema(stationsSchema).option("header", "true") \
    .load(stationsURL)

# # Example Part 3
# # Convert value: binary -> JSON -> fields + parsed timestamp
# trackingMessages = prices.select(
#     # Extract 'value' from Kafka message (i.e., the tracking data)
#     from_json(
#         column("value").cast("string"),
#         trackingMessageSchema
#     ).alias("json")
# ).select(
#     # Convert Unix timestamp to TimestampType
#     from_unixtime(column('json.timestamp'))
#     .cast(TimestampType())
#     .alias("parsed_timestamp"),

#     # Select all JSON fields
#     column("json.*")
# ) \
#     .withColumnRenamed('json.mission', 'mission') \
#     .withWatermark("parsed_timestamp", windowDuration)

# Example Part 4
# Compute most popular slides
minPrices = prices \
    .join(stations, prices.station_uuid == stations.uuid, "inner") \
    .where(col("post_code").like("687%")) \
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
    .limit(10)

minPrices.printSchema()

# Example Part 5
# Start running the query; print running counts to the console
consoleDump = minPrices \
    .writeStream \
    .trigger(processingTime="1 minute") \
    .outputMode("append") \
    .format("console") \
    .option("numRows", "500") \
    .option("truncate", "false") \
    .start()


# Example Part 6

def saveToDatabase(batchDataframe, batchId):
    # Define function to save a dataframe to mysql
    def save_to_db(iterator):
        # Connect to database and use schema
        session = mysqlx.get_session(dbOptions)
        session.sql("USE prices").execute()

        for row in iterator:
            print(row)

            if row.window_start is None or row.window_end is None or row.post_code is None or row.diesel is None or row.e5 is None or row.e10 is None:
                continue

            # Run upsert (insert or update existing)
            session.sql("INSERT INTO fuel_prices (`window_start`, `window_end`, `post_code`, `diesel`, `e5`, `e10`) "
                        "VALUES ('{}', '{}', '{}', {}, {}, {})"
                        "ON DUPLICATE KEY UPDATE `diesel` = VALUES(`diesel`), `e5` = VALUES(`e5`), `e10` = VALUES(`e10`)"
                        .format(row['window_start'], row['window_end'], row['post_code'], row['diesel'],
                                row['e5'], row['e10'])) \
                .execute()

        session.close()

    # Perform batch UPSERTS per data partition
    batchDataframe.foreachPartition(save_to_db)


# Example Part 7


dbInsertStream = minPrices \
    .writeStream \
    .trigger(processingTime="1 minute") \
    .outputMode("append") \
    .foreachBatch(saveToDatabase) \
    .start()

# Wait for termination
spark.streams.awaitAnyTermination()
