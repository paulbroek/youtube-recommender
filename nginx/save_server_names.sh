#!/bin/bash

filename=$1

# Check if the file already exists
if [ -f "$filename" ]; then
  # If the file already exists, delete it
  rm "$filename"
fi

# Create a new empty file with the specified filename
touch "$filename"

# Get the list of server names from the second command line argument
# server_names=$2
server_names="$(docker ps --filter name=youtube-recommender_scrape-service --format '{{.Names}}' | sort -k 2)"

# Check if the list of server names is not empty
if [ -z "$server_names" ]; then
  # If the list of server names is empty, prompt the user to run `docker-compose up`
  echo "No servers found. Please run 'docker-compose up' first. See README.md"
else
  # Iterate over the list of server names
  for server_name in $server_names; do
    # Append the server name to the file
    echo "server $server_name:50051;" >> "$filename"
  done
fi
