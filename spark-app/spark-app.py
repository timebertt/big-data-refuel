from pyspark.sql import SparkSession
from pyspark.sql.functions import *
from pyspark.sql.types import DoubleType, StringType, StructType, TimestampType, BooleanType, IntegerType
import mysqlx

dbOptions = {"host": "my-app-mysql-service", 'port': 33060, "user": "root", "password": "mysecretpw"}
dbSchema = 'popular'
windowDuration = '4 hours'
slidingDuration = '1 minute'

# Example Part 1
# Create a spark session
spark = SparkSession.builder \
    .appName("Structured Streaming") \
    .master("local[*]") \
    .getOrCreate()

# Set log level
spark.sparkContext.setLogLevel('WARN')

url = "https://dev.azure.com/tankerkoenig/362e70d1-bafa-4cf7-a346-1f3613304973/_apis/git/repositories/0d6e7286-91e4-402c-af56-fa75be1f223d/items?path=/prices/2021/11/2021-11-17-prices.csv&versionDescriptor%5BversionOptions%5D=0&versionDescriptor%5BversionType%5D=0&versionDescriptor%5Bversion%5D=master&resolveLfs=true&%24format=octetStream&api-version=5.0&download=true"
url = "file:/data/*rices.csv"

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


pricesSchema = StructType() \
    .add("date", StringType()) \
    .add("station_uuid", StringType()) \
    .add("diesel", DoubleType()) \
    .add("e5", DoubleType()) \
    .add("e10", DoubleType()) \
    .add("dieselchange", IntegerType()) \
    .add("e5change", IntegerType()) \
    .add("e10change", IntegerType())

prices = spark.readStream.format("csv").schema(pricesSchema).option("header","true").load(url)

# Displays the content of the DataFrame to stdout
# prices.show()

# Print the schema in a tree format
# prices.printSchema()

def mapZeroToNull(x):
    return when(col(x) > 0, col(x)).otherwise(None)


# 2021-11-17 00:00:08+01
prices = prices \
    .withColumn('date', unix_timestamp('date', "yyyy-MM-dd HH:mm:ssX").cast(TimestampType())) \
    .withColumn('diesel', mapZeroToNull('diesel')) \
    .withColumn('e5', mapZeroToNull('e5')) \
    .withColumn('e10', mapZeroToNull('e10'))

# prices.show()
# prices.printSchema()

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
minPrices = prices.select(column("*")) \
    .withWatermark("date", windowDuration) \
    .groupBy(
        window(
            column("date"),
            windowDuration
        ),
        column("station_uuid")
    ).min()

# Example Part 5
# Start running the query; print running counts to the console
consoleDump = minPrices \
    .writeStream \
    .trigger(processingTime="1 minute") \
    .outputMode("update") \
    .format("console") \
    .option("numRows", "500") \
    .option("truncate", "false") \
    .start()

# # Example Part 6

# def saveToDatabase(batchDataframe, batchId):
#     # Define function to save a dataframe to mysql
#     def save_to_db(iterator):
#         # Connect to database and use schema
#         session = mysqlx.get_session(dbOptions)
#         session.sql("USE popular").execute()

#         for row in iterator:
#             # Run upsert (insert or update existing)
#             sql = session.sql("INSERT INTO popular "
#                               "(mission, count) VALUES (?, ?) "
#                               "ON DUPLICATE KEY UPDATE count=?")
#             sql.bind(row.mission, row.views, row.views).execute()

#         session.close()

#     # Perform batch UPSERTS per data partition
#     batchDataframe.foreachPartition(save_to_db)

# # Example Part 7


# dbInsertStream = popular.writeStream \
#     .trigger(processingTime=slidingDuration) \
#     .outputMode("update") \
#     .foreachBatch(saveToDatabase) \
#     .start()

# Wait for termination
spark.streams.awaitAnyTermination()
