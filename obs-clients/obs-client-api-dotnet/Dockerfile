# Build Stage
FROM registry.redhat.io/rhel8/dotnet-80 AS build
WORKDIR /opt/app-root

USER root
COPY *.csproj ./
RUN dotnet restore
COPY . ./
RUN dotnet publish -c Release -o out

# Runtime 
FROM registry.redhat.io/ubi8/dotnet-80-runtime AS runtime
WORKDIR /opt/app-root

COPY --from=build /opt/app-root/out .

EXPOSE 8080

# Run the application
ENTRYPOINT ["dotnet", "obs-client-api-dotnet.dll"]