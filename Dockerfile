FROM python:3.7.7-alpine3.11

# ==============================================================================
# 타임존 설정
RUN apk add tzdata && \
    cp /usr/share/zoneinfo/Asia/Seoul /etc/localtime && \
    echo "Asia/Seoul" > /etc/timezone

ENV PYTHONUNBUFFERED=0

RUN apk add --no-cache --virtual .build-deps gcc musl-dev
# ==============================================================================
RUN mkdir -p /src/restful_modbus_api
ADD restful_modbus_api /src

# ==============================================================================
# 파일 복사

ADD . /src
WORKDIR /src

# ==============================================================================
# 설치
RUN python setup.py install

# ==============================================================================
# 설치파일 정리
WORKDIR /root
RUN rm -rf /src
RUN apk del .build-deps

EXPOSE 5000

VOLUME ["/root"]

ENTRYPOINT ["restful-modbus-api"]
