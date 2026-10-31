FROM registry.redhat.io/ubi9/dotnet-100 AS build
WORKDIR /opt/app-root

USER root
COPY *.csproj ./
RUN dotnet restore
COPY . ./
# Ensure no stale local OpenTelemetry DLLs are copied into output
RUN dotnet publish obs-client-api-dotnet.csproj -c Release -o out && \
    rm -f out/OpenTelemetry*.dll

FROM registry.redhat.io/ubi9/dotnet-100 AS runtime
WORKDIR /opt/app-root

COPY --from=build /opt/app-root/out .
EXPOSE 8080

ENTRYPOINT ["dotnet", "obs-client-api-dotnet.dll"]

