FROM python:2.7

RUN pip install tensorflow tflearn tweepy h5py dateparser influxdb pandas
ADD sentiment_lookup.py tweets-* /home/root/
WORKDIR /home/root
ENTRYPOINT ["python", "-u", "sentiment_lookup.py"]

