FROM pypy:3.10-slim
ENV PIP_ROOT_USER_ACTION=ignore
COPY requirements_docker.txt /cls_cps/
WORKDIR /cls-cps
RUN apt-get update && apt-get install -y libxft2 libxext6 git \
    && pip install --no-cache-dir -r /cls_cps/requirements_docker.txt \
    && apt-get purge -y --auto-remove git \
    && rm -rf /var/lib/apt/lists/*
COPY . /cls-cps
ENV TZ=Europe/Berlin
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone
EXPOSE 8000
RUN touch cls_cps/database/container
CMD pypy -m uvicorn cls_cps.server:app --host 0.0.0.0 --port 80
