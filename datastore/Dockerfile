FROM python:latest

RUN pip install psycopg2 Flask Flask-API markdown Flask-SQLAlchemy
ENV FLASK_APP=app.py
ENV DB_PATH=/var/lib/db
ARG FLASK_DEBUG=1
ADD app.py /home/root/
WORKDIR /home/root
ENTRYPOINT ["python", "-m", "flask", "run", "--host=0.0.0.0"]

