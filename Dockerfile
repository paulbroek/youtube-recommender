FROM python:3.11-slim

RUN python -m pip install --upgrade pip

# RUN apt-get update   		            && \
# 	apt-get install git -y				&& \
# 	apt-get install openssh-client

COPY requirements.txt /tmp

RUN /usr/local/bin/python -m pip install --upgrade pip
RUN pip install -r /tmp/requirements.txt

# download english corpus for SpaCy
RUN python -m spacy download en_core_web_sm

COPY . /tmp

RUN pip install https://github.com/paulbroek/rarc-utils/archive/master.zip
RUN pip install https://github.com/paulbroek/scrape-utils-py/archive/master.zip

RUN pip install python-dotenv

# install package
RUN pip install /tmp/

# compile protobufs
COPY youtube_recommender/protobufs /service/protobufs/
COPY youtube_recommender/scrape_requests /service/scrape_requests/
WORKDIR /service/scrape_requests
RUN python -m grpc_tools.protoc -I ../protobufs --python_out=. \
           --grpc_python_out=. ../protobufs/scrape_requests.proto

# TODO: copy config files
# ...
# or mount in compose file

# adds deps here that can later me moved to requirements.txt
# RUN pip install pandas  

WORKDIR /src
