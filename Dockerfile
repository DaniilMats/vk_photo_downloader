FROM python:3.7-alpine
MAINTAINER Daniil Matsyutsya
WORKDIR /usr/src/app
COPY  . .
RUN pip install --no-cache-dir -r requirements.txt
ENTRYPOINT /bin/sh

