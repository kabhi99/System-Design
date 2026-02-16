# DOCKER DATA PERSISTENCE
*Chapter 4: Volumes and Bind Mounts*

Containers are ephemeral by design-when they stop, their data is lost.
This chapter covers how to persist data beyond the container lifecycle.

## SECTION 4.1: THE PERSISTENCE PROBLEM

```
+-------------------------------------------------------------------------+
|                                                                         |
|  WHY DATA DISAPPEARS                                                   |
|                                                                         |
|  Container filesystem is a writable layer on top of image.            |
|  When container is removed, that layer is deleted.                    |
|                                                                         |
|  +-----------------------------------------------------------------+  |
|  |                                                                 |  |
|  |   Container (Running)              Container Removed           |  |
|  |   +----------------+               +----------------+          |  |
|  |   | Writable Layer |               |                |          |  |
|  |   | (your data)    |  ------->     |   GONE!      |          |  |
|  |   +----------------+               |                |          |  |
|  |   | Image Layers   |               +----------------+          |  |
|  |   | (read-only)    |                                           |  |
|  |   +----------------+                                           |  |
|  |                                                                 |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
|  REAL-WORLD EXAMPLE:                                                   |
|  --------------------                                                   |
|  docker run -d mysql                                                  |
|  # Insert data into database                                         |
|  docker rm -f <container_id>                                         |
|  docker run -d mysql                                                  |
|  # All data is GONE!                                                 |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 4.2: DOCKER STORAGE OPTIONS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  THREE WAYS TO PERSIST DATA                                           |
|                                                                         |
|  +-----------------------------------------------------------------+  |
|  |                                                                 |  |
|  |   Host Machine                                                 |  |
|  |   +---------------------------------------------------------+  |  |
|  |   |                                                         |  |  |
|  |   |  /var/lib/docker/volumes/   /home/user/app   tmpfs     |  |  |
|  |   |  +----------------------+   +-----------+   +-------+  |  |  |
|  |   |  |      VOLUMES         |   |   BIND    |   | tmpfs |  |  |  |
|  |   |  |                      |   |  MOUNTS   |   |       |  |  |  |
|  |   |  |  Docker-managed      |   |           |   |  RAM  |  |  |  |
|  |   |  |  Best for prod       |   | Host path |   | only  |  |  |  |
|  |   |  +----------+-----------+   +-----+-----+   +---+---+  |  |  |
|  |   |             |                     |             |      |  |  |
|  |   +-------------+---------------------+-------------+------+  |  |
|  |                 |                     |             |         |  |
|  |   Container     v                     v             v         |  |
|  |   +---------------------------------------------------------+ |  |
|  |   |  /var/lib/mysql      /app/code         /app/cache      | |  |
|  |   |  (database files)    (source code)     (temp data)     | |  |
|  |   +---------------------------------------------------------+ |  |
|  |                                                                 |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 4.3: VOLUMES (Recommended)

```
+-------------------------------------------------------------------------+
|                                                                         |
|  DOCKER VOLUMES                                                        |
|                                                                         |
|  Managed by Docker, stored in /var/lib/docker/volumes/                |
|  Best choice for persisting data in production.                       |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  CREATING VOLUMES                                                       |
|  -----------------                                                      |
|                                                                         |
|  # Create a named volume                                               |
|  docker volume create mydata                                           |
|                                                                         |
|  # List volumes                                                        |
|  docker volume ls                                                       |
|                                                                         |
|  # Inspect volume                                                       |
|  docker volume inspect mydata                                          |
|  # Shows: Mountpoint: /var/lib/docker/volumes/mydata/_data            |
|                                                                         |
|  # Remove volume                                                        |
|  docker volume rm mydata                                                |
|                                                                         |
|  # Remove all unused volumes                                           |
|  docker volume prune                                                    |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  USING VOLUMES                                                         |
|  -------------                                                          |
|                                                                         |
|  # Named volume (recommended)                                          |
|  docker run -d \                                                       |
|    -v mydata:/var/lib/mysql \                                         |
|    mysql:8.0                                                            |
|                                                                         |
|  # Anonymous volume (auto-generated name)                              |
|  docker run -d \                                                       |
|    -v /var/lib/mysql \                                                 |
|    mysql:8.0                                                            |
|                                                                         |
|  # Using --mount (more explicit, recommended)                         |
|  docker run -d \                                                       |
|    --mount type=volume,source=mydata,target=/var/lib/mysql \          |
|    mysql:8.0                                                            |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  VOLUME ADVANTAGES                                                     |
|  -----------------                                                      |
|                                                                         |
|  Y Docker manages the location                                        |
|  Y Easier to backup (docker volume commands)                         |
|  Y Works on Linux and Windows                                        |
|  Y Can be shared among containers                                    |
|  Y Volume drivers enable remote storage (NFS, cloud)                |
|  Y Pre-populated with container's existing files                    |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  SHARING VOLUMES BETWEEN CONTAINERS                                   |
|  -----------------------------------                                    |
|                                                                         |
|  # Database container                                                  |
|  docker run -d --name db \                                             |
|    -v shared-data:/data \                                              |
|    postgres                                                             |
|                                                                         |
|  # Backup container                                                    |
|  docker run --rm \                                                      |
|    -v shared-data:/data:ro \                                           |
|    -v $(pwd):/backup \                                                  |
|    alpine tar cvf /backup/data.tar /data                              |
|                                                                         |
|  Note: :ro makes it read-only                                         |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 4.4: BIND MOUNTS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  BIND MOUNTS                                                           |
|                                                                         |
|  Map a host directory/file into the container.                        |
|  You control the exact path on the host.                              |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  BASIC USAGE                                                           |
|  -----------                                                           |
|                                                                         |
|  # Using -v (old syntax)                                               |
|  docker run -d \                                                       |
|    -v /home/user/myapp:/app \                                          |
|    node:18                                                              |
|                                                                         |
|  # Using --mount (recommended, more explicit)                         |
|  docker run -d \                                                       |
|    --mount type=bind,source=/home/user/myapp,target=/app \            |
|    node:18                                                              |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  DEVELOPMENT WORKFLOW                                                  |
|  ---------------------                                                  |
|                                                                         |
|  Perfect for development-edit code on host, run in container.        |
|                                                                         |
|  # Mount current directory into container                             |
|  docker run -it \                                                       |
|    -v $(pwd):/app \                                                     |
|    -w /app \                                                            |
|    -p 3000:3000 \                                                       |
|    node:18 npm run dev                                                 |
|                                                                         |
|  Edit files locally > Changes immediately visible in container       |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  BIND MOUNT CONSIDERATIONS                                            |
|  -------------------------                                              |
|                                                                         |
|  Y Good for: Development, config files                               |
|  X Bad for: Production databases                                     |
|                                                                         |
|  ISSUES:                                                               |
|  * Host path must exist (not auto-created)                           |
|  * Permission problems (container user vs host user)                 |
|  * Not portable (path varies per machine)                            |
|  * Container can modify host files (security risk)                  |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  READ-ONLY BIND MOUNTS                                                 |
|  ----------------------                                                 |
|                                                                         |
|  # Prevent container from modifying host files                        |
|  docker run -d \                                                       |
|    -v /host/config:/app/config:ro \                                    |
|    myapp                                                                |
|                                                                         |
|  Or with --mount:                                                      |
|  --mount type=bind,source=/host/config,target=/app/config,readonly   |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 4.5: TMPFS MOUNTS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  TMPFS MOUNTS                                                          |
|                                                                         |
|  Store data in host's memory only.                                    |
|  Never written to disk. Gone when container stops.                   |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  USE CASES                                                             |
|  ---------                                                             |
|                                                                         |
|  * Sensitive data (credentials, tokens)                              |
|  * Temporary cache                                                    |
|  * Performance (RAM is faster than disk)                             |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  USAGE                                                                 |
|  -----                                                                 |
|                                                                         |
|  docker run -d \                                                       |
|    --tmpfs /app/cache \                                                |
|    myapp                                                                |
|                                                                         |
|  # With size limit                                                     |
|  docker run -d \                                                       |
|    --mount type=tmpfs,target=/app/cache,tmpfs-size=100m \             |
|    myapp                                                                |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  COMPARISON                                                            |
|                                                                         |
|  +-------------+-----------------------------------------------------+|
|  | Type        | Location      | Persists | Use Case               ||
|  +-------------+---------------+----------+------------------------+|
|  | Volume      | Docker area   | Yes      | Databases, prod data  ||
|  | Bind Mount  | Any host path | Yes      | Dev, config files     ||
|  | tmpfs       | Memory only   | No       | Secrets, cache        ||
|  +-------------+---------------+----------+------------------------+|
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 4.6: DOCKER COMPOSE WITH VOLUMES

```
+-------------------------------------------------------------------------+
|                                                                         |
|  VOLUMES IN DOCKER COMPOSE                                            |
|                                                                         |
|  version: '3.8'                                                        |
|                                                                         |
|  services:                                                              |
|    db:                                                                  |
|      image: postgres:14                                                |
|      volumes:                                                           |
|        # Named volume                                                  |
|        - db-data:/var/lib/postgresql/data                             |
|        # Bind mount for init scripts                                  |
|        - ./init.sql:/docker-entrypoint-initdb.d/init.sql:ro          |
|      environment:                                                       |
|        POSTGRES_PASSWORD: secret                                       |
|                                                                         |
|    web:                                                                 |
|      build: .                                                           |
|      volumes:                                                           |
|        # Bind mount for development                                   |
|        - .:/app                                                         |
|        # Anonymous volume to preserve node_modules                    |
|        - /app/node_modules                                             |
|      tmpfs:                                                             |
|        - /app/cache                                                     |
|                                                                         |
|  # Declare named volumes                                               |
|  volumes:                                                               |
|    db-data:                                                             |
|      # Optional: specify driver                                       |
|      driver: local                                                      |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  EXTERNAL VOLUMES                                                      |
|  ----------------                                                       |
|                                                                         |
|  # Use pre-existing volume                                            |
|  volumes:                                                               |
|    db-data:                                                             |
|      external: true  # Must exist before compose up                  |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 4.7: BACKUP AND RESTORE

```
+-------------------------------------------------------------------------+
|                                                                         |
|  BACKING UP VOLUMES                                                    |
|                                                                         |
|  # Backup: Run a temp container to tar the volume                     |
|  docker run --rm \                                                      |
|    -v mydata:/source:ro \                                               |
|    -v $(pwd):/backup \                                                  |
|    alpine tar cvf /backup/mydata-backup.tar -C /source .              |
|                                                                         |
|  # Restore: Run a temp container to untar                             |
|  docker run --rm \                                                      |
|    -v mydata:/target \                                                  |
|    -v $(pwd):/backup \                                                  |
|    alpine tar xvf /backup/mydata-backup.tar -C /target                |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  DATABASE-SPECIFIC BACKUPS                                            |
|  -------------------------                                              |
|                                                                         |
|  # PostgreSQL                                                          |
|  docker exec mydb pg_dump -U postgres mydb > backup.sql               |
|                                                                         |
|  # MySQL                                                                |
|  docker exec mydb mysqldump -u root -p mydb > backup.sql             |
|                                                                         |
|  # MongoDB                                                              |
|  docker exec mydb mongodump --archive=/backup/dump.gz --gzip         |
|                                                                         |
+-------------------------------------------------------------------------+
```

## CHAPTER SUMMARY

```
+-------------------------------------------------------------------------+
|                                                                         |
|  DATA PERSISTENCE - KEY TAKEAWAYS                                     |
|                                                                         |
|  THREE OPTIONS                                                         |
|  -------------                                                         |
|  * Volumes: Docker-managed, best for production                      |
|  * Bind Mounts: Host paths, best for development                     |
|  * tmpfs: Memory only, best for secrets/cache                        |
|                                                                         |
|  BEST PRACTICES                                                        |
|  --------------                                                        |
|  * Use named volumes (not anonymous)                                 |
|  * Use --mount syntax (clearer than -v)                             |
|  * Make bind mounts read-only when possible                         |
|  * Don't store data in container's writable layer                   |
|                                                                         |
|  COMMANDS                                                              |
|  --------                                                              |
|  docker volume create/ls/inspect/rm/prune                            |
|  docker run -v name:/path (or --mount)                               |
|                                                                         |
+-------------------------------------------------------------------------+
```

## END OF CHAPTER 4

