FROM python:3.10

COPY ./bots/requirements.txt /app/requirements.txt

WORKDIR /app

RUN python3 -m pip install --upgrade pip

RUN pip3 install --trusted-host pypi.python.org -r requirements.txt

RUN pip3 install pytest

RUN pip3 install pytest-mock

ENV PYTHONPATH /app

COPY ./bots /app

COPY ./tests /app

RUN ["ls", ".", "-a"]

# sudo docker-compose -f test-docker-compose.yaml up --build
CMD ["pytest", "test_twitter_wrapper.py"]