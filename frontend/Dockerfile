FROM python:3.8.6
MAINTAINER Tamas Gal <tgal@km3net.de>

 WORKDIR /frontend
 ENV FLASK_APP=app
 ENV FLASK_RUN_HOST=0.0.0.0
 COPY requirements.txt requirements.txt
 RUN pip install -r requirements.txt
 EXPOSE 5000
 COPY . .
 CMD ["flask", "run"]
