FROM grpc/python:latest

RUN pip install tensorflow tflearn tweepy h5py psycopg2
ADD sentiment_lookup.py tweets-* /home/root/
WORKDIR /home/root
ENTRYPOINT ["python", "sentiment_lookup.py"]

