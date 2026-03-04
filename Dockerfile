FROM ghcr.io/lavalink-devs/lavalink:4

# Limit JVM heap to 350MB so Render's 512MB container doesn't OOM-kill Lavalink.
# Without this, the JVM grabs all available memory and gets killed mid-song.
ENV JAVA_OPTS="-Xmx350m -Xms64m -XX:+UseG1GC -XX:MaxGCPauseMillis=100 -XX:+ParallelRefProcEnabled"

COPY application.yml /opt/Lavalink/application.yml
