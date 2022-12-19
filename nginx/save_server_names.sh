#!/bin/bash
# usage examples:
# ./save_server_names.sh ./includes/grpcservers docker
# ./save_server_names.sh ./includes/grpcservers kubernetes

filename=$1
option=$2

# Check if the file already exists
if [ -f "$filename" ]; then
  # If the file already exists, delete it
  rm "$filename"
fi

# Create a new empty file with the specified filename
touch "$filename"

# Get the list of server names from the second command line argument
# server_names=$2

# Get the list of server names based on the option passed
if [ "$option" = "kubernetes" ]; then
  server_names="$(kubectl get po | awk '/scrape-service/ {print $1}')"
elif [ "$option" = "docker" ]; then
  server_names="$(docker ps --filter name=youtube-recommender_scrape-service --format '{{.Names}}' | sort -k 2)"
else
  echo "Error: Invalid option '$option'. Please specify either 'kubernetes' or 'docker'."
  exit 1
fi

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
