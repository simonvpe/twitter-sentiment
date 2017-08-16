FROM python:latest

RUN pip install Flask Flask-API markdown Flask-SQLAlchemy dateparser iso8601 influxdb
ENV FLASK_APP=app.py
ENV DB_PATH=/var/lib/db
ARG FLASK_DEBUG=1
ADD app.py /home/root/
WORKDIR /home/root
ENTRYPOINT ["python", "-u", "-m", "flask", "run", "--host=0.0.0.0"]

