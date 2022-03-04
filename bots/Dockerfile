FROM python:3

# ENV GROUP_ID=1000 \
#     USER_ID=1000

# WORKDIR /var/www/

COPY ./requirements.txt /app/requirements.txt

WORKDIR /bots

RUN python -m pip install --upgrade pip

RUN pip install pika && \
    pip install -r requirements.txt

RUN pip install gunicorn

COPY . /app

# CMD [ "python3" , "app.py" ]

# RUN addgroup -g $GROUP_ID www
# RUN adduser -D -u $USER_ID -G www www -s /bin/sh

# USER www

EXPOSE 5000

CMD [ "gunicorn", "-w", "4", "--bind", "0.0.0.0:5000", "wsgi"]
