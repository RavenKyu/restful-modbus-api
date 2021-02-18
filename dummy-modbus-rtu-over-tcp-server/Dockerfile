FROM python:3.7.7-alpine3.11

# ==============================================================================
# 타임존 설정
RUN apk add tzdata && \
    cp /usr/share/zoneinfo/Asia/Seoul /etc/localtime && \
    echo "Asia/Seoul" > /etc/timezone

RUN apk add --no-cache --virtual .build-deps gcc musl-dev

ENV PYTHONUNBUFFERED=0

# ==============================================================================
RUN mkdir -p /root/dummy-modbus-server

ADD dummy-modbus-rtu-over-tcp-server/requirements.txt /root/dummy-modbus-server
WORKDIR /root/dummy-modbus-server
RUN pip install -r requirements.txt

ADD dummy-modbus-rtu-over-tcp-server /root/dummy-modbus-server

WORKDIR /root

RUN apk del .build-deps

EXPOSE 502

ENTRYPOINT ["python" , "-m", "dummy-modbus-server"]