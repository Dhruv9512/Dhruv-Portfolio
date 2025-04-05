# Use Miniconda as the base image
FROM continuumio/miniconda3

# Install system dependencies
RUN apt-get update && apt-get install -y \
    pkg-config \
    libmariadb-dev \
    libmariadb-dev-compat \
    build-essential \
    tini \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy environment.yml into the container
COPY environment.yml /app/

# Create the Conda environment (named "portfolioenv")
RUN conda env create -f /app/environment.yml

# Set environment variables
ENV PATH /opt/conda/envs/portfolioenv/bin:$PATH
ENV DEBIAN_FRONTEND=noninteractive

# Ensure Conda is available in bash shells
RUN echo "source /opt/conda/etc/profile.d/conda.sh" >> ~/.bashrc

# Activate Conda by default for all shell commands
SHELL ["conda", "run", "-n", "portfolioenv", "/bin/bash", "-c"]

# Copy your Django project code into the image
COPY . /app/

# Ensure entrypoint is executable
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Expose Django’s default port
EXPOSE 8000

# Use Tini as init system
ENTRYPOINT ["/usr/bin/tini", "--"]

# Run entrypoint script to start Gunicorn
CMD ["/app/entrypoint.sh"]
