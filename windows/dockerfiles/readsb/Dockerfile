FROM debian:buster-slim
RUN apt-get update -y
RUN apt-get upgrade -y && \
 apt install -y git build-essential debhelper libusb-1.0-0-dev && \
 apt install -y librtlsdr-dev pkg-config dh-systemd && \
  apt install -y libncurses5-dev zlib1g-dev && \
  apt install -y zlib1g-dev zlib1g  libzstd-dev libzstd1
RUN git clone --depth 1 https://github.com/wiedehopf/readsb.git -b dev && \
 cd readsb && \
 make -j3 HISTORY=yes 
RUN useradd -u 1001 -s /bin/bash riccardo
RUN mkdir /data/  &&  chown 1001:1001 /data
RUN mkdir /data/json &&  chown 1001:1001 /data/json
RUN mkdir /var/globe_history &&  chown -R 1001:1001 /var/globe_history
USER 1001:1001
ENV RECEIVER_OPTIONS =${RECEIVER_OPTIONS}
ENV DECODER_OPTIONS = ${DECODER_OPTIONS}
ENV NET_OPTIONS_READSB = ${NET_OPTIONS_READSB}
ENV JSON_OPTIONS = ${JSON_OPTIONS}
#CMD ["readsb/readsb ${RECEIVER_OPTIONS} ${DECODER_OPTIONS} ${NET_OPTIONS} ${JSON_OPTIONS}"]
CMD readsb/readsb  ${RECEIVER_OPTIONS} ${DECODER_OPTIONS} ${NET_OPTIONS_READSB} ${JSON_OPTIONS}
