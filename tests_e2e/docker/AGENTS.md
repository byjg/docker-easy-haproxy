# Instructions for testing

1. Run a docker compose in background for the specified feature e.g. `docker compose -f docker-compose.yml up -d`
2. Check if it is running by running `docker ps` and verifying the container is up
3. If the container is not running, check the logs with `docker logs <container_id>` to diagnose any issues
4. In the top each file, you can find the instructions to test and check if it is working. 
5. If everything is working tear down the container with `docker compose -f docker-compose.yml down`
6. To ensure the container is properly shut down, use `docker compose -f docker-compose.yml down --remove-orphans` to remove any orphaned containers.

# In case you find issues

**DONT TEAR DOWN THE CONTAINERS**

1. Investigate the source code in src/*
2. Try to fix it. 
3. After the code is changed, build it again: `docker build -t byjg/easy-haproxy:5.0.0 -f deploy/docker/Dockerfile --no-cache .` and start the tests again.


