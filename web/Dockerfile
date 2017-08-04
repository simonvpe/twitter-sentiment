FROM python:latest

RUN pip install psycopg2 Flask
ENV FLASK_APP=app.py
ADD app.py /home/root/
WORKDIR /home/root
ENTRYPOINT ["python", "-m", "flask", "run", "--host=0.0.0.0"]

