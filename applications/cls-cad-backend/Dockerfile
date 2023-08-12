FROM pypy:3.10-slim
COPY . /cls-cps
WORKDIR /cls-cps
ENV TZ=Europe/Berlin
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone
RUN apt-get -y update && apt-get clean -y && apt-get -y install libxft2 libxext6 && rm -rf /var/lib/apt/lists/ \
EXPOSE 8000
RUN touch cls_cps/database/container
RUN pip3 install -U pip poetry
RUN poetry config virtualenvs.create false
RUN poetry install --no-dev
CMD ["uvicorn", "cls_cps.server:app", "--host", "0.0.0.0", "--port", "80"]
