FROM python:3.8.6
 MAINTAINER Tamas Gal <tgal@km3net.de>

 WORKDIR /monitoring

 COPY requirements.txt requirements.txt
 RUN pip install -r requirements.txt

 COPY . .

 CMD ["supervisord", "--nodaemon", "-c", "supervisord.conf"]
