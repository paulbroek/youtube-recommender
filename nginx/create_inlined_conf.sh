#!/bin/bash

# Check if the file and include directory exist
if [ ! -f "nginx.conf" ] || [ ! -d "includes" ]; then
  echo "Error: nginx.conf or includes directory does not exist."
  exit 1
fi

# Check if the grpcservers file exists in the includes directory
if [ ! -f "includes/grpcservers" ]; then
  echo "Error: grpcservers file does not exist in the includes directory."
  exit 1
fi

# Read the contents of the grpcservers file into a variable
grpcservers_contents=$(cat "includes/grpcservers")
grpcservers_contents=`echo ${grpcservers_contents} | tr '\n' "\\n"`

# Use sed to replace the text in nginx.conf and store the output in nginx-inline.conf
sed "s|include includes/grpcservers;|${grpcservers_contents}|g" nginx.conf > nginx-inline.conf
# sed "s|include includes/grpcservers;|some line|g" nginx.conf > nginx-inline.conf

# Confirm that the replacement was successful
echo "Successfully replaced text in nginx.conf and stored the output in nginx-inline.conf."
