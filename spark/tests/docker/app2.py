import random
import socket
import time
from threading import Event, Thread

from pyspark.sql import SparkSession
from pyspark.sql.functions import explode
from pyspark.sql.functions import split


WORDS = ('air', 'owl', 'way', 'hen', 'pan', 'owe', 'few', 'kid', 'see', 'beg', 'act', 'cow', 'bin', 'pit', 'ice', 'far')


class ThreadListener(Thread):
    def __init__(self, event):
        super().__init__()
        self.event = event

    @staticmethod
    def _pick_words():
        count = random.randint(1, 10)
        words = random.choices(WORDS, k=count)
        return " ".join(words).encode() + b'\n'

    def run(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('localhost', 9999))
            s.listen(1)
            self.event.set()
            conn, addr = s.accept()
            with conn:
                print('Connected by', addr)
                while True:
                    words = self._pick_words()
                    conn.sendall(words)
                    time.sleep(3)


def main():
    spark = SparkSession.builder.appName("StructuredStreaming").getOrCreate()
    spark.conf.set("spark.sql.streaming.metricsEnabled", "true")

    lines = spark \
        .readStream \
        .format("socket") \
        .option("host", "localhost") \
        .option("port", 9999) \
        .load()

    # Split the lines into words
    words = lines.select(
        explode(
            split(lines.value, " ")
        ).alias("word")
    )

    # Generate running word count
    word_counts = words.groupBy("word").count()

    # Start running the query that prints the running counts to the console
    query = word_counts \
        .writeStream \
        .outputMode("complete") \
        .format("console") \
        .start()

    query.awaitTermination()


def start_listener():
    event = Event()
    thread = ThreadListener(event)
    thread.start()
    event.wait(2)
    return event


if __name__ == '__main__':
    run_event = start_listener()
    try:
        main()
    except:
        print("Terminating threads")
        run_event.clear()


