FROM pypy:3.10-slim
ENV PIP_ROOT_USER_ACTION=ignore
COPY requirements_docker.txt /cls_cad_backend/
WORKDIR /cls_cad_backend
RUN apt-get update && apt-get install -y libxft2 libxext6 git \
    && pip install --no-cache-dir -r /cls_cad_backend/requirements_docker.txt \
    && apt-get purge -y --auto-remove git \
    && rm -rf /var/lib/apt/lists/*
COPY . /cls_cad_backend
ENV TZ=Europe/Berlin
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone
EXPOSE 8000
RUN touch cls_cad_backend/database/container
CMD pypy -m uvicorn cls_cad_backend.server:app --host 0.0.0.0 --port 80
