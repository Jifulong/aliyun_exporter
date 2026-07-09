FROM python:3-slim

LABEL maintainer="danqing.jfl@gmail.com"

WORKDIR /usr/src/app

COPY . /usr/src/app/
RUN pip install -e .

EXPOSE 9522

ENTRYPOINT ["python", "-u", "/usr/local/bin/aliyun-exporter"]