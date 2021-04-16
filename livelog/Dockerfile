FROM mthenw/frontail
 MAINTAINER Tamas Gal <tgal@km3net.de>

 COPY frontail.json frontail.json
 RUN mkdir -p /logs && touch /logs/MSG.log

 EXPOSE 9001

 CMD ["/logs/MSG.log --ui-highlight --ui-highlight-preset frontail.json --theme dark -l 10000 -n 200 -p 9001"]
