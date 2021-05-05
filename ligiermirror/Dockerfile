FROM docker.km3net.de/jpp:v14.1.0
 MAINTAINER Tamas Gal <tgal@km3net.de>

 WORKDIR /ligiermirror

 COPY . .

 RUN source /Jpp/setenv.sh /Jpp && make && mv JLigierMirror /usr/local/bin
