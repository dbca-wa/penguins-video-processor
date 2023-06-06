# Penguins Island video processor

This project contains basic scripts and a Dockerfile to run the video transcoding
process required to convert high-quality videos captured on Penguin Island to a
smaller format suitable for usage on the Little Penguins web application.

An image built from the included Dockerfile will run and perform two actions:

1. For the volume mounted at `/app/storage`, it will check the `unprocessed`
   directory for new videos.
1. For any new videos, it will encode them to the required output preset and
   save this output to `/app/storage/encoded`. Processed files are moved to
   `/app/storage/processed`.
1. Encoded videos are uploaded to Azure blob storage, and then the local file is
   removed.

# Running locally

Set up a Python virtualenv and install the packages in `requirements.txt` to run
this project. Run the script manually like so:

    python processor.py

This project uses environment variables (locally set in a `.env` file) to define
application settings. The only required variable is `AZURE_CONNECTION_STRING` to
upload encoded videos to Azure blob storage.

Videos are assumed to be located at `./storage` (relative to the Python script).

# Docker image

To build a new Docker image from the `Dockerfile`:

    docker image build -t ghcr.io/dbca-wa/penguins-video-processor .
