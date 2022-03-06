FROM python:3.10

# ENV GROUP_ID=1000 \
#     USER_ID=1000

# WORKDIR /var/www/

COPY ./requirements.txt /app/requirements.txt

WORKDIR /app

RUN python3 -m pip install --upgrade pip

# RUN pip install -r requirements.txt

RUN pip3 install --trusted-host pypi.python.org -r requirements.txt

RUN pip3 install gunicorn

COPY . /app

# CMD [ "python3" , "app.py" ]

# RUN addgroup -g $GROUP_ID www
# RUN adduser -D -u $USER_ID -G www www -s /bin/sh

# USER www

EXPOSE 5000

CMD [ "gunicorn", "-w", "4", "--bind", "0.0.0.0:5000", "wsgi"]
