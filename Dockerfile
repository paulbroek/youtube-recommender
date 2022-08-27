FROM python:3.9

RUN python -m pip install --upgrade pip

RUN apt-get update   		            && \
	apt-get install git -y				&& \
	apt-get install openssh-client

COPY requirements.txt /tmp

RUN /usr/local/bin/python -m pip install --upgrade pip
RUN pip install -r /tmp/requirements.txt

COPY . /tmp

RUN pip install -U git+https://git@github.com/paulbroek/rarc-utils.git 

# download english corpus for SpaCy
RUN python -m spacy download en_core_web_sm

# install package
RUN pip install /tmp/

# compile protobufs
COPY youtube_recommender/protobufs /service/protobufs/
COPY youtube_recommender/scrape_requests /service/scrape_requests/
WORKDIR /service/scrape_requests
RUN python -m grpc_tools.protoc -I ../protobufs --python_out=. \
           --grpc_python_out=. ../protobufs/scrape_requests.proto

# todo: copy config files
# ...

# adds deps here that can later me moved to requirements.txt
# RUN pip install pandas  

WORKDIR /src
