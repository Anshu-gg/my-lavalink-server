FROM ghcr.io/lavalink-devs/lavalink:4

# -Djava.net.preferIPv4Stack=true  ← THE KEY FIX
#   Render containers have IPv6 enabled by default, but Discord's voice
#   servers are IPv4. Without this flag the JVM tries IPv6 first, hangs
#   trying to reach Discord voice endpoints, and the bot always times out
#   joining a voice channel no matter how long the timeout is.
#
# -Xmx350m  ← RAM cap for Render's 512MB free tier (prevents OOM kill)
ENV JAVA_OPTS="-Xmx350m -Xms64m -XX:+UseG1GC -XX:MaxGCPauseMillis=100 -XX:+ParallelRefProcEnabled -Djava.net.preferIPv4Stack=true"

COPY application.yml /opt/Lavalink/application.yml
