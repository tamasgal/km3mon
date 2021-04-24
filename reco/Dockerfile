FROM julia:1.6.0
MAINTAINER Tamas Gal <tgal@km3net.de>

 WORKDIR /reco
 RUN apt-get -y update && apt-get -y install build-essential && apt-get clean

 COPY . .
 RUN julia -e 'using Pkg; Pkg.activate("."); Pkg.instantiate(); Pkg.add(url="https://github.com/tamasgal/NeRCA.jl", rev="master"); Pkg.build("NeRCA"); Pkg.test("NeRCA"; coverage = true)'

 ENTRYPOINT ["julia", "--project=.", "royfit.jl"]
